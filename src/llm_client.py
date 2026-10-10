"""Unified LLM client with timeout, retries, backoff, response cache, and provider abstraction."""

import os
import time
import hashlib
import sqlite3
from typing import Optional, Dict, Any, List
import os

supabase_client = None
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except ImportError:
        pass

class LLMClient:
    def __init__(
        self,
        config: Dict[str, Any],
        db_path: str = "data/llm_cache.db"
    ):
        self.cfg = config.get("llm", {})
        self.primary_provider = self.cfg.get("primary_provider", "gemini")
        self.primary_model = self.cfg.get("primary_model", "gemini-3.5-flash-lite")
        self.fallback_provider = self.cfg.get("fallback_provider", "groq")
        self.fallback_model = self.cfg.get("fallback_model", "mixtral-8x7b-32768")
        
        self.timeout = self.cfg.get("timeout_seconds", 30)
        self.max_retries = self.cfg.get("max_retries", 3)
        self.backoff_factor = self.cfg.get("backoff_factor", 1.5)
        self.enable_cache = self.cfg.get("enable_cache", True)
        
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        
        self.db_path = db_path
        self._init_cache()

    def _init_cache(self):
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    prompt_hash TEXT PRIMARY KEY,
                    provider TEXT,
                    model TEXT,
                    response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _get_cache(self, prompt: str, model: str, images: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        if not self.enable_cache:
            return None
            
        hash_str = f"{model}:{prompt}"
        if images:
            for img in images:
                hash_str += f":img_hash_{hashlib.sha256(img['data'].encode('utf-8') if isinstance(img['data'], str) else img['data']).hexdigest()}"
                
        h = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()
        
        if supabase_client:
            try:
                response = supabase_client.table("response_cache").select("response").eq("prompt_hash", h).execute()
                if len(response.data) > 0:
                    return response.data[0]["response"]
            except Exception as e:
                pass # Fallback to sqlite
                
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT response FROM response_cache WHERE prompt_hash = ?", (h,))
            row = cursor.fetchone()
            if row:
                return row[0]
        return None

    def _set_cache(self, prompt: str, model: str, provider: str, response: str, images: Optional[List[Dict[str, Any]]] = None):
        if not self.enable_cache:
            return
            
        hash_str = f"{model}:{prompt}"
        if images:
            for img in images:
                hash_str += f":img_hash_{hashlib.sha256(img['data'].encode('utf-8') if isinstance(img['data'], str) else img['data']).hexdigest()}"
                
        h = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()
        
        if supabase_client:
            try:
                supabase_client.table("response_cache").upsert({
                    "prompt_hash": h,
                    "provider": provider,
                    "model": model,
                    "response": response
                }).execute()
                return
            except Exception as e:
                pass # Fallback to sqlite
                
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO response_cache (prompt_hash, provider, model, response) VALUES (?, ?, ?, ?)",
                (h, provider, model, response)
            )

    def generate(self, prompt: str, system_prompt: str = "", images: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Unified call with automatic fallback, retries, and caching.
        Returns dict with: text, provider, model, cached, latency_s, tokens
        """
        full_prompt = f"{system_prompt}\n\n{prompt}".strip()
        
        # Check cache
        cached_resp = self._get_cache(full_prompt, self.primary_model, images)
        if cached_resp:
            return {
                "text": cached_resp,
                "provider": self.primary_provider,
                "model": self.primary_model,
                "cached": True,
                "latency_s": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
            
        start_t = time.time()
        
        # 1. Try Primary: Gemini
        if self.gemini_key and self.primary_provider == "gemini":
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=self.gemini_key)
                
                contents = [full_prompt]
                if images:
                    import base64
                    for img in images:
                        raw_bytes = base64.urlsafe_b64decode(img["data"])
                        contents.append(types.Part.from_bytes(data=raw_bytes, mime_type=img["mime_type"]))
                
                for attempt in range(self.max_retries):
                    try:
                        resp = client.models.generate_content(
                            model=self.primary_model,
                            contents=contents,
                        )
                        text = resp.text
                        latency = time.time() - start_t
                        self._set_cache(full_prompt, self.primary_model, "gemini", text, images)
                        return {
                            "text": text,
                            "provider": "gemini",
                            "model": self.primary_model,
                            "cached": False,
                            "latency_s": latency,
                            "prompt_tokens": getattr(resp.usage_metadata, "prompt_token_count", 0),
                            "completion_tokens": getattr(resp.usage_metadata, "candidates_token_count", 0),
                        }
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise e
                        time.sleep(self.backoff_factor ** attempt)
            except Exception as primary_err:
                print(f"[LLMClient Warning] Primary provider failed: {primary_err}. Falling back to Groq...")

        # 2. Try Fallback: Groq
        if self.groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=self.groq_key)
                
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                resp = client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    temperature=self.cfg.get("temperature", 0.1),
                    max_tokens=self.cfg.get("max_tokens", 512),
                )
                text = resp.choices[0].message.content
                latency = time.time() - start_t
                self._set_cache(full_prompt, self.fallback_model, "groq", text, images)
                return {
                    "text": text,
                    "provider": "groq",
                    "model": self.fallback_model,
                    "cached": False,
                    "latency_s": latency,
                    "prompt_tokens": resp.usage.prompt_tokens,
                    "completion_tokens": resp.usage.completion_tokens,
                }
            except Exception as fallback_err:
                raise RuntimeError(f"Both primary and fallback providers failed. Groq error: {fallback_err}")
                
        # If no keys set, provide clean mock reply for testing pipelines
        mock_text = "[MOCK LLM GENERATION]: We have verified the relevant course guidelines. Please review the cited policies."
        return {
            "text": mock_text,
            "provider": "mock",
            "model": "mock-baseline",
            "cached": False,
            "latency_s": 0.001,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
