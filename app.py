import os
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import timedelta

from database import get_db, init_db, close_connection, execute_query
from auth import create_user, authenticate_user, create_session, get_current_user, logout_user, login_required
from llm import call_llm
from rules import generate_chatty_response, doctors_db, INFO_FAQ
from security import check_security, sanitize_output, get_user_id
from data import HOSPITAL_NAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'change_this_in_production')
app.permanent_session_lifetime = timedelta(days=7)
CORS(app)

logging.info("=" * 50)
logging.info("STARTING RS CHATBOT - VERSION 4.0 AUTH + POSTGRES")
logging.info(f"Hospital: {HOSPITAL_NAME}")
logging.info("=" * 50)

@app.before_request
def setup_database():
    if not hasattr(app, '_db_initialized'):
        init_db(app)
        app._db_initialized = True

@app.teardown_appcontext
def teardown_database(exception):
    close_connection(exception)

def log_security_event(user_id: str, event_type: str, details: str = ""):
    try:
        execute_query(
            "INSERT INTO security_log (user_id, event_type, details) VALUES (%s, %s, %s)",
            (user_id, event_type, details)
        )
    except Exception as e:
        logging.error(f"[SECURITY LOG] Failed: {e}")

@app.route('/login')
def login():
    user = get_current_user(get_db())
    if user:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/signup')
def signup():
    user = get_current_user(get_db())
    if user:
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    
    if not all(k in data for k in ['name', 'email', 'password']):
        return jsonify({"success": False, "message": "Data tidak lengkap"})
    
    db = get_db()
    result = create_user(db, data['email'], data['password'], data['name'])
    
    if result['success']:
        result['user'] = result['user'].to_dict()
        create_session(db, result['user']['id'])
    
    return jsonify(result)

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    
    if not all(k in data for k in ['email', 'password']):
        return jsonify({"success": False, "message": "Data tidak lengkap"})
    
    db = get_db()
    result = authenticate_user(db, data['email'], data['password'])
    
    if result['success']:
        create_session(db, result['user'].id)
    
    return jsonify(result)

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    db = get_db()
    logout_user(db)
    return jsonify({"success": True, "message": "Logout berhasil"})

@app.route('/api/auth/me', methods=['GET'])
def api_me():
    db = get_db()
    user = get_current_user(db)
    
    if user:
        return jsonify({"success": True, "user": user.tp_dict()})
    else:
        return jsonify({"success": False, "message": "Not authenticated"})

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "version": "4.0-auth"})

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    
    db = get_db()
    user = get_current_user(db)
    user_id = str(user.id)
    
    logging.info(f"[CHAT] User {user.email}: '{user_input[:50]}...'")

    security_check = check_security(user_input, user_id)
    
    if not security_check["allowed"]:
        log_security_event(
            user_id, 
            security_check["metadata"]["reason"],
            security_check["metadata"].get("pattern", "")
        )
        logging.warning(f"[SECURITY] Blocked: {security_check['metadata']['reason']}")
        return jsonify({
            "reply": {
                "intent": "security_blocked",
                "reply": security_check["response"]
            }
        })
    
    if security_check["metadata"].get("contains_pii"):
        log_security_event(
            user_id,
            "pii_detected",
            f"Types: {', '.join(security_check['metadata']['pii_types'])}"
        )
    
    sanitized_input = security_check["sanitized_input"]
    disclaimer = security_check["disclaimer"]
    
    rule_reply = generate_chatty_response(sanitized_input, [])

    if rule_reply:
        logging.info("[CHAT] Rule-based response used")
        reply_text = rule_reply.get("reply") if isinstance(rule_reply, dict) else str(rule_reply)
        
        if disclaimer:
            reply_text += disclaimer
            rule_reply["reply"] = reply_text
        
        execute_query(
            "INSERT INTO chat_history (user_id, message, response) VALUES (%s, %s, %s)",
            (user.id, user_input, reply_text)
        )
        
        return jsonify({"reply": rule_reply})
    
    logging.info("[CHAT] No rule match, calling LLM")
    llm_reply = call_llm(sanitized_input)

    if llm_reply:
        output_check = sanitize_output(llm_reply)
        
        if not output_check["safe"]:
            log_security_event(user_id, "unsafe_llm_output", "Output sanitized")
            final_reply = output_check["sanitized_text"]
        else:
            final_reply = llm_reply
        
        if disclaimer:
            final_reply += disclaimer
        
        reply = {"intent": "llm", "reply": final_reply}
        logging.info("[CHAT] LLM response used")
        execute_query(
            "INSERT INTO chat_history (user_id, message, response) VALUES (%s, %s, %s)",
            (user.id, user_input, final_reply)
        )
    else:
        reply = {
            "intent": "fallback", 
            "reply": "Maaf, saya belum bisa menjawab pertanyaan tersebut. Silakan hubungi staf RS untuk informasi lebih lanjut."
        }
        logging.warning("[CHAT] LLM failed, using fallback")
        execute_query(
            "INSERT INTO chat_history (user_id, message, response) VALUES (%s, %s, %s)",
            (user.id, user_input, reply["reply"])
        )
    
    return jsonify({"reply": reply})

@app.route('/api/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    data = request.get_json()  
    if not all(k in data for k in ['patient_name', 'contact', 'doctor_id', 'date', 'time']):
        return jsonify({"status": "error", "message": "Data tidak lengkap"})
    
    db = get_db()
    user = get_current_user(db)
    
    try:
        execute_query(
            """INSERT INTO appointments 
               (user_id, patient_name, contact, doctor_id, appointment_date, appointment_time) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (user.id, data['patient_name'], data['contact'], 
             data['doctor_id'], data['date'], data['time'])
        )
        return jsonify({"status": "success", "message": "Janji temu berhasil dibuat"})
    except Exception as e:
        logging.error(f"[BOOKING] Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    return jsonify(doctors_db['umum'] + doctors_db['psikiater'])

@app.route('/api/faq', methods=['GET'])
def get_faq():
    topic = request.args.get('topic', '')
    return jsonify({"reply": INFO_FAQ.get(topic, "Info tidak tersedia")})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)