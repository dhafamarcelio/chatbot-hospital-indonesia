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
                return {"intent": "counseling_confirmed", "reply": "💙 Baik, terima kasih atas kepercayaan Anda. Silakan ceritakan apa yang sedang Anda rasakan saat ini."}
            elif last_intent == 'book_appointment':
                session.pop('last_intent', None)
                return {"intent": "book_appointment", "reply": "👍 Baik. Untuk proses pendaftaran, mohon kirimkan data berikut:<br>1. Nama lengkap<br>2. Nomor kontak<br>3. Dokter tujuan<br>4. Rencana tanggal & waktu kunjungan"}
        elif lower_input in ['tidak', 'kagak', 'no', 'ga', 'g', 'nono', 'gak', 'engga']:
            session.pop('last_intent', None)
            return {"intent": "smalltalk", "reply": "😊 Baik, tidak masalah. Apakah ada informasi lain yang bisa saya bantu?"}
    
    if any(word in lower_input for word in ['igd', 'ugd', 'gawat darurat', 'emergency']):
        return {
            "intent": "faq_nav", 
            "reply": f"🚨 <b>Layanan Gawat Darurat (IGD/UGD):</b><br>Unit Gawat Darurat kami berlokasi di <b>Lantai 1 Sayap Kiri</b> gedung utama. Akses terbuka 24 jam. Anda dapat langsung menuju pintu masuk khusus ambulance untuk penanganan cepat."
        }
    
    if any(word in lower_input for word in ['toilet', 'wc', 'kamar mandi', 'restroom']):
        return {
            "intent": "facility_nav",
            "reply": f"🚻 <b>Fasilitas Toilet:</b><br>Toilet tersedia di setiap lantai, tepat di sebelah area lift dan dekat tangga darurat. Tersedia juga toilet khusus difabel di area Lobby Utama."
        }
    
    if any(word in lower_input for word in ['musholla', 'sholat', 'masjid', 'ibadah']):
        return {
            "intent": "facility_nav",
            "reply": f"🕌 <b>Fasilitas Ibadah:</b><br>Musholla utama terletak di <b>Lantai Basement 1</b> dan <b>Lantai 3 Sayap Kanan</b>. Area ini dilengkapi dengan tempat wudhu yang memadai."
        }

    if any(word in lower_input for word in ['apotek', 'farmasi', 'ambil obat']):
        return {
            "intent": "facility_nav",
            "reply": f"💊 <b>Instalasi Farmasi/Apotek:</b><br>Berlokasi di <b>Lantai 1</b>, searah dengan pintu keluar utama. Silakan serahkan resep Anda di loket yang tersedia."
        }
    
    if any(word in lower_input for word in ['lab', 'laboratorium', 'cek darah', 'rontgen', 'radiologi']):
        return {
            "intent": "facility_nav",
            "reply": f"🔬 <b>Layanan Penunjang Medis:</b><br>Laboratorium dan Radiologi terletak di <b>Lantai 2</b>. Silakan gunakan lift utama dan ikuti petunjuk arah berwarna biru."
        }

    if any(word in lower_input for word in ['pendaftaran', 'registrasi', 'kasir', 'admin', 'bayar']):
        return {
            "intent": "facility_nav",
            "reply": f"💳 <b>Layanan Administrasi:</b><br>Loket Pendaftaran dan Kasir berada di <b>Lobby Utama Lantai 1</b>. Mohon siapkan kartu identitas atau kartu asuransi Anda."
        }

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
                parts = date_time.lower().split('jam') if 'jam' in date_time.lower() else [date_time, '00:00']
                appt_date = parts[0].strip()
                appt_time = parts[1].strip() if len(parts) > 1 else '00:00'
                
                db.execute(
                    "INSERT INTO appointments (patient_name, contact, doctor_id, appointment_date, appointment_time) VALUES (?, ?, ?, ?, ?)",
                    (name, contact, doctor['kontak'], appt_date, appt_time)
                )
                db.commit()
                
                return {
                    "intent": "booking_confirmed",
                    "reply": (
                        f"✅ <b>Reservasi Berhasil Dikonfirmasi</b><br><br>"
                        f"Nama Pasien: {name}<br>Dokter: {doctor['nama']}<br>"
                        f"Jadwal: {date_time}<br><br>"
                        f"Mohon hadir 15 menit sebelum jadwal. Terima kasih."
                    )
                }
            except:
                return {"intent": "booking_error", "reply": "❌ Mohon maaf, terjadi kendala teknis saat menyimpan data pendaftaran."}
        else:
            return {"intent": "booking_error", "reply": f"❌ Mohon maaf, dokter dengan nama '{doctor_name}' tidak ditemukan dalam database kami."}
    
    # Smalltalk & Identity (Dibuat lebih formal)
    if any(word in lower_input for word in ['makasih', 'terima kasih', 'thanks']):
        return {"intent": "smalltalk", "reply": f"{emoji} Terima kasih kembali. Senang dapat membantu Anda."}
    
    if any(word in lower_input for word in ['bye', 'dadah', 'sampai jumpa']):
        return {"intent": "smalltalk", "reply": "Terima kasih telah menghubungi kami. Semoga sehat selalu."}
    
    if any(keyword in lower_input for keyword in ['dokter', 'dr', 'jadwal dokter', 'spesialis']):
        doctor_info = handle_doctor_query(lower_input)
        if doctor_info: return {"intent": "doctor_info", "reply": doctor_info}
    
    if any(word in lower_input for word in ['buat janji', 'booking', 'daftar', 'appointment']):
        session['last_intent'] = 'book_appointment'
        return {"intent": "book_appointment", "reply": f"{emoji} Untuk pendaftaran mandiri, silakan gunakan format berikut:<br><b>Nama, Nomor HP, Dr. [Nama Dokter], tanggal [tanggal] jam [waktu]</b>"}
    
    if "nama kamu" in lower_input:
        return {"intent": "bot_identity_name", "reply": f"{emoji} Saya Kiko, asisten virtual resmi dari RS Sehat Selalu."}
    
    if any(word in lower_input for word in ['dimana lokasi', 'dimana tempat', 'nama jalan', 'jalan', 'lokasi']):
        return {"intent": "location", "reply": f"📍 <b>Lokasi Kami:</b><br>RS Sehat Selalu berlokasi di Jl. Manggis No. 89, Gambir, Jakarta Pusat. Kami tersedia di Google Maps untuk navigasi lebih mudah."}

    if any(word in lower_input for word in ['hi', 'halo', 'hai', 'assalamualaikum', 'selamat']):
        return {"intent": "smalltalk", "reply": f"{emoji} Selamat datang di layanan asisten virtual RS Sehat Selalu. Ada yang bisa saya bantu?"}

    return None
        