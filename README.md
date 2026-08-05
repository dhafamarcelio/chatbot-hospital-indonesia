python -c "
content = '''# 🏥 Chatbot Hospital Indonesia

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Flask](https://img.shields.io/badge/Framework-Flask-green.svg)
![LLM](https://img.shields.io/badge/Fallback%20LLM-Qwen%20(Local)-orange.svg)
![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)

**Chatbot Hospital Indonesia** adalah aplikasi asisten virtual berbasis web yang dirancang untuk menjawab pertanyaan seputar layanan rumah sakit di Indonesia. 

Aplikasi ini menggunakan pendekatan **Hybrid Architecture**:
1. **Rule-Based Engine (Jawaban Utama)**: Memproses query pengguna secara cepat, akurat, dan deterministik berdasarkan aturan/pola yang telah didefinisikan (\`rules.py\`).
2. **Local LLM Fallback (Qwen Model)**: Jika query pengguna tidak dapat dijawab oleh sistem rule-based, sistem secara otomatis meneruskan pertanyaan ke Large Language Model (Qwen) yang berjalan secara lokal via Ollama / Local Server untuk memberikan respons yang fleksibel dan kontekstual.

---

## 🛠️ Fitur Utama

- ⚡ **Jawaban Cepat & Presisi**: Menggunakan logika rule-based untuk pertanyaan umum rumah sakit (pendaftaran, jadwal dokter, fasilitas).
- 🤖 **Fallback LLM Lokal (Qwen)**: Menangani pertanyaan umum/kompleks yang tidak tercakup dalam aturan tanpa mengirim data ke API pihak ketiga (menjaga privasi).
- 🔐 **Autentikasi & Keamanan**: Modul keamanan terintegrasi (\`auth.py\` dan \`security.py\`) untuk manajemen sesi dan validasi input.
- 💾 **Manajemen Data & Feedback**: Menyimpan data respons, histori pengguna, serta umpan balik (feedback) pengguna ke database SQLite (\`database.py\` & \`data.py\`).
- 🌐 **Antarmuka Web Interaktif**: Dibuat menggunakan HTML/CSS & Flask (\`templates/\` & \`static/\`).

---

## 📂 Struktur Repositori

\`\`\`text
chatbot-hospital-indonesia/
├── static/              # Berkas statis (CSS, JS, Gambar)
├── templates/           # Berkas HTML template (Flask UI)
├── .gitignore           # Daftar berkas/direktori yang diabaikan Git
├── app.py               # Main Entry Point / Flask Web Application
├── auth.py              # Logika autentikasi pengguna & otorisasi
├── data.py              # Manajemen data & query handler
├── database.py          # Konfigurasi & koneksi database SQLite
├── llm.py               # Integrasi dengan Local LLM (Qwen Fallback)
├── rules.py             # Sistem aturan (Rule-Based Engine) utama
├── security.py          # Modul keamanan & enkripsi/sanitasi
├── test.py              # Berkas pengujian / unit testing
└── requirements.txt     # Daftar dependensi modul Python
\`\`\`

---

## 💻 Tech Stack

- **Bahasa Pemrograman**: Python 3.x
- **Web Framework**: Flask
- **Frontend**: HTML5, CSS3, JavaScript
- **Local LLM**: Qwen (via Ollama / Local Inference Server)
- **Database**: SQLite

---

## 🚀 Panduan Instalasi & Penggunaan

### 1. Prasyarat
Pastikan sistem Anda telah terpasang:
- Python 3.8+ 
- [Git](https://git-scm.com/)
- **Ollama** (atau runtime LLM lokal lainnya) dengan model **Qwen**:
  \`\`\`bash
  ollama run qwen:1.5b
  \`\`\`

### 2. Clone Repositori
\`\`\`bash
git clone https://github.com/dhafamarcelio/chatbot-hospital-indonesia.git
cd chatbot-hospital-indonesia
\`\`\`

### 3. Buat Virtual Environment
\`\`\`bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / MacOS
python3 -m venv venv
source venv/bin/activate
\`\`\`

### 4. Install Dependensi
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 5. Jalankan Aplikasi
\`\`\`bash
python app.py
\`\`\`
Akses aplikasi melalui browser di \`http://localhost:5000\`.

---

## 🔄 Alur Kerja Sistem (Architecture Workflow)

\`\`\`text
[ Input Pengguna ]
        │
        ▼
┌──────────────────┐
│   rules.py       │ ── (Pencocokan Aturan Utama) ──► [ Jawaban Rule-Based ]
└──────────────────┘
        │
        │ (Jika tidak cocok / Rule Failed)
        ▼
┌──────────────────┐
│    llm.py        │ ── (Inference ke Qwen Lokal) ──► [ Jawaban LLM Fallback ]
└──────────────────┘
\`\`\`

---

## 🌐 Sosial Media & Kontak

Jika ada pertanyaan, saran, atau ingin berdiskusi lebih lanjut mengenai proyek ini, Anda dapat menghubungi saya melalui:

- 📷 **Instagram**: [@dapdhapa](https://www.instagram.com/dapdhapa/?hl=en)
- 👤 **Facebook**: [Muhammad Dhafa](https://www.facebook.com/muhammad.dhafa.3720190)

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).
'''

open('README.md', 'w', encoding='utf-8').write(content)
print('File README.md berhasil diperbarui!')
"