"""
Synthetic AML transaction data generator.
Plants deliberate structuring, layering, and normal-behavior patterns
with a documented ground-truth manifest for benchmarking.

Customer ID ranges:
  1000-1499 : normal population (baseline behavior)
  9001-9005 : structuring / smurfing (sub-$10k rapid clustering)
  9006-9010 : layering (multi-hop fund splitting via intermediates)
  9011-9015 : mixed pattern (both, to test overlapping detection)
"""

import pandas as pd
import numpy as np
import json
import uuid
from datetime import datetime, timedelta

np.random.seed(42)

NUM_NORMAL_CUSTOMERS = 500
TXNS_PER_NORMAL_CUSTOMER = (5, 20)
START_DATE = datetime(2026, 6, 1)
END_DATE = datetime(2026, 7, 24)

CHANNELS = ["wire", "ach", "cash_deposit", "cash_withdrawal", "card"]
COUNTRIES = ["US", "US", "US", "UK", "AE", "SG"]  # weighted toward US


def random_timestamp():
    delta = END_DATE - START_DATE
    seconds = np.random.randint(0, int(delta.total_seconds()))
    return START_DATE + timedelta(seconds=int(seconds))


def make_txn(customer_id, counterparty_id, amount, timestamp, channel, txn_type="transfer"):
    return {
        "transaction_id": str(uuid.uuid4())[:8],
        "customer_id": customer_id,
        "counterparty_id": counterparty_id,
        "amount": round(float(amount), 2),
        "timestamp": timestamp.isoformat(),
        "channel": channel,
        "country": np.random.choice(COUNTRIES),
        "txn_type": txn_type,
    }


def generate_normal_population():
    rows = []
    for cid in range(1000, 1000 + NUM_NORMAL_CUSTOMERS):
        n_txns = np.random.randint(*TXNS_PER_NORMAL_CUSTOMER)
        for _ in range(n_txns):
            amount = np.random.lognormal(mean=6.5, sigma=1.0)
            amount = min(amount, 25000)
            counterparty = np.random.randint(1000, 1000 + NUM_NORMAL_CUSTOMERS)
            rows.append(make_txn(
                cid, counterparty, amount, random_timestamp(),
                np.random.choice(CHANNELS)
            ))
    return rows


def generate_structuring_pattern(customer_id, start_date, num_txns=12, window_hours=18):
    """Sub-$10,000 rapid clustering -- classic smurfing to evade CTR threshold."""
    rows = []
    for _ in range(num_txns):
        amount = np.random.uniform(8800, 9950)
        ts = start_date + timedelta(hours=float(np.random.uniform(0, window_hours)))
        counterparty = np.random.randint(1000, 1500)
        rows.append(make_txn(customer_id, counterparty, amount, ts, "cash_deposit"))
    return rows


def generate_layering_pattern(entry_customer_id, intermediate_id, num_out=8, total_inbound=185000, window_minutes=38):
    """One large inbound transfer, rapidly split across multiple outbound accounts."""
    rows = []
    base_time = random_timestamp()
    rows.append(make_txn(entry_customer_id, intermediate_id, total_inbound, base_time, "wire"))
    per_account = total_inbound / num_out
    for _ in range(num_out):
        ts = base_time + timedelta(minutes=float(np.random.uniform(1, window_minutes)))
        out_customer = np.random.randint(2000, 2500)
        rows.append(make_txn(intermediate_id, out_customer, per_account, ts, "wire"))
    return rows


def generate_mixed_pattern(customer_id):
    """Both structuring and layering behavior on the same entity."""
    rows = generate_structuring_pattern(customer_id, random_timestamp(), num_txns=10, window_hours=24)
    rows += generate_layering_pattern(customer_id + 100000, customer_id, num_out=6, total_inbound=95000, window_minutes=45)
    return rows


def build_ground_truth_manifest():
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "schema_version": "1.0",
        "scenarios": []
    }

    for cid in range(9001, 9006):
        manifest["scenarios"].append({
            "customer_id": cid,
            "pattern_type": "structuring",
            "expected_detection": "rule_engine",
            "expected_statute": "31 CFR 1010.311",
            "description": f"12 transactions between $8,800-$9,950 within 18-hour window, customer {cid}",
            "expected_risk_tier": "HIGH"
        })

    for cid in range(9006, 9011):
        manifest["scenarios"].append({
            "customer_id": cid,
            "pattern_type": "layering",
            "expected_detection": "graph_engine",
            "expected_statute": "31 CFR 1010.311 (layering indicator, FATF)",
            "description": f"Customer {cid} acts as intermediate node splitting inbound transfer across 6-8 accounts within tight time window",
            "expected_risk_tier": "HIGH"
        })

    for cid in range(9011, 9016):
        manifest["scenarios"].append({
            "customer_id": cid,
            "pattern_type": "mixed_structuring_layering",
            "expected_detection": "rule_engine+graph_engine",
            "expected_statute": "31 CFR 1010.311",
            "description": f"Customer {cid} exhibits both structuring and layering behavior",
            "expected_risk_tier": "HIGH"
        })

    return manifest


def main():
    all_rows = []

    print("Generating normal population...")
    all_rows += generate_normal_population()

    print("Planting structuring patterns (9001-9005)...")
    for cid in range(9001, 9006):
        all_rows += generate_structuring_pattern(cid, random_timestamp())

    print("Planting layering patterns (9006-9010)...")
    for cid in range(9006, 9011):
        all_rows += generate_layering_pattern(cid + 5000, cid)

    print("Planting mixed patterns (9011-9015)...")
    for cid in range(9011, 9016):
        all_rows += generate_mixed_pattern(cid)

    df = pd.DataFrame(all_rows)
    df = df.sort_values("timestamp").reset_index(drop=True)

    output_path = "data/transactions.csv"
    df.to_csv(output_path, index=False)
    print(f"Wrote {len(df)} transactions to {output_path}")

    manifest = build_ground_truth_manifest()
    manifest_path = "data/ground_truth_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote ground truth manifest to {manifest_path}")
    print(f"Total planted scenarios: {len(manifest['scenarios'])}")


if __name__ == "__main__":
    main()
