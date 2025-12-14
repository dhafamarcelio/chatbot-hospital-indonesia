import sqlite3
import re
import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g
from flask_cors import CORS
import requests

load_dotenv()

DATABASE = 'hospital_chatbot.db'

API_KEY=os.getenv("GEMINI_API_KEY")
API_URL=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"


app = Flask(__name__, static_folder='static', template_folder='static')
CORS(app)

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
        cursor = db.cursor()
        cursor.execute("""
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


def classify_intent(text):
    text = text.lower()
    patterns = {
        "greeting": [r"halo", r"selamat (pagi|siang|sore|malam)"],
        "check_schedule": [r"jadwal dokter", r"kapan (buka|praktik)", r"cek dokter (.*)"],
        "book_appointment": [r"buat janji", r"reservasi", r"mau daftar"],
        "check_info": [r"igd", r"rawat inap", r"jam besuk", r"info (.*)"],
        "fallback": [r".*"]
    }

    for intent, pats in patterns.items():
        for p in pats:
            t = re.compile(p, re.IGNORECASE)
            if t.search(text):
                return intent
    return 'fallback'

def extract_entities(text, intent):
    entities = {}
    text = text.lower()

    m = re.search(r'nama saya\s*[:\-\]?\s*(?P<patient_name>[A-Z a-z 0-9]+)', text, re.IGNORECASE)
    if m:
        entities['patient_name'] = m.group('patient_name').strip()

    m = re.search(r'(\+62|0)?\s*8[0-9\s-]{7,11}', text)
    if m:
        entities['contact'] = m.group(0).strip()
        
    m = re.search(r'(\d{4}-\d{2}-\d{2})(?:\s+pukul\s+(\d{2}:\d{2}))?', text)
    if m:
        entities['date'] = m.group(1)
        if m.group(2):
            entities['time'] = m.group(2)

    for d in DOCTORS:
        if d['name'].lower() in text or d['speciality'].lower() in text:
            entities['doctor_id'] = d['id']
            break
            
    return entities


def handle_greeting(text, entities):
    return "Halo! Ada yang bisa saya bantu terkait janji, jadwal, atau informasi umum rumah sakit?"

def handle_check_schedule(text, entities):
    if 'doctor_id' in entities:
        doc = next((d for d in DOCTORS if d['id'] == entities['doctor_id']), None)
        if doc:
            return f"Jadwal {doc['name']} ({doc['speciality']}): {doc['schedule']}. Apakah Anda ingin membuat janji?"
    
    specialities = ", ".join(d['speciality'] for d in DOCTORS)
    return f"Kami memiliki dokter {specialities}. Dokter mana yang jadwalnya ingin Anda cek?"

def handle_check_info(text, entities):
    text_lower = text.lower()
    for key, info in INFO_FAQ.items():
        if key in text_lower or re.search(r'\binfo\s+' + key.replace('_',''), text_lower):
            return info
    
    keys = ", ".join(INFO_FAQ.keys())
    return f"Informasi apa yang Anda cari? Kami memiliki informasi tentang: {keys}."

def handle_booking(text, entities):
    db = get_db()
    
    required_slots = ['patient_name', 'contact', 'doctor_id', 'date', 'time']
    
    missing_slots = [slot for slot in required_slots if slot not in entities]
    
    if not missing_slots:
        try:
            doc_name = next(d['name'] for d in DOCTORS if d['id'] == entities['doctor_id'])
            
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO appointments (patient_name, contact, doctor_id, appointment_date, appointment_time) VALUES (?, ?, ?, ?, ?)",
                (entities['patient_name'], entities['contact'], entities['doctor_id'], entities['date'], entities['time'])
            )
            db.commit()
            
            return (f"Booking berhasil! Atas nama {entities['patient_name']} dengan kontak {entities['contact']}, "
                    f"janji temu Anda dengan {doc_name} pada tanggal {entities['date']} pukul {entities['time']} telah dikonfirmasi.")
        except Exception as e:
            return "Maaf, terjadi kesalahan saat menyimpan janji temu. Silakan coba lagi."

    slot_map = {
        'patient_name': 'nama lengkap Anda',
        'contact': 'nomor kontak (telepon atau WA)',
        'doctor_id': 'dokter atau spesialisasi yang Anda inginkan (misal: Kardiologi, Dr. Maya)',
        'date': 'tanggal janji temu (YYYY-MM-DD)',
        'time': 'waktu janji temu (HH:MM)'
    }
    
    first_missing = missing_slots[0]
    prompt = slot_map.get(first_missing, 'informasi yang hilang')
    
    if 'doctor_id' in entities and first_missing == 'doctor_id':
        return f"Spesialisasi yang Anda sebutkan tidak ada dalam daftar kami. Kami hanya memiliki Kardiologi, Psikiatri, dan Neurologi. Ingin janji dengan siapa?"

    return f"Baik, untuk membuat janji, saya butuh {prompt}. Bisa Anda berikan?"

def generate_response_gemini(user_prompt):
    if not API_KEY:
        return None
    
    system_prompt = (
        "Anda adalah Asisten AI Rumah Sakit yang ramah dan sangat sopan. "
        "Tugas Anda adalah membantu pengguna dengan pertanyaan umum yang TIDAK terkait dengan jadwal atau janji. "
        "Jawablah dengan profesional dan gunakan Bahasa Indonesia. "
        "Jika pertanyaan terkait kesehatan atau diagnosis, segera arahkan pengguna untuk berkonsultasi langsung dengan dokter yang tersedia."
    )

    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstructions": {"parts": [{"text": system_prompt}]}
    }

    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        candidate = result.get('candidates', [{}])[0]
        text = candidate.get('content', {}).get('parts', [{}])[0].get('text', '').strip()
        return text
    except requests.exceptions.RequestException as e:
        print(f"GEMINI API Error (Requests Failed): {e}")
        return None
    except Exception as e:
        print(f"Parsing Error: {e}")
        return None

def handle_fallback(text, entities):
    if not API_KEY:
        return "Maaf, saya tidak mengerti. Kunci API Ekseternal sedang tidak tersedia untuk sekarang."
    
    gemini_answer = generate_response_gemini(text)
    if gemini_answer:
        return gemini_answer
    return "Maaf, saya tidak mengerti. Ada masalah koneksi AI atau pertanyaan Anda di luar cakupan saya. Bisakah Anda mengulangi atau mencoba pertanyaan lain?"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Server berjalan normal."})

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        user_text = data.get('text', '')
        
        if not user_text:
            return jsonify({'intent': 'none', 'response': 'Mohon masukkan teks.'}), 400

        intent = classify_intent(user_text)
        entities = extract_entities(user_text, intent)
        
        if intent == 'greeting':
            response_text = handle_greeting(user_text, entities)
        elif intent == 'check_schedule':
            response_text = handle_check_schedule(user_text, entities)
        elif intent == 'check_info':
            response_text = handle_check_info(user_text, entities)
        elif intent == 'book_appointment':
            response_text = handle_booking(user_text, entities)
        else:
            response_text = handle_fallback(user_text, entities)

        return jsonify({'intent': intent, 'response': response_text, 'entities': entities})

    except Exception as e:
        return jsonify({'intent': 'error', 'response': 'Terjadi error server yang tidak terduga. Silakan cek log server.'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)