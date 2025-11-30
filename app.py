import re
import sqlite3
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, g, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"Failed to initizalize OpenAI client: {e}")
        openai_client = None

DATABASE = 'hospital_chatbot.db'
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

DOCTORS = [
    {"id": 1, "name": "Dr. Arifudin", "specialty": "Cardiology", "days": ["Senin", "Rabu"], "times": "09:00-13:00"},
    {"id": 2, "name": "Dr. Maya Hariyanto", "specialty": "Psychiatry", "days": ["Selasa", "Kamis"], "times": "10:00-15:00"},
    {"id": 3, "name": "Dr. Jonathan Hutapea", "specialty": "Neurology", "days": ["Rabu", "Jum'at"], "times": "13:00-17:00"},
]

FAQ = {
    "igd": "IGD (Unit Gawat Darurat) buka 24 jam. Jika kondisi darurat, segera datang ke IGD terdekat.",
    "rawat_inap": "Prosedur rawat inap: regustrasi, pemeriksaan dokter, dan penjadwalan kamar jika diperlukan.",
    "visiting_hours": "Jam besuk atau menjenguk: 12:00 - 19:00 setiap hari.",
}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database',None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        contact TEXT,
        doctor_id INTEGER,
        datetime TEXT,
        created_at TEXT
    );
                    
    CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT,
        token TEXT,
        status TEXT,
        created_at TEXT
    );
                      
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_input TEXT,
        intent TEXT,
        response TEXT,
        created_at TEXT
    );
                      ''')
    db.commit()

with app.app_context():
    init_db()

INTENT_PATTERNS = {
    'greeting': [r'halo', r'selamat', r'hi', r'halo\b', r'selamat pagi', r'selamat siang', r'selamat sore', r'selamat malam', r'hey'],
    'doctor_schedule': [r'(jadwal|schedule).*dokter', r'jadwal.*dokter', r'siapa.*praktek', r'jadwal.*(poli|dokter)', r'praktek'],
    'book_appointment': [r'buat.*janji', r'mau.*periksa', r'start.*appointment', r'booking.*dokter', r'pesan.*janji'],
    'check_queue': [r'antrian', r'berapa.*atrian', r'cek.*antrian', r'token', r'no antrian'],
    'faq': [r'igd', r'rawat inap', r'jam besuk', r'jam menjenguk', r'biaya', r'tarif'],
}

def detect_intent(text):
    t = text.lower()
    for intent, pattern in INTENT_PATTERNS.items():
        for p in pattern:
            if re.search(p, t):
                return intent
            return 'fallback'

def extract_entities(text, intent):
    entities = {}
    m = re.search(r'nama saya\s*[:\-]?\s*([A-Z a-z 0-9]+)', text, re.IGNORECASE)
    if m:
        entities['patient_name'] = m.group(1).strip()
    m = re.search(r'(?:\+?62|0)8[0-9]{7, 11}', text)
    if m:
        entities['contact'] = m.group(0)
    m = re.search(r'(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?', text)
    if m:
        entities['date'] = m.group(1)
        if m.group(2):
            entities['time'] = m.group(2)
    for d in DOCTORS:
        if d['name'].lower() in text.lower() or d['speciality'].lower() in text.lower():
            entities['doctor_id'] = d['id']
            break
    return entities

def handle_greeting(_text, entities):
    return "Halo! Saya asisten rumah sakit. Saya bisa membantu cek jadwal dokter, membuat janji, atau mengecek antrian. Apa ada yang bisa saya bantu? "

def handle_doctor_schedule(_text, entities):
    lines = []
    for d in DOCTORS:
        lines.append(f"{d['name']} - {d['speciality']} | Hari: {', '.join(d['days'])} | Jam: {d['times']}")
    return "\n".join(lines)

def handle_book_appointment(text, entities):
    db = get_db()
    cur = db.cursor()
    name = entities.get('patient_name') or 'Pasien'
    contact = entities.get('contact') or "N/A"
    doctor_id = entities.get('doctor_id') or 1
    date = entities.get('date') or datetime.today().strftime('%Y-%m-%d')
    time = entities.get('time') or '09:00'
    dt_str = f"{date} {time}"
    created_at = datetime.utcnow().isoformat()
    doctor_id = int(doctor_id)
    cur.execute('INSERT INTO appointments (patient_name, contact, doctor_id, datetime, created_at) VALUES (?,?,?,?,?)',
                (name, contact, doctor_id, dt_str, created_at))
    db.commit()
    appt_id = cur.lastrowid
    doctor = next((d for d in DOCTORS if d['id'] == doctor_id), DOCTORS[0])
    return f"Janji telah dibuat (ID: {appt_id}) dengan {doctor['name']} pada {dt_str}. Kami akan menghubungi {contact} untuk konfirmasi."

def handle_check_queue(text, entities):
    db = get_db()
    cur = db.cursor()
    dept = 'general'
    cur.execute('SELECT COUNT(*) as c FROM queue WHERE department=? AND status=?', (dept, 'waiting'))
    row = cur.fetchone()
    count = row['c'] if row else 0
    return f"Saat ini ada {count} pasien menunggu di departemen {dept}."

def handle_faq(text, entities):
    t = text.lower()
    if 'igd' in t:
        return FAQ['igd']
    if 'rawat' in t:
        return FAQ['rawat_inap']
    if 'jam besuk' in t or 'besuk' in t:
        return FAQ['visiting_hours']
    if 'jam menjenguk' in t or 'menjenguk' in t:
        return FAQ['visiting_hours']
    return "Maaf, saya belum punya info tersebut, silahkan hubungi call center."

def handle_fallback(text, entities):
    if openai_client:
        try:
            prompt = f"You are a most polite hospital customer service assistant. Answer the user concisely in Indonesian or English. User: {text}\nAssistant:"
            resp = openai_client.completions.create( 
                model="text-davinci-003",
                prompt=prompt,
                max_tokens=150,
                temperature=0.2,
            )
            answer = resp.choices[0].text.strip()
            if answer:
                return answer
        except Exception as e:
            print(f"OpenAI error: {e}")
            pass
        return "Maaf, saya tidak mengerti, bisa ulangi dengan kata lain atau pilih menu bantuan?"

def log_interaction(user_input, intent, response_text):
    db = get_db()
    cur = db.cursor()
    cur.execute('INSERT INTO logs (user_input, intent, response, created_at) VALUES (?,?,?,?)',
                (user_input, intent, response_text, datetime.utcnow().isoformat()))
    db.commit()

@app.route('/')
def index():
    return send_from_directory('.', 'static/index.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json or {}
    text = data.get('text', '')
    intent = detect_intent(text)
    entities = extract_entities(text, intent)
    if intent == 'greeting':
        resp = handle_greeting(text, entities)
    elif intent == 'doctor_schedule':
        resp = handle_doctor_schedule(text, entities)
    elif intent == 'book_appointment':
        resp = handle_book_appointment(text, entities)
    elif intent == 'check_queue':
        resp = handle_check_queue(text, entities)
    elif intent == 'faq':
        resp = handle_faq(text, entities)
    else:
        resp = handle_fallback(text, entities)
    log_interaction(text, intent, resp)
    return jsonify({'intent': intent, 'response': resp, 'entities': entities})

@app.route('/api/appointment', methods=['GET'])
def api_appointment():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM appointments ORDER BY created_at DESC')
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

@app.route('/api/queue', methods=['POST'])
def api_queue_add():
    data = request.json or {}
    dept = data.get('department', 'general')
    token = data.get('token', f"T-{int(datetime.utcnow().timestamp())}")
    created_at = datetime.utcnow().isoformat()
    db = get_db()
    cur = db.cursor()
    cur.execute('INSERT INTO queue (department, token, status, created_at) VALUES (?,?,?,?)',
                (dept, token, 'waiting', created_at))
    db.commit()
    return jsonify({'token': token})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()})

@app.route('/admin/seed_queue')
def admin_seed():
    db = get_db()
    cur = db.cursor()
    for i in range(5):
        token = f"T-{i+1}"
        cur.execute('INSERT INTO queue (department, token, status, created_at) VALUES (?,?,?,?)', ('general', token, 'waiting', datetime.utcnow().isoformat()))
    db.commit()
    return 'seeded'

if __name__ == '__main__':
    app.run(debug=True)