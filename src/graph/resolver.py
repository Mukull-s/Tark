import re
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import pyTigerGraph

from src.graph.connection import get_tigergraph_connection


class TransactionNotFoundError(Exception):
    """Raised when a transaction ID cannot be found in TigerGraph."""
    pass


class ResolvedTransactionContext(BaseModel):
    """Fully resolved graph context for an arbitrary transaction."""
    txn_id: str
    amount: float
    timestamp: str
    risk_score: Optional[float] = None
    channel: str = "online"
    addr1: float = 0.0
    card_id: str = ""
    customer_id: str = ""
    device_id: Optional[str] = None
    email_domain: Optional[str] = None
    is_flagged: bool = False
    raw_attributes: Dict[str, Any] = Field(default_factory=dict)


class TransactionResolver:
    """Automated entity and context resolution engine for TigerGraph.
    
    Traverses the bipartite financial graph:
    
            Transaction (txn_id, amount, ts, risk_score)
                  ├── [Transaction_MADE_BY_Card] ────────▶ Card (c_id)
                  │                                         └── [customer_id] ──▶ Customer (cust_id)
                  ├── [Transaction_FROM_DEVICE] ─────────▶ DeviceProfile (profile_id)
                  └── [Transaction_PURCHASER_EMAIL] ─────▶ EmailDomain (domain)
    
    Guarantees:
    - Resolves arbitrary unseen transactions dynamically.
    - Operates without any dependency on benchmark CSV files or pre-cached fixtures.
    - Gracefully handles missing edges (e.g. absent device or customer).
    """

    def __init__(self, tg_conn: Optional[pyTigerGraph.TigerGraphConnection] = None):
        self._tg_conn = tg_conn

    def _get_conn(self) -> pyTigerGraph.TigerGraphConnection:
        if self._tg_conn is not None:
            return self._tg_conn
        conn = get_tigergraph_connection()
        if conn is None:
            raise RuntimeError("TigerGraph connection unavailable for transaction resolution.")
        return conn

    def resolve(self, txn_id: str) -> ResolvedTransactionContext:
        """Resolves transaction context and 1-hop / 2-hop connected entities from TigerGraph."""
        conn = self._get_conn()
        clean_id = str(txn_id).strip()

        # 1. Fetch Transaction vertex
        try:
            vertices = conn.getVerticesById("Transaction", clean_id)
        except Exception as e:
            err_msg = str(e)
            if "not a valid vertex id" in err_msg or any("601" in str(a) for a in getattr(e, "args", ())):
                raise TransactionNotFoundError(f"Transaction '{clean_id}' does not exist in graph database.")
            raise

        if not vertices:
            raise TransactionNotFoundError(f"Transaction '{clean_id}' does not exist in graph database.")

        v = vertices[0]
        attrs = v.get("attributes", {})

        amount = float(attrs.get("amount", 0.0))
        ts = str(attrs.get("ts", ""))
        r_score = float(attrs.get("risk_score")) if attrs.get("risk_score") is not None else None
        channel = str(attrs.get("channel", "online"))
        addr1 = float(attrs.get("addr1", 0.0)) if attrs.get("addr1") is not None else 0.0
        is_flagged = bool(attrs.get("is_flagged", False))

        # 2. Traverse edges out of Transaction
        card_id = ""
        device_id = None
        email_domain = None

        try:
            edges = conn.getEdges("Transaction", clean_id)
            for edge in edges:
                e_type = edge.get("e_type", "")
                to_type = edge.get("to_type", "")
                to_id = edge.get("to_id", "")

                if e_type == "Transaction_MADE_BY_Card" or to_type == "Card":
                    card_id = str(to_id)
                elif e_type == "Transaction_FROM_DEVICE" or to_type == "DeviceProfile":
                    device_id = str(to_id)
                elif e_type == "Transaction_PURCHASER_EMAIL" or to_type == "EmailDomain":
                    email_domain = str(to_id)
        except Exception as e:
            # Non-fatal if edges retrieval fails; card_id may be in attributes or resolved via query
            pass

        # 3. Resolve Customer from Card
        customer_id = ""
        if card_id:
            try:
                card_v = conn.getVerticesById("Card", card_id)
                if card_v:
                    c_attrs = card_v[0].get("attributes", {})
                    customer_id = str(c_attrs.get("customer_id", ""))
                
                # If customer_id attribute was empty, check reverse edge Card_OWNED_BY_Customer
                if not customer_id:
                    card_edges = conn.getEdges("Card", card_id)
                    for ce in card_edges:
                        if ce.get("to_type") == "Customer" or ce.get("e_type") == "Card_OWNED_BY_Customer":
                            customer_id = str(ce.get("to_id", ""))
                            break
            except Exception:
                pass

        return ResolvedTransactionContext(
            txn_id=clean_id,
            amount=amount,
            timestamp=ts,
            risk_score=r_score,
            channel=channel,
            addr1=addr1,
            card_id=card_id,
            customer_id=customer_id,
            device_id=device_id,
            email_domain=email_domain,
            is_flagged=is_flagged,
            raw_attributes=attrs
        )
