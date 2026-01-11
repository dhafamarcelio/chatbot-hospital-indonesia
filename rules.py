import re
import random
import logging
import sqlite3
from flask import session, g
import os
from data import doctors_db, INFO_FAQ, PERSONALITY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'hospital_chatbot.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row 
    return db

def analyze_mood(text):
    text = text.lower()
    positive_words = ['senang', 'happy', 'asyik', 'mantap', 'wkwk', 'haha']
    negative_words = ['sedih', 'galau', 'stress', 'capek', 'lelah', 'marah']
    
    if any(word in text for word in positive_words):
        return "happy"
    elif any(word in text for word in negative_words):
        return "sad"
    elif '?' in text:
        return "curious"
    return "neutral"

def get_random_emoji(mood):
    return random.choice(PERSONALITY["moods"].get(mood, ["🙂"]))

def handle_doctor_query(query):
    logging.info(f"[DOCTOR QUERY] Processing: {query}")
    query_lower = query.lower()
    found_doctors = []
    
    if 'psikiat' in query_lower or 'jiwa' in query_lower or 'mental' in query_lower:
        found_doctors = doctors_db['psikiater']
    elif 'anak' in query_lower or 'pediatri' in query_lower:
        found_doctors = [d for d in doctors_db['umum'] if 'Anak' in d['spesialisasi']]
    elif 'dalam' in query_lower or 'penyakit dalam' in query_lower or 'jantung' in query_lower:
        found_doctors = [d for d in doctors_db['umum'] if 'Penyakit Dalam' in d['spesialisasi']]
    
    for doctor in doctors_db['umum'] + doctors_db['psikiater']:
        if doctor['nama'].lower() in query_lower:
            found_doctors = [doctor]
            break
    
    if not found_doctors:
        general_keywords = ['dokter', 'jadwal', 'tersedia', 'ada', 'siapa', 'list', 'daftar', 'semua', 'lihat']
        if any(keyword in query_lower for keyword in general_keywords):
            found_doctors = doctors_db['umum'] + doctors_db['psikiater']
    
    if not found_doctors:
        return None
    
    responses = []
    for doctor in found_doctors:
        mood_emoji = random.choice(["😊", "👨‍⚕️", "💉", "🩺"])
        response = (
            f"{mood_emoji} <b>{doctor['nama']}</b><br>"
            f"Spesialis: {doctor['spesialisasi']}<br>"
            f"Jadwal: {doctor['jadwal']}<br>"
            f"Kontak: {doctor['kontak']}<br>"
            f"Fun Fact: {doctor['fun_fact']}<br><br>"
            f"<i>{doctor['sapaan']}</i>"
        )
        responses.append(response)
    
    return "<br><br>".join(responses)

def generate_chatty_response(user_input, history):
    logging.info(f"[CHATTY] Analyzing input: {user_input}")
    mood = analyze_mood(user_input)
    emoji = get_random_emoji(mood)
    lower_input = user_input.lower()
    
    last_intent = session.get('last_intent')
    if last_intent:
        if lower_input in ['iya', 'ya', 'yes', 'yep', 'y', 'yoi', 'oke', 'ok', 'boleh']:
            if last_intent == 'counseling':
                session.pop('last_intent', None)
                return {"intent": "counseling_confirmed", "reply": "💙 Baik, saya senang Anda mau berbagi. Silakan ceritakan apa yang sedang Anda rasakan."}
            elif last_intent == 'book_appointment':
                session.pop('last_intent', None)
                return {"intent": "book_appointment", "reply": "👍 Baik! Untuk membuat janji temu, silakan berikan:<br>1. Nama lengkap<br>2. Nomor kontak<br>3. Dokter pilihan<br>4. Tanggal & waktu"}
        elif lower_input in ['tidak', 'kagak', 'no', 'ga', 'g', 'nono', 'gak', 'engga']:
            session.pop('last_intent', None)
            return {"intent": "smalltalk", "reply": "😊 Tidak apa-apa! Ada yang bisa saya bantu dengan hal lain?"}
    
    booking_pattern = r'(.+?),\s*(\d[\d\-\s]+),\s*[Dd]r\.?\s*(.+?),\s*(?:tanggal\s+)?(.+)'
    booking_match = re.match(booking_pattern, user_input)
    
    if booking_match:
        name = booking_match.group(1).strip()
        contact = booking_match.group(2).strip().replace(' ', '').replace('-', '')
        doctor_name = booking_match.group(3).strip()
        date_time = booking_match.group(4).strip()
        
        all_doctors = doctors_db['umum'] + doctors_db['psikiater']
        doctor = next((d for d in all_doctors if doctor_name.lower() in d['nama'].lower() or d['nama'].lower() in doctor_name.lower()), None)
        
        if doctor:
            try:
                db = get_db()
                if 'jam' in date_time.lower():
                    parts = date_time.lower().split('jam')
                    appt_date = parts[0].strip()
                    appt_time = parts[1].strip() if len(parts) > 1 else '00:00'
                else:
                    appt_date = date_time
                    appt_time = '00:00'
                
                db.execute(
                    "INSERT INTO appointments (patient_name, contact, doctor_id, appointment_date, appointment_time) VALUES (?, ?, ?, ?, ?)",
                    (name, contact, doctor['kontak'], appt_date, appt_time)
                )
                db.commit()
                
                return {
                    "intent": "booking_confirmed",
                    "reply": (
                        f"✅ <b>Janji temu berhasil dibuat!</b><br><br>"
                        f"Pasien: {name}<br>Dokter: {doctor['nama']}<br>"
                        f"Tanggal & Waktu: {date_time}<br>Kontak: {contact}<br><br>"
                        f"Silakan datang 15 menit sebelumnya. Untuk perubahan, hubungi {doctor['kontak']}"
                    )
                }
            except:
                return {"intent": "booking_error", "reply": "❌ Maaf, gagal menyimpan janji temu."}
        else:
            return {"intent": "booking_error", "reply": f"❌ Dokter '{doctor_name}' tidak ditemukan."}
    
    if any(word in lower_input for word in ['lucu', 'joke', 'gokil', 'ngakak', 'ketawa']):
        return {"intent": "smalltalk", "reply": f"{emoji} {random.choice(PERSONALITY['responses']['jokes'])}"}
    
    if any(word in lower_input for word in ['makasih', 'terima kasih', 'thanks']):
        return {"intent": "smalltalk", "reply": f"{emoji} Sama-sama! Senang bisa membantu~"}
    
    if any(word in lower_input for word in ['bye', 'dadah', 'sampai jumpa']):
        return {"intent": "smalltalk", "reply": random.choice(PERSONALITY["responses"]["farewell"])}
    
    if mood == "sad":
        return {"intent": "empathy", "reply": random.choice(PERSONALITY["responses"]["empathy"])}
    
    if any(keyword in lower_input for keyword in ['dokter', 'dr', 'jadwal dokter', 'spesialis']):
        doctor_info = handle_doctor_query(lower_input)
        if doctor_info:
            return {"intent": "doctor_info", "reply": doctor_info}
    
    if any(word in lower_input for word in ['igd', 'gawat darurat', 'emergency', 'ugd']):
        return {"intent": "faq", "reply": f"🚨 {INFO_FAQ['igd']}"}
    
    if any(word in lower_input for word in ['rawat inap', 'dirawat', 'opname']):
        return {"intent": "faq", "reply": f"🏥 {INFO_FAQ['rawat_inap']}"}
    
    if any(word in lower_input for word in ['besuk', 'jenguk', 'jam kunjungan']):
        return {"intent": "faq", "reply": f"🕐 {INFO_FAQ['jam_besuk']}"}
    
    if any(word in lower_input for word in ['buat janji', 'booking', 'daftar', 'appointment']):
        session['last_intent'] = 'book_appointment'
        return {"intent": "book_appointment", "reply": f"{emoji} Format: <b>Nama, Nomor HP, Dr. [Nama Dokter], tanggal [tanggal] jam [waktu]</b><br>Contoh: <i>Budi, 08123456789, Dr. Arifudin, tanggal 30 Desember jam 10:00</i>"}
    
    if any(word in lower_input for word in ['curhat', 'cerita', 'bingung', 'galau']):
        session['last_intent'] = 'counseling'
        return {"intent": "counseling", "reply": f"💙 Saya di sini untuk mendengarkan. Untuk konseling lebih mendalam, saya bisa menghubungkan Anda dengan <b>Dr. Jonathan Hutapea</b> (Psikiatri).<br><br>Jadwal: Rabu-Jumat 13:00-19:00<br>Kontak: 0896-3309-7878<br><br>Atau mau cerita dulu ke saya?"}
    
    if any(word in lower_input for word in ['apa kabar', 'kamu gimana', 'kamu baik']):
        return {"intent": "bot_condition", "reply": f"{emoji} Aku baik kok, makasih! Kamu gimana?"}
    
    if any(word in lower_input for word in ['lagi apa', 'lagi ngapain', 'sedang apa']):
        return {"intent": "bot_activity", "reply": f"{emoji} Lagi stand by sambil nunggu kamu. Ada yang bisa aku bantu?"}
    
    if "cuaca" in lower_input:
        return {"intent": "weather", "reply": f"{emoji} Aku belum bisa cek cuaca real-time. Kamu bisa cek di aplikasi BMKG."}
    
    if "nama kamu" in lower_input:
        return {"intent": "bot_identity_name", "reply": f"{emoji} Aku Kiko, asisten virtual RS Sehat Selalu."}
    
    if any(word in lower_input for word in ['kamu hidup', 'kamu manusia', 'kamu apa']):
        return {"intent": "bot_identity_type", "reply": "Aku chatbot, asisten virtual RS Sehat Selalu. Senang ngobrol denganmu!"}
    
    if any(word in lower_input for word in ['dibuat oleh siapa', 'siapa pencipta']):
        return {"intent": "bot_identity_creator", "reply": f"{emoji} Aku dibuat oleh Dhafa Marcelio. Cek @dapdhapa di Instagram!"}
    
    if any(word in lower_input for word in ['kamu bisa apa', 'fitur kamu']):
        return {"intent": "bot_capabilities", "reply": f"{emoji} Aku bisa jawab pertanyaan, kasih info, dan bantu layanan di RS Sehat Selalu."}
    
    if any(word in lower_input for word in ['hi', 'halo', 'hai', 'assalamualaikum', 'selamat']):
        return {"intent": "smalltalk", "reply": f"{emoji} {random.choice(PERSONALITY['responses']['greetings'])}"}
    
    if any(word in lower_input for word in ['dimana lokasi', 'dimana tempat', 'nama jalan', 'jalan', 'lokasi']):
        return {"intent": "bot_identity_creator", "reply": f"{emoji}Halo~. Untuk lokasi RS Sehat Selalu ada di Jl. Manggis No. 89, RT06/RW09, Gambir, Jakarta Pusat"}
    return None