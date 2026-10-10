"""Cost calculation and cumulative spend tracking."""

import sqlite3
import os
from typing import Dict, Any, Optional


class CostTracker:
    def __init__(self, config: Dict[str, Any], db_path: str = "data/triage_logs.db"):
        self.pricing = config.get("pricing", {})
        self.jev_rate = self.pricing.get("jev_per_million", 0.042)
        self.gemini_in_rate = self.pricing.get("gemini_input_per_million", 0.075)
        self.gemini_out_rate = self.pricing.get("gemini_output_per_million", 0.30)
        self.groq_in_rate = self.pricing.get("groq_input_per_million", 0.59)
        self.groq_out_rate = self.pricing.get("groq_output_per_million", 0.79)
        self.jev_budget = config.get("jev", {}).get("budget_usd", 5.0)
        self.db_path = db_path

    def calculate_cost(
        self,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> Dict[str, float]:
        """Calculates estimated list-price cost and actual cash spend."""
        est_cost = 0.0
        
        if provider == "jev":
            total_tokens = input_tokens + output_tokens
            est_cost = (total_tokens / 1_000_000.0) * self.jev_rate
            actual_spend = est_cost
        elif provider == "gemini":
            est_cost = (input_tokens / 1_000_000.0) * self.gemini_in_rate + \
                       (output_tokens / 1_000_000.0) * self.gemini_out_rate
            # For Gemini development using Google AI Studio free tier: actual spend is $0.0
            actual_spend = 0.0
        elif provider == "groq":
            est_cost = (input_tokens / 1_000_000.0) * self.groq_in_rate + \
                       (output_tokens / 1_000_000.0) * self.groq_out_rate
            actual_spend = 0.0
        else:
            actual_spend = 0.0
            
        return {
            "estimated_cost_usd": est_cost,
            "actual_spend_usd": actual_spend
        }

    def check_budget_status(self, cumulative_jev_cost: float) -> Dict[str, Any]:
        """Warns if cumulative estimated Jev cost approaches configured budget."""
        pct_used = (cumulative_jev_cost / self.jev_budget) * 100.0 if self.jev_budget > 0 else 0.0
        warning = pct_used >= 80.0
        return {
            "budget_usd": self.jev_budget,
            "cumulative_spent_usd": cumulative_jev_cost,
            "percentage_used": pct_used,
            "budget_warning": warning
        }
