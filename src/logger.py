"""SQLite audit logging for every ticket decision and cost event."""

import sqlite3
import os
import json
from typing import Dict, Any


class TriageLogger:
    def __init__(self, db_path: str = "data/triage_logs.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ticket_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ticket_text TEXT,
                    backend_used TEXT,
                    category TEXT,
                    category_confidence REAL,
                    urgency INTEGER,
                    rule_flags TEXT,
                    top_dense_score REAL,
                    is_answerable INTEGER,
                    verification_status INTEGER,
                    decision TEXT,
                    reasons TEXT,
                    total_latency_s REAL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    estimated_cost_usd REAL,
                    actual_spend_usd REAL,
                    provider TEXT,
                    errors TEXT
                )
            """)

    def log_ticket(self, log_entry: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ticket_audit_logs (
                    ticket_text, backend_used, category, category_confidence,
                    urgency, rule_flags, top_dense_score, is_answerable,
                    verification_status, decision, reasons, total_latency_s,
                    input_tokens, output_tokens, estimated_cost_usd,
                    actual_spend_usd, provider, errors
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_entry.get("ticket_text", ""),
                log_entry.get("backend_used", ""),
                log_entry.get("category", ""),
                log_entry.get("category_confidence", 0.0),
                log_entry.get("urgency", 1),
                json.dumps(log_entry.get("rule_flags", {})),
                log_entry.get("top_dense_score", 0.0),
                1 if log_entry.get("is_answerable", False) else 0,
                1 if log_entry.get("verification_status", False) else 0,
                log_entry.get("decision", ""),
                json.dumps(log_entry.get("reasons", [])),
                log_entry.get("total_latency_s", 0.0),
                log_entry.get("input_tokens", 0),
                log_entry.get("output_tokens", 0),
                log_entry.get("estimated_cost_usd", 0.0),
                log_entry.get("actual_spend_usd", 0.0),
                log_entry.get("provider", ""),
                json.dumps(log_entry.get("errors", []))
            ))

    def get_summary_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(estimated_cost_usd), SUM(actual_spend_usd) FROM ticket_audit_logs")
            row = cursor.fetchone()
            total_tickets = row[0] or 0
            est_cost = row[1] or 0.0
            act_spend = row[2] or 0.0
            
            cursor.execute("SELECT decision, COUNT(*) FROM ticket_audit_logs GROUP BY decision")
            decisions = dict(cursor.fetchall())
            
        return {
            "total_tickets_logged": total_tickets,
            "estimated_cost_total": est_cost,
            "actual_spend_total": act_spend,
            "decisions": decisions
        }
