"""Threshold sweep script analyzing the impact of urgency/confidence thresholds and deterministic rules."""

import os
import json
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
load_dotenv()
from src.pipeline import TriagePipeline


def run_threshold_sweep(dataset_path="eval/tickets.csv", out_dir="eval/results"):
    os.makedirs(out_dir, exist_ok=True)
    pipeline = TriagePipeline()
    
    tickets = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            tickets.append(r)
            
    # Sweep urgency escalation threshold: [2, 3, 4, 5]
    urgency_thresholds = [2, 3, 4, 5]
    automation_rates_with_rules = []
    automation_rates_no_rules = []
    
    for thresh in urgency_thresholds:
        # Run with deterministic rules enabled
        pipeline.decision_engine.urgency_threshold = thresh
        
        esc_count_rules = 0
        esc_count_no_rules = 0
        
        for t in tickets:
            # Process ticket
            res = pipeline.process_ticket(t["ticket"])
            if res["decision"]["action"] == "ESCALATE":
                esc_count_rules += 1
                
            # Simulate without deterministic keyword/amount rules
            # Only urgency boundary
            urg = res["classification"]["urgency"]
            if urg >= thresh or not res["answerability"].get("dense_pass", True):
                esc_count_no_rules += 1
                
        auto_rate_rules = (len(tickets) - esc_count_rules) / len(tickets)
        auto_rate_no_rules = (len(tickets) - esc_count_no_rules) / len(tickets)
        
        automation_rates_with_rules.append(auto_rate_rules)
        automation_rates_no_rules.append(auto_rate_no_rules)
        
    # Plot Threshold Sweep
    plt.figure(figsize=(8, 5))
    plt.plot(urgency_thresholds, automation_rates_with_rules, marker='o', label='With Deterministic Safety Rules', color='#1E88E5', linewidth=2)
    plt.plot(urgency_thresholds, automation_rates_no_rules, marker='s', linestyle='--', label='Without Deterministic Rules (Urgency Only)', color='#D81B60', linewidth=2)
    plt.title("Automation Rate vs Urgency Escalation Threshold", fontsize=13, fontweight='bold')
    plt.xlabel("Urgency Escalation Cutoff (Lower = More Conservative)", fontsize=11)
    plt.ylabel("Automation Rate (% Auto-Replied)", fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='lower right')
    plt.tight_layout()
    
    plot_path = os.path.join(out_dir, "threshold_sweep_plot.png")
    plt.savefig(plot_path, dpi=200)
    plt.close()
    
    sweep_results = {
        "urgency_thresholds": urgency_thresholds,
        "automation_rates_with_deterministic_rules": automation_rates_with_rules,
        "automation_rates_without_rules": automation_rates_no_rules,
        "plot_saved_to": plot_path
    }
    
    with open(os.path.join(out_dir, "threshold_sweep_results.json"), "w", encoding="utf-8") as f:
        json.dump(sweep_results, f, indent=2)
        
    print(f"Threshold sweep plot generated and saved to {plot_path}.")
    return sweep_results

if __name__ == "__main__":
    run_threshold_sweep()
