"""CLI demonstration script processing sample student tickets."""

import sys
from src.pipeline import TriagePipeline

SAMPLE_TICKETS = [
    "I bought the Lakshya batch 2 days ago but haven't watched any lecture. Can I get a full refund? Order PW-882194.",
    "My money was debited 4000 Rs via UPI-998877665544 yesterday night, but course is not showing in My Batches. Please fix urgently!",
    "This platform is a complete scam! You cheated me. If you do not refund my money immediately, I am going to file a complaint in the consumer court against PhysicsWallah!",
    "Can I transfer my batch enrollment to my cousin brother who wants to prepare for JEE this year?",
    "Video keeps buffering and giving DRM error code DRM-401 whenever I open the app on my phone. What should I do?"
]

def main():
    print("=" * 60)
    print("PW SUPPORT TICKET TRIAGE AGENT — SAMPLE RUNNER")
    print("=" * 60)
    
    pipeline = TriagePipeline()
    print(f"Loaded {len(pipeline.chunks)} policy chunks across 12 knowledge documents.\n")
    
    for i, ticket in enumerate(SAMPLE_TICKETS, 1):
        print(f"\n--- TICKET #{i} ---")
        print(f"Query: {ticket}")
        
        result = pipeline.process_ticket(ticket)
        cls = result["classification"]
        dec = result["decision"]
        top_ev = result["evidence"][0] if result["evidence"] else None
        
        print(f"-> Classification: Category='{cls['category']}' | Urgency={cls['urgency']}/5 | ChurnRisk={cls['churn_risk']} | ToneAngry={cls['angry_tone']} | LegalThreat={cls['legal_threat']}")
        if top_ev:
            print(f"-> Top Evidence: [{top_ev['document']}] (Dense Cosine: {top_ev['dense_score']:.3f}, BM25 Rank: {top_ev['bm25_rank']})")
        print(f"-> Final Decision: {dec['action']}")
        print(f"-> Decision Reasons: {dec['reasons']}")
        if dec['draft_reply']:
            print(f"-> Draft Reply: {dec['draft_reply']}")
            print(f"-> Citations: {dec['citations']}")
            
    print("\n" + "=" * 60)
    print("Sample run completed successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
