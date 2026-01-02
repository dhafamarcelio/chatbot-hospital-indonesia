import sqlite3
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g, session
from flask_cors import CORS
import logging
from llm import call_llm
from rules import generate_chatty_response, doctors_db, INFO_FAQ, get_db
from security import check_security, sanitize_output, get_user_id

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='static')
app.secret_key = "kunci_rahasia_rs_sehat_selalu"
CORS(app)

CHAT_HISTORY = []

def save_chat(user_msg: str, bot_msg: str) -> None:
    CHAT_HISTORY.append({
        "user": user_msg,
        "bot": bot_msg
    })

def load_chat_history(limit: int = 5) -> str:
    history = CHAT_HISTORY[-limit:]
    formatted = []

    for h in history:
        formatted.append(f"User: (h:['user'])")
        formatted.append(f"Bot: (h['bot'])")
    return "\n".join(formatted)


@app.before_request
def setup_database():
    init_db()
    run_migrations()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'hospital_chatbot.db')
HOSPITAL_NAME = "RS Sehat Selalu"

logging.info("=" * 50)
logging.info("STARTING HOSPITAL CHATBOT - VERSION 3.3 LLM FIXED")
logging.info("Using Ollama with qwen2.5:7b")
logging.info("=" * 50)



@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()

def init_migrations():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    db.commit()

def get_db_version():
    db = get_db()
    row = db.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
    return row["version"] if row and row["version"] else 0

def migrate_v1():
    db = get_db()
    cursor = db.execute("PRAGMA table_info(appointments)")
    columns = [row["name"] for row in cursor.fetchall()]
    
    if "appointment_date" not in columns:
        db.execute("ALTER TABLE appointments ADD COLUMN appointment_date TEXT")
    if "appointment_time" not in columns:
        db.execute("ALTER TABLE appointments ADD COLUMN appointment_time TEXT")
    
    db.execute("INSERT INTO schema_migrations (version) VALUES (1)")
    db.commit()

def run_migrations():
    with app.app_context():
        init_migrations()
        if get_db_version() < 1:
            migrate_v1()

def log_security_event(user_id: str, event_type: str, details: str = ""):
    try:
        db = get_db()
        db.execute(
            "INSERT INTO security_log (user_id, event_type, details) VALUES (?,?,?)",
            (user_id, event_type, details)
        )
        db.commit()
    except Exception as e:
        logging.error(f"[SECURITY LOG] Failed to log: {e}")

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()

    user_id = get_user_id(request)

    logging.info(f"[CHAT] {user_id}: '{user_input[:50]}...'")

    security_check = check_security(user_input, user_id)
    if not security_check["allowed"]:
        log_security_event(user_id, security_check["metadata"]["reason"],security_check["metadata"].get("pattern", ""))
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
            f"Types: {','.join(security_check['metadata']['pii_types'])}"
        )

    sanitized_input = security_check["sanitized_input"]
    disclaimer = security_check["disclaimer"]

    rule_reply = generate_chatty_response(sanitized_input, [])

    if rule_reply:
        logging.info("[CHAT] Rule based response used")
        reply_text = rule_reply.get("reply") if isinstance(rule_reply , dict) else str(rule_reply)

        if disclaimer:
            reply_text += disclaimer
            rule_reply["reply"] = reply_text
        
        save_chat(user_input, reply_text)
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
        logging.info("[CHAT] LLM Response used")
        save_chat(user_input, final_reply)
    else:
        reply = {
            "intent": "fallback", 
            "reply": "Maaf, saya belum bisa menjawab pertanyaan tersebut. Silahkan hubungi staff RS untuk informasi lebih lanjut."
            }
        logging.warning("[CHAT] LLM failed, using static falback")
        save_chat(user_input, reply["reply"])
        
    return jsonify({"reply": reply})
    

@app.route('/api/book_appointment', methods=['POST'])
def book_appointment():
    data = request.get_json()
    if not all(k in data for k in ['patient_name', 'contact', 'doctor_id', 'date', 'time']):
        return jsonify({"status": "error", "message": "Data tidak lengkap!"})
    
    try:
        db = get_db()
        db.execute(
            "INSERT INTO appointments (patient_name, contact, doctor_id, appointment_date, appointment_time) VALUES (?, ?, ?, ?, ?)",
            (data['patient_name'], data['contact'], data['doctor_id'], data['date'], data['time'])
        )
        db.commit()
        return jsonify({"status": "success", "message": "Janji temu berhasil dibuat!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/doctors', methods=['GET'])
def get_doctors():
    return jsonify(doctors_db['umum'] + doctors_db['psikiater'])

@app.route('/api/faq', methods=['GET'])
def get_faq():
    topic = request.args.get('topic', '')
    return jsonify({"reply": INFO_FAQ.get(topic, "Info tidak tersedia.")})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "version": "3.2-llm"})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)