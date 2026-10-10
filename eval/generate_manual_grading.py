"""Script generating eval/manual_grading.csv for human review."""

import csv
import os
from src.pipeline import TriagePipeline

def generate_manual_grading(dataset_path="eval/tickets.csv", out_path="eval/manual_grading.csv", sample_count=30):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pipeline = TriagePipeline()
    
    tickets = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            tickets.append(r)
            
    # Sample up to sample_count tickets
    sampled = tickets[:sample_count]
    
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ticket_id",
            "query",
            "decision",
            "draft_reply",
            "citations",
            "supported?",
            "citation_correct?",
            "correctness_1_5",
            "groundedness_1_5",
            "tone_1_5"
        ])
        
        for t in sampled:
            res = pipeline.process_ticket(t["ticket"])
            dec = res["decision"]
            writer.writerow([
                t["ticket_id"],
                t["ticket"],
                dec["action"],
                dec["draft_reply"] or "[ESCALATED - NO REPLY DISPATCHED]",
                "; ".join(dec["citations"]),
                "",  # blank for human review
                "",  # blank for human review
                "",  # blank for human review
                "",  # blank for human review
                ""   # blank for human review
            ])
            
    print(f"Generated manual grading template at {out_path} with {len(sampled)} tickets.")

if __name__ == "__main__":
    generate_manual_grading()
