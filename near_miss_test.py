"""
near_miss_test.py

Tests the structuring rule on both sides of its real threshold
(count>=5, sum>=$30k) instead of only testing safely below it.
"""

import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta

from tools.feature_eng import engineer_features, get_customer_summary
from tools.detection import apply_structuring_rules

np.random.seed(99)

NEAR_MISS_START_ID = 8000

rows = []

# Tier 1: BELOW count threshold (3-4 same-day deposits, near-CTR amounts).
for i in range(15):
    cid = NEAR_MISS_START_ID + i
    base_day = datetime(2026, 7, 1) + timedelta(days=int(np.random.randint(0, 20)))
    n_txns = int(np.random.randint(3, 5))
    for _ in range(n_txns):
        amount = float(np.random.uniform(7000, 9800))
        ts = base_day + timedelta(hours=float(np.random.uniform(0, 20)))
        rows.append({
            "transaction_id": str(uuid.uuid4())[:8], "customer_id": cid,
            "counterparty_id": int(np.random.randint(1000, 1500)), "amount": round(amount, 2),
            "timestamp": ts.isoformat(), "channel": "cash_deposit", "country": "US", "txn_type": "transfer",
        })

# Tier 2: AT/ABOVE count threshold (5-6 same-day deposits summing >=$30k).
for i in range(15, 25):
    cid = NEAR_MISS_START_ID + i
    base_day = datetime(2026, 7, 1) + timedelta(days=int(np.random.randint(0, 20)))
    n_txns = int(np.random.randint(5, 7))
    for _ in range(n_txns):
        amount = float(np.random.uniform(7000, 9800))
        ts = base_day + timedelta(hours=float(np.random.uniform(0, 20)))
        rows.append({
            "transaction_id": str(uuid.uuid4())[:8], "customer_id": cid,
            "counterparty_id": int(np.random.randint(1000, 1500)), "amount": round(amount, 2),
            "timestamp": ts.isoformat(), "channel": "cash_deposit", "country": "US", "txn_type": "transfer",
        })

df = pd.DataFrame(rows)
df.to_csv("data/near_miss_test.csv", index=False)
print(f"Generated {len(df)} near-miss transactions across 25 customers (15 below-threshold, 10 at-threshold)")
print(df.groupby("customer_id").size().describe())
print()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df_featured = engineer_features(df)

below_ids = set(range(NEAR_MISS_START_ID, NEAR_MISS_START_ID + 15))
at_ids = set(range(NEAR_MISS_START_ID + 15, NEAR_MISS_START_ID + 25))

below_flagged, at_flagged = 0, 0
for cid in sorted(df["customer_id"].unique()):
    summary = get_customer_summary(df_featured, cid)
    result = apply_structuring_rules(summary)
    triggered = result.get("rule_triggered")
    tier = "BELOW-threshold (should NOT flag)" if cid in below_ids else "AT-threshold (should flag)"
    if triggered:
        if cid in below_ids:
            below_flagged += 1
        else:
            at_flagged += 1
    print(f"Customer {cid} [{tier}]: {'FLAGGED' if triggered else 'not flagged'} -- {result.get('trigger_detail')}")

print()
print(f"Below-threshold tier (n=15): {below_flagged} flagged -- false positive rate {below_flagged/15*100:.1f}%")
print(f"At-threshold tier   (n=10): {at_flagged} flagged -- true positive rate {at_flagged/10*100:.1f}%")
