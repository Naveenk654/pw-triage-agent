"""Comprehensive evaluation runner calculating classification, escalation, retrieval, and Jev metrics."""

import os
import csv
import json
import time
import random
import numpy as np
from typing import List, Dict, Any
from dotenv import load_dotenv
load_dotenv()
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from tqdm import tqdm
from src.pipeline import TriagePipeline


def run_full_evaluation(
    dataset_path: str = "eval/tickets.csv",
    out_dir: str = "eval/results",
    disable_cache: bool = True
):
    os.makedirs(out_dir, exist_ok=True)
    
    # Load dataset
    tickets_data = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            tickets_data.append(r)
            
    print(f"Loaded {len(tickets_data)} tickets from {dataset_path}.")
    
    pipeline = TriagePipeline()
    if disable_cache:
        pipeline.llm_client.enable_cache = False
        
    y_true_cat = []
    y_pred_cat = []
    y_true_esc = []
    y_pred_esc = []
    
    latencies = []
    results_dump = []
    
    # Track retrieval recall
    retrieval_hits_1 = 0
    retrieval_hits_3 = 0
    retrieval_hits_5 = 0
    
    # Jev experiment 2: Choice order sensitivity tracking
    order_changes = 0
    
    start_eval_time = time.time()
    
    for row in tqdm(tickets_data, desc="Evaluating Tickets"):
        t_id = row["ticket_id"]
        t_text = row["ticket"]
        exp_cat = row["expected_category"]
        exp_esc = (row["expected_escalate"].strip().upper() == "TRUE")
        exp_src = row["expected_source"]
        
        t0 = time.time()
        res = pipeline.process_ticket(t_text)
        lat = time.time() - t0
        latencies.append(lat)
        
        from src.classifier import to_parent_category
        pred_cat_raw = res["classification"]["category"]
        pred_cat = res["classification"].get("parent_category") or to_parent_category(pred_cat_raw)
        act_str = str(res["decision"]["action"]).replace("TriageAction.", "")
        pred_esc = (act_str in ["ESCALATE", "APPROVAL_REQUIRED"])
        
        y_true_cat.append(exp_cat)
        y_pred_cat.append(pred_cat)
        
        y_true_esc.append(exp_esc)
        y_pred_esc.append(pred_esc)
        
        # Check retrieval recall against expected source
        retrieved_docs = [ev["document"] for ev in res.get("retrieval", [])]
        if exp_src != "none":
            if retrieved_docs and exp_src == retrieved_docs[0]:
                retrieval_hits_1 += 1
            if exp_src in retrieved_docs[:3]:
                retrieval_hits_3 += 1
            if exp_src in retrieved_docs[:5]:
                retrieval_hits_5 += 1
                
        results_dump.append({
            "ticket_id": t_id,
            "text": t_text,
            "exp_cat": exp_cat,
            "pred_cat": pred_cat,
            "exp_esc": exp_esc,
            "pred_esc": pred_esc,
            "reasons": res["decision"]["reasons"],
            "latency_s": lat
        })
        
        # Rate limit: max 15 requests per minute for Gemini free tier (2 calls per ticket)
        # Sleep 8.5 seconds per ticket = ~14 calls per minute
        time.sleep(8.5)

    total_eval_duration = time.time() - start_eval_time
    
    # 1. Classification Metrics
    cat_labels = sorted(list(set(y_true_cat + y_pred_cat)))
    acc_cat = accuracy_score(y_true_cat, y_pred_cat)
    p_cat, r_cat, f1_cat, _ = precision_recall_fscore_support(y_true_cat, y_pred_cat, average="macro", zero_division=0)
    conf_mat = confusion_matrix(y_true_cat, y_pred_cat, labels=cat_labels).tolist()
    
    # 2. Escalation Metrics
    acc_esc = accuracy_score(y_true_esc, y_pred_esc)
    p_esc, r_esc, f1_esc, _ = precision_recall_fscore_support(y_true_esc, y_pred_esc, average="binary", zero_division=0)
    
    # Safety metrics
    # Missed-escalation = True escalate predicted as AUTO_REPLY (False Negative)
    fn = sum(1 for yt, yp in zip(y_true_esc, y_pred_esc) if yt and not yp)
    tp = sum(1 for yt, yp in zip(y_true_esc, y_pred_esc) if yt and yp)
    fp = sum(1 for yt, yp in zip(y_true_esc, y_pred_esc) if not yt and yp)
    tn = sum(1 for yt, yp in zip(y_true_esc, y_pred_esc) if not yt and not yp)
    
    missed_esc_rate = fn / max(1, (fn + tp))
    false_esc_rate = fp / max(1, (fp + tn))
    auto_reply_rate = sum(1 for p in y_pred_esc if not p) / len(y_pred_esc)

    # 3. Retrieval Recall
    eval_src_count = sum(1 for r in tickets_data if r["expected_source"] != "none")
    recall_1 = retrieval_hits_1 / max(1, eval_src_count)
    recall_3 = retrieval_hits_3 / max(1, eval_src_count)
    recall_5 = retrieval_hits_5 / max(1, eval_src_count)

    # 4. Latency percentiles
    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))

    metrics = {
        "dataset_size": len(tickets_data),
        "total_eval_duration_s": total_eval_duration,
        "classification": {
            "accuracy": acc_cat,
            "macro_precision": p_cat,
            "macro_recall": r_cat,
            "macro_f1": f1_cat,
            "labels": cat_labels,
            "confusion_matrix": conf_mat
        },
        "escalation": {
            "accuracy": acc_esc,
            "precision": p_esc,
            "recall": r_esc,
            "f1": f1_esc,
            "missed_escalation_rate": missed_esc_rate,
            "false_escalation_rate": false_esc_rate,
            "automation_rate": auto_reply_rate,
            "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}
        },
        "retrieval": {
            "evaluated_queries": eval_src_count,
            "recall_at_1": recall_1,
            "recall_at_3": recall_3,
            "recall_at_5": recall_5
        },
        "performance": {
            "p50_latency_s": p50_lat,
            "p95_latency_s": p95_lat,
            "mean_latency_s": float(np.mean(latencies))
        }
    }
    
    # Save metrics JSON
    metrics_path = os.path.join(out_dir, "evaluation_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Metrics saved to {metrics_path}.")
    return metrics


if __name__ == "__main__":
    run_full_evaluation()
