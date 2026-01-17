import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import g
from dotenv import load_dotenv
import logging

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'rs_chatbot'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', 5432)
}

def get_db():
    if 'db' not in g:
        try:
            g.db = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
            logging.debug("[DB] Connected")
        except Exception as e:
            logging.error(f"[DB] Connection failedm: {e}")
            raise
        return g.db

def close_connection(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute("""
                           CREATE TABLE IF NOT EXITS users (
                           id SERIAL PRIMARY KEY,
                           email VARCHAR(255) NOT NULL,
                           password_has VARCHAR(255) NOT NULL,
                           name VARCHAR(255) NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                           """)
            
        cursor.execute("""
                       CREATE TABLE IF NOT EXITS sessions (
                       id SERIAL PRIMARY KEY,
                       user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                       session_token VARCHAR (255) UNIQUE NOT NULL,
                       expires_at TIMESTAMP NOT NULL,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                       """)
        
        cursor.execute("""
                       CREATE INDEX IF NOT EXITS idx_sessions_token ON sessions(session_token) """)
        
        cursor.execute("""
                       CREATE TABLE IF NOT EXITS appointments (
                       id SERIAL PRIMARY KEY,
                       user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                       patient_name VARCHAR(255) NOT NULL,
                       CONTACT VARCHAR(255) NOT NULL,
                       doctor_id VARCHAR(255) NOT NULL,
                       appointment_date VARCHAR(50) NOT NULL,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                       """)
        cursor
