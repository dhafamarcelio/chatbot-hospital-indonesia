"""
Data dan konstanta untuk chatbot RS Sehat Selalu
"""

HOSPITAL_NAME = "RS Sehat Selalu"

doctors_db = {
    "umum": [
        {
            "nama": "Dr. Arifudin", 
            "spesialisasi": "Penyakit Dalam", 
            "jadwal": "Senin-Jumat 08:00-15:00", 
            "kontak": "0891-9906-7798",
            "fun_fact": "Suka nyanyi lagu dangdut pas istirahat",
            "sapaan": "Halo-halo! Siap melayani pasien dengan senyuman!"
        },
        {
            "nama": "Dr. Maya Hariyanto", 
            "spesialisasi": "Anak", 
            "jadwal": "Selasa-Kamis 10:00-17:00", 
            "kontak": "0917-5676-890",
            "fun_fact": "Punya koleksi 100+ stetoskop warna-warni",
            "sapaan": "Hai adik-adik! Ayo bermain sambil periksa ya~"
        }
    ],
    "psikiater": [
        {
            "nama": "Dr. Jonathan Hutapea", 
            "spesialisasi": "Psikiatri", 
            "jadwal": "Rabu-Jumat 13:00-19:00", 
            "kontak": "0896-3309-7878",
            "fun_fact": "Pernah jadi standup comedian sebelum jadi dokter",
            "sapaan": "Tenang saja, semua perasaanmu valid di sini."
        }
    ]
}

INFO_FAQ = {
    "igd": "IGD (Unit Gawat Darurat) buka 24 jam. Jika kondisi darurat, segera hubungi 118.",
    "rawat_inap": "Prosedur rawat inap: registrasi, pemeriksaan dokter, penempatan kamar. Harap bawa identitas diri.",
    "jam_besuk": "Jam besuk atau menjenguk: 12:00-14:00 sore dan 18:00-20:00 malam."
}

PERSONALITY = {
    "name": "Kiko",
    "moods": {
        "happy": ["😊", "😄", "🤗"],
        "sad": ["😔", "🥺", "😢"],
        "angry": ["😠", "🤬", "👿"],
        "confused": ["🤔", "😕", "🧐"]
    },
    "responses": {
        "greetings": [
            "Hai juga! Ada yang bisa Kiko bantu?",
            "Halo! Senang bertemu denganmu hari ini!",
            "Hai-hai! Kiko siap membantu~"
        ],
        "farewell": [
            "Sampai jumpa! Jaga kesehatan ya!",
            "Dadah! Kalau butuh Kiko, panggil lagi ya!",
            "Sampai bertemu lagi! Jangan lupa minum air yang cukup!"
        ],
        "jokes": [
            "Kenapa dokter gigi tidak suka main game? Karena mereka selalu kalah sama 'candy crush'!",
            "Apa bedanya dokter sama programmer? Kalau programmer debug, dokter debridement!",
            "Pasien: Dok, saya susah tidur. Dokter: Coba hitung domba sampai 1000. Pasien: Sampai 999 terus balik lagi ke 1!"
        ],
        "empathy": [
            "Wah, kedengarannya berat ya... Kiko di sini buat dengerin kamu kok 💙",
            "Aku bisa merasakan apa yang kamu rasakan. Mau cerita lebih lanjut?",
            "Peluk virtual dari Kiko dulu ya *hug*"
        ],
        "fun_facts": [
            "Tahukah kamu? Tertawa 15 menit sehari bisa membakar 10-40 kalori!",
            "Fakta unik: RS tertua di Indonesia adalah RS PGI Cikini, berdiri tahun 1919!",
            "Di Jepang, ada 'ruang tawa' di rumah sakit untuk terapi pasien lho!"
        ]
    }
}