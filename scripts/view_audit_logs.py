# -*- coding: utf-8 -*-
"""
Sia AI Assistant - CLI Audit Log Viewer & Security Observer
Provides structured terminal inspection, filtering, and export for system audit logs.
"""

import sys
import os
import argparse
import json
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.audit_logger import get_recent_audit_logs


def main():
    parser = argparse.ArgumentParser(description="Sia Assistant - Audit Log Viewer & Observer")
    parser.add_argument("--limit", type=int, default=20, help="Number of audit log entries to fetch (default: 20)")
    parser.add_argument("--risk", type=str, choices=["SAFE", "ALLOW", "CONFIRM", "DENY"], help="Filter by risk level")
    parser.add_argument("--json", action="store_true", help="Output audit logs as formatted JSON")
    parser.add_argument("--csv", type=str, help="Export audit logs to specified CSV file path")
    args = parser.parse_args()

    logs = get_recent_audit_logs(limit=args.limit)

    if args.risk:
        target_risk = args.risk.upper()
        logs = [l for l in logs if l.get("risk_level", "").upper() == target_risk]

    if args.json:
        print(json.dumps(logs, indent=2))
        return

    if args.csv:
        if not logs:
            print("No logs available to export.")
            return
        fieldnames = list(logs[0].keys())
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(logs)
        print(f"Exported {len(logs)} audit log records to CSV: {args.csv}")
        return

    print("=========================================================================================")
    print(" SIA ASSISTANT - AUDIT TRAIL & SYSTEM CONTROL LOGS")
    print("=========================================================================================")
    if not logs:
        print(" (No audit records found)")
        return

    header_fmt = "{:<24} | {:<22} | {:<8} | {:<14} | {:<20}"
    print(header_fmt.format("TIMESTAMP", "ACTION", "RISK", "STATUS", "DETAILS"))
    print("-" * 93)

    for record in logs:
        ts = str(record.get("timestamp", ""))[:23]
        act = str(record.get("action_name", ""))[:22]
        risk = str(record.get("risk_level", ""))[:8]
        status = str(record.get("status", ""))[:14]
        details = str(record.get("details", ""))[:20]

        print(header_fmt.format(ts, act, risk, status, details))

    print("-" * 93)
    print(f" Total records shown: {len(logs)}\n")


if __name__ == "__main__":
    main()

