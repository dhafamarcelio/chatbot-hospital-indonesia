# 🏥 Chatbot Hospital Indonesia

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?logo=python">
  <img src="https://img.shields.io/badge/Flask-Web_Framework-black?logo=flask">
  <img src="https://img.shields.io/badge/LLM-Qwen-orange">
  <img src="https://img.shields.io/badge/SQLite-Database-blue?logo=sqlite">
  <img src="https://img.shields.io/badge/Status-Completed-success">
  <img src="https://img.shields.io/badge/License-MIT-green">
</p>

---

# 📌 Project Overview

**Chatbot Hospital Indonesia** is a web-based virtual assistant designed to help users obtain information related to hospital services in Indonesia.

Unlike conventional chatbots that rely solely on Large Language Models (LLMs), this project implements a **Hybrid AI Architecture**, combining a **Rule-Based Expert System** with a **Local Large Language Model (Qwen)**.

The chatbot first attempts to answer user questions using predefined rules to ensure fast, deterministic, and accurate responses. If no matching rule is found, the request is automatically forwarded to a locally hosted **Qwen LLM** through Ollama, enabling more flexible and contextual conversations while maintaining user privacy.

---

# 📚 Table of Contents

- Project Overview
- Features
- Technology Stack
- System Architecture
- Repository Structure
- Installation
- Usage
- Future Improvements
- Author
- License

---

# ✨ Features

### ⚡ Rule-Based Response Engine

- Fast and deterministic answers
- Pattern matching using predefined rules
- Ideal for FAQs and hospital services

Examples:

- Doctor schedules
- Patient registration
- Hospital facilities
- Visiting hours
- General hospital information

---

### 🤖 Local LLM Fallback

When no predefined rule matches the user's question, the chatbot automatically switches to a **Qwen Local LLM** running via Ollama.

Benefits:

- More natural conversation
- Better understanding of complex questions
- No dependency on cloud APIs
- Better user privacy

---

### 🔐 Authentication & Security

Built-in security modules include:

- User Authentication
- Session Management
- Input Validation
- Sanitization
- Protection against invalid requests

---

### 💾 Database Management

Application data is managed using SQLite.

Stored information includes:

- Chat history
- User feedback
- Application data
- Rule datasets

---

### 🌐 Interactive Web Interface

The application provides a lightweight web interface built with:

- HTML5
- CSS3
- JavaScript
- Flask Templates

---

# 💻 Technology Stack

| Category | Technology |
|-----------|------------|
| Language | Python 3 |
| Backend | Flask |
| Frontend | HTML5, CSS3, JavaScript |
| Database | SQLite |
| AI Engine | Rule-Based Expert System |
| Local LLM | Qwen via Ollama |
| Version Control | Git & GitHub |

---

# 🔄 System Workflow

```
                 User Question
                      │
                      ▼
          Rule-Based Matching Engine
             (rules.py)
                      │
      ┌───────────────┴───────────────┐
      │                               │
 Rule Found                     Rule Not Found
      │                               │
      ▼                               ▼
 Return Response              Local Qwen LLM
                                     │
                                     ▼
                            Generate AI Response
                                     │
                                     ▼
                             Return to User
```

---

# 🏗️ System Architecture

The application follows a modular architecture.

```
User
 │
 ▼
Flask Web Application
 │
 ├── Authentication
 │
 ├── Security
 │
 ├── Rule Engine
 │
 ├── Local LLM
 │
 └── SQLite Database
```

---

# 📁 Repository Structure

```text
chatbot-hospital-indonesia/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│
├── app.py
├── auth.py
├── data.py
├── database.py
├── llm.py
├── rules.py
├── security.py
├── test.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/dhafamarcelio/chatbot-hospital-indonesia.git

cd chatbot-hospital-indonesia
```

---

## Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Install Ollama

Download Ollama from:

https://ollama.com

Pull the Qwen model:

```bash
ollama pull qwen:1.5b
```

Run the model:

```bash
ollama run qwen:1.5b
```

---

## Run the Application

```bash
python app.py
```

Open your browser:

```
http://localhost:5000
```

---

# 📊 Hybrid AI Workflow

```
                User Input
                     │
                     ▼
          Flask Application
                     │
                     ▼
          Rule-Based Engine
                     │
        ┌────────────┴────────────┐
        │                         │
     Matched                 Not Matched
        │                         │
        ▼                         ▼
 Return Rule             Local Qwen Model
   Response                    │
                               ▼
                     AI Generated Response
                               │
                               ▼
                          User Output
```

---

# 📈 Project Highlights

✅ Hybrid AI Architecture

✅ Fast Rule-Based Responses

✅ Local LLM Integration

✅ Privacy Friendly

✅ Modular Code Structure

✅ SQLite Database

✅ Flask Web Framework

---

# 🔮 Future Improvements

Some possible future enhancements include:

- User Login Dashboard
- Doctor Appointment Booking
- Voice-to-Text Integration
- Hospital Recommendation System
- Multi-language Support
- Retrieval-Augmented Generation (RAG)
- Medical Knowledge Base Integration
- REST API Version
- Docker Deployment
- Cloud Deployment

---

# 👨‍💻 Author

**Dhafa Marcelio**

Instagram

https://instagram.com/dapdhapa

Facebook

https://facebook.com/muhammad.dhafa.3720190

---

## ⭐ Support

If you find this project useful, consider giving this repository a **Star ⭐**.

---

# 📄 License

This project is licensed under the **MIT License**.