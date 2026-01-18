import hashlib
import secrets
from datetime import datetime, timedelta
from flask import session
import logging

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, pwd_hash = hashed.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() ==pwd_hash
    except:
        return False
def generate_session_token() -> str:
    return secrets.token_urlsafe(32)

class User:
    def __init__(self, user_id, email, name, created_at=None):
        self.id = user_id
        self.email = email
        self.name = name
        self.created_at = created_at

    def tp_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': str(self.created_at) if self.created_at else None
        }
    
def create_user(db, email:str, password: str, name: str) -> dict:
    cursor = db.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return {"success": False, "message": "Email sudah terdaftar"}
            
        pwd_hash = hash_password(password)

        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s) RETURNING id, email, name, created_at",
            (email, pwd_hash, name)
        )

        user_data = cursor.fetchone()
        db.commit()

        user = User(
            user_id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            created_at=user_data['created_at']
        )

        logging.info(f"[AUTH] User created: {email}")
        return {"success": True, "message": "Registrasi berhasil", "user": user}
        
    except Exception as e:
        db.rollback()
        logging.error(f"[AUTH] Create user error: {e}")
        return {"success": False, "message": "Terjadi kesalahan sistem"}
    finally:
        cursor.close()

def authenticate_user(db, email: str, password: str) -> dict:
    cursor = db.cursor()

    try:
        cursor.execute(
            "SELECT id, email, name, password_hash, created_at FROM users WHERE email = %s",
            (email,)
        )

        user_data = cursor.fetchone()

        if not user_data:
            return {"success": False, "message": "Email atau password salah"}
        
        if not verify_password(password, user_data['password_hash']):
            return {"success": False, "message": "Email atau password salah"}
        
        user = User(
            user_id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            created_at=user_data['created_at']
        )

        logging.info(f"[AUTH] User autheticated: {email}")
        return {"success": True, "message": "Login berhasil"}
    
    except Exception as e:
        logging.error(f"[AUTH] Auth error: {e}")
        return {"success": False, "message": "Terjadi kesalahan sistem"}
    finally:
        cursor.close()

def create_session(db, user_id: int) -> str:
    cursor = db.cursor()
    session_token = generate_session_token()
    expires_at = datetime.now() + timedelta(days=7)

    try:
        cursor.execute(
            "INSERT INTO sessions (user_id, session_token, expires_at) VALUES (%s, %s, %s)",
            (user_id, session_token, expires_at)
        )
        db.commit()

        session['session_token'] = session_token
        session['user_id'] = user_id
        session.permanent = True

        logging.info(f"[AUTH] Session created for user{user_id}")
        return session_token
    
    except Exception as e:
        db.rollback()
        logging.error(f"[AUTH] Created session error: {e}")
        return None
    finally:
        cursor.close()

def get_current_user(db) -> User:
    session_token = session.get('session_token')

    if not session_token:
        return None
    
    cursor = db.cursor()

    try:
        cursor.execute(
            """
             SELECT u.id, u.email, u.name, u.cretad_at FROM users u JOIN sessions s ON u.id = s.user_id WHERE s.session_token = %s AND s.expires_at > NOW()
            """,
            (session_token,)
        )

        user_data = cursor.fetchone()

        if not user_data:
            return None
        
        return User(
            user_id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            created_at=user_data['created_at']
        )
    except Exception as e:
        logging.error(f"[AUTH] Get current user error: {e}")
        return None
    finally:
        cursor.close()

def logout_user(db):
    session_token = session.get('session_token')

    if session_token:
        cursor = db.cursor()
        try:
            cursor.execute(
                "DELETE FROM sessions WHERE session_token = %s",
                (session_token,)
            )
            db.commit()
        except:
            pass
        finally:
            cursor.close()

        session.clear()
        logging.info(f"[AUTH] User logged out")

def login_required(f):
    from functools import wraps
    from flask import redirect, url_for

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from database import get_db
        db = get_db()
        user = get_current_user(db)

        if not user:
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    
    return decorated_function

