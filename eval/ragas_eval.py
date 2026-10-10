"""Run custom Ragas evaluation for the triage pipeline without the broken ragas library."""

import os
import csv
import json
import time
from tqdm import tqdm
from dotenv import load_dotenv

from src.pipeline import TriagePipeline
from eval.custom_ragas import run_custom_ragas

load_dotenv()

def run_evaluation(
    dataset_path: str = "eval/tickets.csv",
    out_dir: str = "eval/results",
):
    os.makedirs(out_dir, exist_ok=True)
    cache_path = os.path.join(out_dir, "ragas_cache.json")
    
    if os.path.exists(cache_path):
        print(f"Loading cached generated data from {cache_path}...")
    else:
        # Initialize pipeline
        pipeline = TriagePipeline()
        
        tickets_data = []
        with open(dataset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                tickets_data.append(r)
                
        print(f"Loaded {len(tickets_data)} tickets for Ragas evaluation.")
        
        questions = []
        answers = []
        contexts = []
        
        print("Running pipeline to gather data...")
        for row in tqdm(tickets_data, desc="Gathering Ragas Eval Data"):
            t_text = row["ticket"]
            res = pipeline.process_ticket(t_text)
            
            if res.get("draft") and res["draft"].get("reply_text"):
                questions.append(t_text)
                answers.append(res["draft"]["reply_text"])
                ticket_contexts = [doc["content"] for doc in res.get("retrieval", [])]
                contexts.append(ticket_contexts)

            # Strict 15 RPM limit for Gemini Flash free tier
            time.sleep(8.5)

        if not questions:
            print("No tickets generated an answer. Check pipeline configuration.")
            return
            
        print("Saving generated data to cache...")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"questions": questions, "answers": answers, "contexts": contexts}, f)
            
    # Now run the custom LLM judge for faithfulness and relevancy!
    run_custom_ragas()

if __name__ == "__main__":
    run_evaluation()
