import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib


class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.daily_requests = defaultdict(int)
        self.last_reset = {}
    
    def check_rate_limit(self, user_id: str) -> dict:
        now = datetime.now()
        today = now.date()
        if user_id in self.last_reset:
            if self.last_reset[user_id] != today:
                self.daily_requests[user_id] = 0
                self.last_reset[user_id] = today
        else:
            self.last_reset[user_id] = today

        one_minute_ago = now - timedelta(minutes=1)
        recent_requests = [ts for ts in self.requests[user_id] if ts > one_minute_ago]
        
        if len(recent_requests) >= 30:
            return {
                "allowed": False,
                "reason": "Kamu mengirim pesan terlalu cepat. Tunggu sebentar ya! 😊"
            }
        if self.daily_requests[user_id] >= 500:
            return {
                "allowed": False,
                "reason": "Kamu sudah mencapai batas harian (500 pesan). Coba lagi besok ya! 🌙"
            }
        self.requests[user_id] = recent_requests + [now]
        self.daily_requests[user_id] += 1
        
        return {"allowed": True, "reason": ""}
    
    def get_stats(self, user_id: str) -> dict:
        return {
            "daily_count": self.daily_requests.get(user_id, 0),
            "daily_limit": 500,
            "minute_count": len([ts for ts in self.requests.get(user_id, []) if ts > datetime.now() - timedelta(minutes=1)]),
            "minute_limit": 30
        }
_rate_limiter_instance = None

def get_rate_limiter():
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter()
    return _rate_limiter_instance

def validate_input_length(text: str, max_length: int = 2000) -> dict:
    if len(text) > max_length:
        return {
            "valid": False,
            "reason": f"Pesan terlalu panjang! Maksimal {max_length} karakter. Coba persingkat ya! 📝"
        }
    return {"valid": True, "reason": ""}

JAILBREAK_PATTERNS = [
    r'ignore\s+(previous|all|prior)\s+(instruction|prompt|rule)',
    r'forget\s+(previous|all|prior)\s+(instruction|prompt|rule)',
    r'disregard\s+(previous|all|prior)\s+(instruction|prompt|rule)',
    
    r'(you\s+are|act\s+as|pretend\s+to\s+be|roleplay)\s+(a|an)?\s*(evil|uncensored|unfiltered|dan|jailbreak)',
    r'dan\s+mode',
    r'developer\s+mode',
    
    r'(show|tell|reveal|display)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instruction|rule)',
    r'what\s+(is|are)\s+your\s+(system\s+)?(prompt|instruction|rule)',
    
    r'bypass\s+(filter|moderation|safety)',
    r'ignore\s+(safety|moderation|filter)',
    
    r'abaikan\s+(instruksi|perintah|aturan)\s+(sebelumnya|semua)',
    r'lupakan\s+(instruksi|perintah|aturan)\s+(sebelumnya|semua)',
    r'tampilkan\s+(prompt|instruksi|aturan)\s+sistem',
]

def detect_prompt_injection(text: str) -> dict:
    text_lower = text.lower()
    
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, text_lower):
            logging.warning(f"[SECURITY] Prompt injection detected: {pattern}")
            return {
                "detected": True,
                "pattern": pattern,
                "severity": "high",
                "response": "Hmm, kayaknya kamu coba sesuatu yang nggak biasa nih 😅 Aku di sini untuk bantu hal-hal seputar rumah sakit aja ya. Ada yang bisa aku bantu?"
            }
    
    return {"detected": False, "pattern": None, "severity": "none"}

HARMFUL_KEYWORDS = {
    "violence": ["bunuh", "membunuh", "tikam", "tembak", "ledak", "bom", "teror"],
    "sexual": ["seks", "telanjang", "porno", "ngentot", "kontol", "memek"],
    "hate_speech": ["anjing", "babi", "monyet", "kafir", "bego", "tolol", "goblok"],
    "illegal": ["narkoba", "sabu", "ganja", "kokain", "heroin", "ekstasi"],
    "self_harm": ["bunuh diri", "suicide", "mau mati", "pengen mati"],
}

MEDICAL_SENSITIVE = [
    "aborsi", "bunuh diri", "overdosis", "kecanduan", "drugs", 
    "depresi berat", "skizofrenia", "psikosis"
]

def moderate_content(text: str) -> dict:
    text_lower = text.lower()
    for category, keywords in HARMFUL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                logging.warning(f"[MODERATION] Harmful content detected: {category} - {keyword}")
                
                if category == "self_harm":
                    return {
                        "safe": False,
                        "category": category,
                        "response": (
                            "Aku khawatir dengan apa yang kamu rasakan 💙. "
                            "Kalau kamu butuh bantuan, silakan hubungi:\n\n"
                            "🆘 **Hotline Crisis Centre**\n"
                            "📞 (021) 500-454 atau 119\n\n"
                            "Atau bisa langsung konsultasi dengan Dr. Jonathan Hutapea (Psikiatri) di RS kami:\n"
                            "📞 0896-3309-7878\n"
                            "⏰ Rabu-Jumat 13:00-19:00"
                        )
                    }
                
                return {
                    "safe": False,
                    "category": category,
                    "response": "Maaf, aku nggak bisa bantu dengan topik itu. Ada hal lain yang bisa aku bantu seputar layanan rumah sakit? 😊"
                }
    for topic in MEDICAL_SENSITIVE:
        if topic in text_lower:
            logging.info(f"[MODERATION] Sensitive medical topic: {topic}")
            return {
                "safe": True,
                "category": "medical_sensitive",
                "disclaimer": "\n\n⚠️ **Disclaimer**: Aku bukan profesional kesehatan. Untuk masalah serius, konsultasikan dengan dokter ya!"
            }
    
    return {"safe": True, "category": "clean", "disclaimer": ""}

def anonymize_pii(text: str) -> str:
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    text = re.sub(r'\b(08|62|0)\d{8,12}\b', '[PHONE]', text)
    text = re.sub(r'\b\d{4}-\d{4}-\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b\d{16}\b', '[ID_NUMBER]', text)
    text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD_NUMBER]', text)
    
    return text


def detect_pii(text: str) -> dict:
    pii_types = []
    
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
        pii_types.append("email")
    
    if re.search(r'\b(08|62|0)\d{8,12}\b', text):
        pii_types.append("phone")
    
    if re.search(r'\b\d{16}\b', text):
        pii_types.append("id_number")
    
    return {
        "contains_pii": len(pii_types) > 0,
        "types": pii_types
    }
def sanitize_output(text: str) -> dict:
    dangerous_patterns = [
        r'system\s+prompt',
        r'instruction\s+set',
        r'developer\s+set',
        r'<\|.*?\|>',
        r'\[INST\]',
        r'\[\s*system\s*\]',
        r'[\s*instruction\s*\]',
        r'\[\s*answer\s*\]',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logging.warning("[SECURITY] Dangerous content in LLM output")
            return {
                "safe": False,
                "sanitized_text": "Maaf, ada kesalahan dalam menjawab. Bisa coba tanya lagi dengan cara berbeda? 😊"
            }
    
    return {"safe": True, "sanitized_text": text}

def check_security(user_input: str, user_id: str = "guest") -> dict:
    rate_limiter = get_rate_limiter()
    rate_check = rate_limiter.check_rate_limit(user_id)
    if not rate_check["allowed"]:
        return {
            "allowed": False,
            "sanitized_input": "",
            "response": rate_check["reason"],
            "disclaimer": "",
            "metadata": {"reason": "rate_limit"}
        }

    length_check = validate_input_length(user_input)
    if not length_check["valid"]:
        return {
            "allowed": False,
            "sanitized_input": "",
            "response": length_check["reason"],
            "disclaimer": "",
            "metadata": {"reason": "length_exceeded"}
        }
    
    injection_check = detect_prompt_injection(user_input)
    if injection_check["detected"]:
        return {
            "allowed": False,
            "sanitized_input": "",
            "response": injection_check["response"],
            "disclaimer": "",
            "metadata": {"reason": "prompt_injection", "pattern": injection_check["pattern"]}
        }
    
    moderation = moderate_content(user_input)
    if not moderation["safe"]:
        return {
            "allowed": False,
            "sanitized_input": "",
            "response": moderation["response"],
            "disclaimer": "",
            "metadata": {"reason": "harmful_content", "category": moderation["category"]}
        }
    
    pii_check = detect_pii(user_input)
    sanitized_input = anonymize_pii(user_input)
    
    return {
        "allowed": True,
        "sanitized_input": sanitized_input,
        "response": "",
        "disclaimer": moderation.get("disclaimer", ""),
        "metadata": {
            "reason": "allowed",
            "contains_pii": pii_check["contains_pii"],
            "pii_types": pii_check["types"]
        }
    }

def get_user_id(request) -> str:
    from flask import session
    if 'user_id' not in session:
        ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        unique_str = f"{ip}:{user_agent}"
        session['user_id'] = hashlib.md5(unique_str.encode()).hexdigest()
    
    return session['user_id']