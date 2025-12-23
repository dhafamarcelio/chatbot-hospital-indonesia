import sqlite3
import re
import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g
from flask_cors import CORS
import requests

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='static')
app.secret_key = "kunci_rahasia_rs_sehat_selalu"
CORS(app)

DATABASE = 'hospital_chatbot.db'
HOSPITAL_NAME = "RS Sehat Selalu"

API_KEY=os.getenv("GEMINI_API_KEY")
if API_KEY and (API_KEY.startswith('"') and API_KEY.endswith('"')):
    API_KEY = API_KEY[1:-1]
    
API_URL=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

DOCTORS = [
    {"id": 1, "name": "Dr. Arifudin", "speciality": "Kardiologi", "schedule": "Senin 09:00-14:00"},
    {"id": 2, "name": "Dr. Maya Hariyanto", "speciality": "Psikiatri", "schedule": "Selasa 10:00-16:00"},
    {"id": 3, "name": "Dr. Jonathan Hutapea", "speciality": "Neurologi", "schedule": "Rabu 08:00-12:00"},
]

INFO_FAQ = {
    "igd": "IGD (Unit Gawat Darurat) buka 24 jam. Jika kondisi darurat, segera hubungi 118.",
    "rawat_inap": "Prosedur rawat inap: regustrasi, pemeriksaan dokter, penempatan kamar. Harap bawa identitas diri.",
    "jam_besuk": "Jam besuk atau menjenguk: 12:00-14:00 sore dan 18:00-20:00 malam."
}


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row 
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                doctor_id INTEGER NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

init_db()


def analyze_with_ai(user_input):
    if not API_KEY:
        return {"intent": "fallback", "entities": "Sistem AI tidak tersedia."}

    system_prompt = f"""Anda adalah assisten virtual RS Sehat Selalu. Tugas Anda:
    1. Memahami maksud pengguna (intent).
    2. Jika pengguna ingin DAFTAR/BOOKING/YA/MAU, balas dengan intent: "book_appointment".
    3. Jika pengguna ingin CEK JADWAL/TANYA DOKTER, balas dengan intent: "check_schedule".
    4. Jika pengguna MENOLAK/TIDAK MAU, balas dengan ramah dan tetap tawarkan bantuan lain.
    5. jika pengguna menyapa/tanya kabar/ngobrol biasa yang diluar dari konteks rumah sakit, balas dengan manusiawi dan interaktif.
    6. Anda harus mengembalikan format JSON: {{"intent": "...", "reply": "..."}}
    
    Data Dokter:
    {json.dumps(DOCTORS)}
    """

    payload = {
        "contents": [{"parts": [{"text": user_input}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        res = requests.post(API_URL, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        content = data['candidates'][0]['content']['parts'][0]['text']
        return json.loads(content)
    except Exception as e:
        print(f"AI Analysis Error: {e}")
        return {"intent": "fallback", "reply": "Maaf, saya tidak mengerti maksud Anda. Bisa ulangi?"}


def extract_entities(text):
    entities = {}
    text_clean = text.lower()

    m_name = re.search(r'(nama saya|nama|panggil)\s*[:\-\s]*\s*(?P<patient_name>[A-Z a-z 0-9]+)', text, re.IGNORECASE)
    if m_name:
        entities['patient_name'] = m_name.group('patient_name').strip()

    m_phone = re.search(r'(\+62|0)?\s*8[0-9\s-]{7,11}', text)
    if m_phone:
        entities['contact'] = m_phone.group(0).strip()
        
    m_date = re.search(r'(\d{4}-\d{2}-\d{2})(?:\s+pukul\s+(\d{2}:\d{2}))?', text)
    if m_date:
        entities['date'] = m_date.group(1)
        if m_date.group(2):
            entities['time'] = m_date.group(2)

    for d in DOCTORS:
        if d['name'].lower() in text.lower() or d['speciality'].lower() in text.lower():
            entities['doctor_id'] = d['id']
            break
            
    return entities


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        user_text = request.json.get('text', '')
        ai_analysis = analyze_with_ai(user_text)
        intent = ai_analysis.get('intent')
        ai_reply = ai_analysis.get('reply')

        if intent == "book_appointment":
            entities = extract_entities(user_text)
            if 'patient_name' in entities and 'contact' in entities and 'doctor_id' in entities:
                return jsonify({'response': f"Baik, data sudah saya catat.{ai_reply}"})       
        else:
            return jsonify({'response': ai_reply})
        return jsonify({'response': ai_reply})
    except Exception as e:
        print("Server Error: {e}")
        return jsonify({'response': "Aduh, ada gangguan di server. Sebentar ya!"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)