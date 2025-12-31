import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

LLM_ENABLED = True

logging.info("=" * 50)
logging.info("[LLM] Using LOCAL LLM via Ollama")
logging.info(f"[LLM] Model: {OLLAMA_MODEL}")
logging.info(f"[LLM] URL: {OLLAMA_BASE_URL}")
logging.info("=" * 50)

def call_llm(user_input: str, history: str = "") -> str | None:
    try:
        logging.info(f"[LLM] Calling Ollama - Model: {OLLAMA_MODEL}")

        system_msg = (
            "Kamu adalah Kiko, asisten virtual ramah dari Rumah Sakit Sehat Selalu. "
            "Jawab dengan singkat, jelas, dan aman dalam Bahasa Indonesia. "
            "Maksimal 8 kalimat. Jangan mengarang fakta medis."
        )

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_input}
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 300
            }
        }

        api_url = f"{OLLAMA_BASE_URL}/api/chat"
        logging.debug(f"[LLM] Sending request to: {api_url}")
        
        resp = requests.post(
            api_url,
            json=payload,
            timeout=60 
        )
        
        logging.debug(f"[LLM] Response status: {resp.status_code}")
        
        if resp.status_code == 404:
            logging.error(f"[LLM] Model '{OLLAMA_MODEL}' tidak ditemukan!")
            logging.error("[LLM] Jalankan: ollama pull phi3:mini")
            return None
            
        if resp.status_code == 500:
            logging.error("[LLM] Ollama error - Pastikan Ollama sudah running")
            return None
        
        resp.raise_for_status()
        data = resp.json()
        
        logging.debug(f"[LLM] Response keys: {data.keys()}")

        if "message" in data:
            content = data["message"].get("content", "").strip()
            if content:
                logging.info(f"[LLM] ✅ Success! Generated: {content[:100]}...")
                return content
        
        logging.warning(f"[LLM] Unexpected response: {data}")
        return None
        
    except requests.exceptions.ConnectionError:
        logging.error("[LLM] Connection Error - Ollama tidak running!")
        logging.error("[LLM] Jalankan: ollama serve")
        return None
    except requests.exceptions.Timeout:
        logging.warning("[LLM] Timeout - Model mungkin sedang loading")
        return None
    except Exception as e:
        logging.exception("[LLM] Exception during LLM call")
        return None