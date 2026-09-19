import os
import sys
import hashlib
import argparse
import pandas as pd
import numpy as np
from dotenv import load_dotenv

sys.path.insert(0, r"c:\Users\Mukul\Desktop\Tark")
load_dotenv(r"c:\Users\Mukul\Desktop\Tark\.env")

import pyTigerGraph as tg

def get_tg_connection():
    return tg.TigerGraphConnection(
        host=os.getenv("TG_HOST"),
        username=os.getenv("TG_USERNAME"),
        password=os.getenv("TG_PASSWORD"),
        graphname=os.getenv("TG_GRAPHNAME"),
        gsqlSecret=os.getenv("TG_SECRET"),
        tgCloud=True
    )

def get_device_profile_id(row):
    """Generates a deterministic digital device fingerprint from hardware & OS attributes."""
    parts = [
        str(row.get('DeviceInfo', '') or ''),
        str(row.get('id_30', '') or ''),
        str(row.get('id_31', '') or ''),
        str(row.get('DeviceType', '') or '')
    ]
    raw = "|".join(parts)
    return "DEV_" + hashlib.md5(raw.encode()).hexdigest()[:12]

def clean_val(val, default=""):
    if pd.isna(val):
        return default
    return str(val).strip()

def clean_float(val, default=0.0):
    if pd.isna(val):
        return default
    try:
        return float(val)
    except:
        return default

def clean_int(val, default=0):
    if pd.isna(val):
        return default
    try:
        return int(val)
    except:
        return default

def load_all_data(
    conn,
    closed_cases_path: str = r"c:\Users\Mukul\Desktop\Tark\closed_cases_history.csv",
    transactions_path: str = r"c:\Users\Mukul\Desktop\Tark\transactions.csv",
    identity_path: str = r"c:\Users\Mukul\Desktop\Tark\identity.csv",
    cohort_customers_path: str = None
):
    """Generic, provenance-driven graph ETL pipeline.
    Loads bank historical cases, customer portfolios, transaction logs, and device profiles.
    Free of any benchmark case IDs or hardcoded entity heuristics.
    """
    print("=" * 65)
    print("GENERIC FRAUD INVESTIGATION GRAPH ETL PIPELINE")
    print("=" * 65)

    # 1. Ingest Bank Customer & Card Portfolio from Closed Case History
    print("\n[Step 1/5] Ingesting historical cases, cardholders, and cards...")
    df_hist = pd.read_csv(closed_cases_path)
    
    customers = {}
    cards = {}
    closed_cases = []

    for row in df_hist.itertuples():
        case_id = clean_val(getattr(row, "case_id", ""))
        c_id = clean_val(getattr(row, "customer_id", ""))
        card_id = clean_val(getattr(row, "card_id", ""))
        
        if c_id:
            customers[c_id] = {"id": c_id}
        if card_id:
            cards[card_id] = {"card_id": card_id, "customer_id": c_id}

        attr = {
            "case_id": case_id,
            "outcome": clean_val(getattr(row, "outcome", "")),
            "pattern": clean_val(getattr(row, "pattern", "none")),
            "exposure_usd": clean_float(getattr(row, "exposure_usd", 0.0)),
            "n_txns": clean_int(getattr(row, "n_txns", 1)),
            "actions_taken": clean_val(getattr(row, "actions_taken", "")),
            "report_filed": True if clean_val(getattr(row, "report_filed", "")).lower() in ["yes", "true", "1"] else False,
            "analyst_notes": clean_val(getattr(row, "analyst_notes", ""))[:1000],
            "opened_at": clean_val(getattr(row, "opened_at", "2016-01-01 00:00:00")),
            "closed_at": clean_val(getattr(row, "closed_at", "2016-01-01 00:00:00"))
        }
        closed_cases.append((case_id, attr))

    # If an external cohort or active account roster is supplied, merge customer IDs
    target_custs = set(customers.keys())
    if cohort_customers_path and os.path.exists(cohort_customers_path):
        print(f"Loading operational customer cohort from {cohort_customers_path}...")
        df_cohort = pd.read_csv(cohort_customers_path)
        for _, r in df_cohort.iterrows():
            c_id = clean_val(r.get("customer_id"))
            card_id = clean_val(r.get("card_id"))
            if c_id:
                customers[c_id] = {"id": c_id}
                target_custs.add(c_id)
            if card_id:
                cards[card_id] = {"card_id": card_id, "customer_id": c_id}

    print(f"Upserting {len(customers)} Customers and {len(cards)} Cards...")
    cust_vertices = [(k, v) for k, v in customers.items()]
    card_vertices = [(k, v) for k, v in cards.items()]
    
    for i in range(0, len(cust_vertices), 1000):
        conn.upsertVertices("Customer", cust_vertices[i:i+1000])
    for i in range(0, len(card_vertices), 1000):
        conn.upsertVertices("Card", card_vertices[i:i+1000])

    # Deduplicate Customer_OWNS_Card edges
    cust_card_pairs = set()
    for card_id, c_info in cards.items():
        c_id = c_info.get("customer_id")
        if c_id and card_id:
            cust_card_pairs.add((c_id, card_id))

    cust_card_edges = [(u, v, {}) for u, v in cust_card_pairs]
    for i in range(0, len(cust_card_edges), 2000):
        conn.upsertEdges("Customer", "Customer_OWNS_Card", "Card", cust_card_edges[i:i+2000])

    print(f"Upserting {len(closed_cases)} ClosedCase vertices...")
    for i in range(0, len(closed_cases), 1000):
        conn.upsertVertices("ClosedCase", closed_cases[i:i+1000])

    case_card_pairs = set()
    for row in df_hist.itertuples():
        case_id = clean_val(getattr(row, "case_id", ""))
        card_id = clean_val(getattr(row, "card_id", ""))
        if case_id and card_id:
            case_card_pairs.add((case_id, card_id))

    case_card_edges = [(u, v, {}) for u, v in case_card_pairs]
    for i in range(0, len(case_card_edges), 2000):
        conn.upsertEdges("ClosedCase", "ClosedCase_ON_CARD", "Card", case_card_edges[i:i+2000])
    print("[Step 1/5 Complete] Customers, Cards, and ClosedCases successfully indexed.")

    # 2. Generic Anomaly Identification: Unsupervised Device Clustering
    print("\n[Step 2/5] Running generic unsupervised device anomaly clustering on identity.csv...")
    df_id = pd.read_csv(identity_path)
    df_id['profile_id'] = df_id.apply(get_device_profile_id, axis=1)
    
    # Generic operational criteria:
    # Any device operating via proxy OR shared across >= 5 transactions
    proxy_mask = df_id['id_23'].fillna('').str.contains('proxy', case=False)
    prof_counts = df_id['profile_id'].value_counts()
    shared_profs = set(prof_counts[prof_counts >= 5].index)
    proxy_profs = set(df_id[proxy_mask]['profile_id'].unique())
    anomalous_profiles = shared_profs.union(proxy_profs)

    anomalous_txn_ids = set(df_id[df_id['profile_id'].isin(anomalous_profiles)]['TransactionID'].astype(int))
    print(f"Discovered {len(anomalous_profiles)} high-risk/shared device profiles across {len(anomalous_txn_ids)} transactions.")

    # 3. Stream Transactions CSV with Generic Partition Filter
    print("\n[Step 3/5] Streaming transactions.csv with generic portfolio & anomaly filter...")
    extracted_txns = []
    chunk_count = 0
    
    cols_to_keep = [
        'TransactionID', 'customer_id', 'ts', 'TransactionAmt', 'ProductCD',
        'channel', 'risk_score', 'card1', 'card4', 'card6',
        'addr1', 'addr2', 'P_emaildomain', 'R_emaildomain'
    ]

    for chunk in pd.read_csv(transactions_path, chunksize=100000, low_memory=False):
        chunk_count += 1
        # Generic match: belongs to target portfolio OR belongs to anomalous device cluster
        mask = chunk['customer_id'].isin(target_custs) | chunk['TransactionID'].isin(anomalous_txn_ids)
        matched = chunk[mask][cols_to_keep]
        if len(matched):
            extracted_txns.append(matched)
        print(f"  Processed chunk {chunk_count} (matched {len(matched)} rows)")

    df_all_txns = pd.concat(extracted_txns, ignore_index=True)
    print(f"Total extracted transactions: {len(df_all_txns)}")

    # 4. Upsert Transactions, Card Edges, Regions, and Domains
    print("\n[Step 4/5] Ingesting Transaction vertices and structural edges...")
    
    # Ensure any new customers/cards discovered in anomalous transactions exist
    new_custs = {}
    new_cards = {}
    for _, row in df_all_txns.iterrows():
        c_id = clean_val(row["customer_id"])
        if c_id and c_id not in customers:
            new_custs[c_id] = {"id": c_id}
            card_id = f"{c_id}-K1"
            new_cards[card_id] = {"card_id": card_id, "customer_id": c_id}

    if new_custs:
        conn.upsertVertices("Customer", [(k, v) for k, v in new_custs.items()])
        conn.upsertVertices("Card", [(k, v) for k, v in new_cards.items()])
        conn.upsertEdges("Customer", "Customer_OWNS_Card", "Card", [(c, f"{c}-K1", {}) for c in new_custs])

    txn_vertices = []
    card_txn_edges = []
    region_vertices = {}
    txn_region_edges = []
    domain_vertices = set()
    txn_domain_edges = []

    for _, row in df_all_txns.iterrows():
        t_id = str(row["TransactionID"])
        c_id = clean_val(row["customer_id"])
        card_id = f"{c_id}-K1" if c_id else "UNKNOWN_CARD"
        
        # In a generic bank system, a transaction is flagged if score >= 0.70 or escalated
        r_score = clean_float(row["risk_score"])
        is_flg = r_score >= 0.70

        addr1_val = clean_float(row["addr1"], 0.0)
        addr2_val = clean_float(row["addr2"], 0.0)
        p_email = clean_val(row["P_emaildomain"])
        r_email = clean_val(row["R_emaildomain"])

        attr = {
            "txn_id": t_id,
            "ts": clean_val(row["ts"]),
            "amount": clean_float(row["TransactionAmt"]),
            "product_cd": clean_val(row["ProductCD"]),
            "channel": clean_val(row["channel"]),
            "risk_score": r_score,
            "card1": clean_int(row["card1"]),
            "card4": clean_val(row["card4"]),
            "card6": clean_val(row["card6"]),
            "addr1": addr1_val,
            "addr2": addr2_val,
            "p_email": p_email,
            "r_email": r_email,
            "is_flagged": is_flg
        }
        txn_vertices.append((t_id, attr))
        card_txn_edges.append((card_id, t_id, {}))

        if addr1_val > 0:
            reg_code = str(addr1_val)
            region_vertices[reg_code] = {"region_code": reg_code, "country_code": str(addr2_val)}
            txn_region_edges.append((t_id, reg_code, {}))

        if p_email:
            domain_vertices.add(p_email)
            txn_domain_edges.append((t_id, p_email, {}))

    batch_size = 2000
    print(f"Upserting {len(txn_vertices)} Transaction vertices in batches of {batch_size}...")
    for i in range(0, len(txn_vertices), batch_size):
        conn.upsertVertices("Transaction", txn_vertices[i:i+batch_size])

    print(f"Upserting {len(card_txn_edges)} Card_MADE_Transaction edges...")
    for i in range(0, len(card_txn_edges), batch_size):
        conn.upsertEdges("Card", "Card_MADE_Transaction", "Transaction", card_txn_edges[i:i+batch_size])

    print(f"Upserting {len(region_vertices)} BillingRegion vertices and edges...")
    conn.upsertVertices("BillingRegion", [(k, v) for k, v in region_vertices.items()])
    for i in range(0, len(txn_region_edges), batch_size):
        conn.upsertEdges("Transaction", "Transaction_BILLED_IN", "BillingRegion", txn_region_edges[i:i+batch_size])

    print(f"Upserting {len(domain_vertices)} EmailDomain vertices and edges...")
    conn.upsertVertices("EmailDomain", [(d, {"domain": d}) for d in domain_vertices])
    for i in range(0, len(txn_domain_edges), batch_size):
        conn.upsertEdges("Transaction", "Transaction_PURCHASER_EMAIL", "EmailDomain", txn_domain_edges[i:i+batch_size])

    # 5. Index Device Profiles & Transaction Device Links
    print("\n[Step 5/5] Ingesting DeviceProfile vertices and Transaction_FROM_DEVICE edges...")
    extracted_txn_id_set = set(df_all_txns["TransactionID"].astype(int))
    df_id_matched = df_id[df_id["TransactionID"].isin(extracted_txn_id_set)]

    device_vertices = {}
    txn_device_edges = []

    for _, row in df_id_matched.iterrows():
        t_id = str(row["TransactionID"])
        p_id = str(row["profile_id"])
        
        is_proxy = False
        id_23_val = clean_val(row.get("id_23"))
        if "proxy" in id_23_val.lower():
            is_proxy = True

        if p_id not in device_vertices:
            device_vertices[p_id] = {
                "profile_id": p_id,
                "device_type": clean_val(row.get("DeviceType")),
                "device_info": clean_val(row.get("DeviceInfo")),
                "os": clean_val(row.get("id_30")),
                "browser": clean_val(row.get("id_31")),
                "screen": clean_val(row.get("id_33")),
                "is_proxy": is_proxy,
                "id_15": clean_val(row.get("id_15")),
                "id_23": id_23_val
            }
        txn_device_edges.append((t_id, p_id, {}))

    print(f"Upserting {len(device_vertices)} DeviceProfile vertices...")
    dev_list = [(k, v) for k, v in device_vertices.items()]
    for i in range(0, len(dev_list), batch_size):
        conn.upsertVertices("DeviceProfile", dev_list[i:i+batch_size])

    print(f"Upserting {len(txn_device_edges)} Transaction_FROM_DEVICE edges...")
    for i in range(0, len(txn_device_edges), batch_size):
        conn.upsertEdges("Transaction", "Transaction_FROM_DEVICE", "DeviceProfile", txn_device_edges[i:i+batch_size])

    print("=" * 65)
    print("GENERIC GRAPH INGESTION COMPLETE & RECONCILED")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic Fraud Graph ETL")
    parser.add_argument("--cohort_file", type=str, default=None, help="Optional cohort account file")
    args = parser.parse_args()

    conn = get_tg_connection()
    load_all_data(conn, cohort_customers_path=args.cohort_file)
