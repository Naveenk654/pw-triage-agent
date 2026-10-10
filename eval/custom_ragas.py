"""Custom Ragas implementation matching the official strict mathematical definitions."""

import os
import json
import time
import numpy as np
from tqdm import tqdm
from pydantic import BaseModel
from typing import List
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from src.embedder import LocalEmbedder

load_dotenv()

# --- PYDANTIC MODELS FOR STRICT RAGAS LOGIC ---

class ClaimExtraction(BaseModel):
    claims: List[str]

class ClaimVerificationItem(BaseModel):
    claim: str
    is_supported: bool

class ClaimVerification(BaseModel):
    verifications: List[ClaimVerificationItem]

class ReverseQuestions(BaseModel):
    questions: List[str]

# --- UTILS ---
def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


def run_custom_ragas():
    cache_path = "eval/results/ragas_cache.json"
    if not os.path.exists(cache_path):
        print("No cache found! Please let the gathering pipeline finish first.")
        return
        
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    questions = data["questions"]
    answers = data["answers"]
    contexts = data["contexts"]
    
    print(f"Loaded {len(questions)} responses from cache.")
    print("Starting Authentic Ragas Evaluation (Claim Extraction + Reverse Engineering)...")
    
    client = instructor.from_openai(OpenAI(
        api_key=os.environ.get("MISTRAL_API_KEY"),
        base_url="https://api.mistral.ai/v1"
    ))
    embedder = LocalEmbedder()
    
    total_faithfulness = 0.0
    total_relevancy = 0.0
    evaluated = 0
    
    for i in tqdm(range(len(questions)), desc="Grading tickets strictly"):
        q = questions[i]
        a = answers[i]
        c = "\n".join(contexts[i])
        
        try:
            # ==========================================
            # 1. RAGAS FAITHFULNESS ALGORITHM
            # ==========================================
            
            # Step 1: Extract claims
            extr_res = client.chat.completions.create(
                model="mistral-small-latest",
                response_model=ClaimExtraction,
                messages=[{"role": "user", "content": f"Extract all factual claims from this text as a list of short sentences.\nText: {a}"}]
            )
            time.sleep(1.5)
            
            faithfulness_score = 1.0 # Default if no claims
            if extr_res.claims:
                # Step 2: Verify claims against context
                verif_prompt = f"Context:\n{c}\n\nClaims:\n{chr(10).join(extr_res.claims)}\n\nFor each claim, verify if it can be directly inferred from the Context. Answer true or false."
                verif_res = client.chat.completions.create(
                    model="mistral-small-latest",
                    response_model=ClaimVerification,
                    messages=[{"role": "user", "content": verif_prompt}]
                )
                
                supported_count = sum(1 for v in verif_res.verifications if v.is_supported)
                total_claims = len(verif_res.verifications)
                faithfulness_score = supported_count / total_claims if total_claims > 0 else 0.0
            
            time.sleep(1.5)
            
            # ==========================================
            # 2. RAGAS ANSWER RELEVANCY ALGORITHM
            # ==========================================
            
            # Step 1: Reverse engineer 3 potential questions from the answer
            rev_res = client.chat.completions.create(
                model="mistral-small-latest",
                response_model=ReverseQuestions,
                messages=[{"role": "user", "content": f"Generate 3 distinct questions that would have resulted in the following answer.\nAnswer: {a}"}]
            )
            
            # Step 2: Calculate embedding cosine similarity
            orig_emb = embedder.embed_query(q)
            similarities = []
            for rev_q in rev_res.questions[:3]:
                rev_emb = embedder.embed_query(rev_q)
                sim = cosine_similarity(orig_emb, rev_emb)
                similarities.append(sim)
                
            relevancy_score = sum(similarities) / len(similarities) if similarities else 0.0
            
            # Add to totals
            total_faithfulness += faithfulness_score
            total_relevancy += relevancy_score
            evaluated += 1
            
            time.sleep(1.5) # Safe rate limit spacing
            
        except Exception as e:
            print(f"\nFailed to grade ticket {i}: {e}")
            time.sleep(5)
            
    if evaluated > 0:
        avg_f = total_faithfulness / evaluated
        avg_r = total_relevancy / evaluated
        print(f"\n--- AUTHENTIC RAGAS RESULTS ---")
        print(f"Faithfulness: {avg_f:.4f}")
        print(f"Answer Relevancy: {avg_r:.4f}")
        
        # Save to evaluation_metrics.json
        metrics_path = "eval/results/evaluation_metrics.json"
        if os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                
            existing["ragas"] = {
                "faithfulness": avg_f,
                "answer_relevancy": avg_r,
                "methodology": "Authentic Ragas Implementation (Claim Extraction + Reverse Embedding)"
            }
            
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            print("Successfully appended scores to evaluation_metrics.json!")
            
if __name__ == "__main__":
    run_custom_ragas()
