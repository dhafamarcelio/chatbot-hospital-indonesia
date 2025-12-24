import sqlite3
import re
import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g, session
from flask_cors import CORS
import requests
import logging

logging.basicConfig(
    filename='chatbot.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

def analyze_with_ai(user_input, history):
    if not API_KEY:
        return {"intent": "error", "reply": "API Key belum di set di file .env!"}
    
    context_str = "\n".join([f"User: {h['user']}\nBot: {h['bot']}" for h in history[-3:]])

    system_prompt = f"""Anda adalah asisten virtual {HOSPITAL_NAME} yang ramah dan membantu. Tugas utama Anda:
1. Pahami intent pengguna dengan tepat
2. Untuk booking/jadwalkan pertemuan, gunakan intent: "book_appointment"
3. Untuk info dokter/jadwal, gunakan intent: "check_schedule"
4. Untuk FAQ rumah sakit, gunakan intent: "info"
5. Format respons HARUS berupa JSON valid: {{"intent": "...", "reply": "..."}}

Contoh respons valid:
{{"intent": "book_appointment", "reply": "Baik, saya akan bantu daftarkan Anda."}}

Data yang tersedia:
- Dokter: {json.dumps(DOCTORS)}
- Info: {json.dumps(INFO_FAQ)}
"""

    payload = {
        "contents": [{
            "parts": [{
                "text": f"Konteks:\n{context_str}\n\nPertanyaan User:\n{user_input}"
            }]
        }],
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "generation_config": {
            "response_mime_type": "application/json",
            "temperature": 0.3  # Kurangi kreativitas untuk hasil lebih konsisten
        }
    }

    try:
        logging.info(f"Mengirim request ke API Gemini dengan payload: {json.dumps(payload)}")
        res = requests.post(API_URL, json=payload, timeout=15)
        res.raise_for_status()
        
        response_data = res.json()
        logging.info(f"Respon dari API: {json.dumps(response_data)}")
        if 'candidates' not in response_data:
            raise ValueError("Format respons tidak valid")
            
        content = response_data['candidates'][0]['content']['parts'][0]['text']
        clean_content = content.replace('```json', '').replace('```', '').strip()
        
        result = json.loads(clean_content)
        if not all(key in result for key in ['intent', 'reply']):
            raise ValueError("Struktur JSON tidak lengkap")
            
        return result
        
    except Exception as e:
        logging.error(f"Error saat request API: {str(e)}")
        print(f"AI Error: {str(e)}")
        lower_input = user_input.lower()
        if any(kw in lower_input for kw in ['daftar', 'booking', 'janji']):
            return {"intent": "book_appointment", "reply": "Saya akan bantu proses pendaftaran. Bisa sebutkan nama, nomor HP, dan dokter yang dituju?"}
        elif any(kw in lower_input for kw in ['jadwal', 'dokter']):
            return {"intent": "check_schedule", "reply": f"Ini jadwal dokter kami: {[d['name']+' ('+d['speciality']+')' for d in DOCTORS]}"}
        else:
            return {"intent": "fallback", "reply": "Maaf, saya belum paham. Bisa diulang dengan lebih detail?"}
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
        session['history'] = session.get('history', [])
        
        user_text = request.json.get('text', '').strip()
        logging.info(f"User mengirim pesan: {user_text}")
        if not user_text:
            return jsonify({'response': "Maaf, pesan tidak boleh kosong"})
        
        ai_response = analyze_with_ai(user_text, session['history'])
        logging.info(f"AI merespon dengan intent: {ai_response.get('intent')}, reply: {ai_response.get('reply')}")
        
        session['history'].append({
            "user": user_text,
            "bot": ai_response.get('reply', '')
        })
        session.modified = True
        
        if ai_response.get('intent') == "book_appointment":
            logging.info("Proses booking dicatat.")
            entities = extract_entities(user_text + " " + " ".join([h['user'] for h in session['history'][-2:]]))
            
            if all(k in entities for k in ['patient_name', 'contact', 'doctor_id']):
                try:
                    db = get_db()
                    db.execute(
                        "INSERT INTO appointments (patient_name, contact, doctor_id, appointment_date, appointment_time) VALUES (?, ?, ?, ?, ?)",
                        (entities['patient_name'], entities['contact'], entities['doctor_id'], 
                         entities.get('date', '2023-01-01'), entities.get('time', '10:00'))
                    )
                    db.commit()
                    ai_response['reply'] = "Pendaftaran berhasil! Kami akan konfirmasi via WhatsApp."
                except Exception as e:
                    print(f"DB Error: {e}")
                    ai_response['reply'] = "Maaf, ada error saat menyimpan data. Coba lagi nanti."
        
        return jsonify({'response': ai_response.get('reply', 'Tidak dapat memproses permintaan')})

    except Exception as e:
        logging.error(f"Error saat simpan ke DB: {str(e)}")
        print(f"Server Error: {e}")
        return jsonify({'response': "Mohon maaf, sedang ada masalah teknis. Silakan coba beberapa saat lagi."}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)