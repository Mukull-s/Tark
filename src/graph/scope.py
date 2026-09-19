import logging
from enum import Enum
from typing import Dict, Any, Optional, Set, List
from pydantic import BaseModel, Field

logger = logging.getLogger("tark.graph.scope")

class GraphScopeStatus(str, Enum):
    DATA_AVAILABLE = "DATA_AVAILABLE"
    DATA_OUT_OF_SCOPE = "DATA_OUT_OF_SCOPE"
    NO_MATCH = "NO_MATCH"
    GRAPH_QUERY_FAILURE = "GRAPH_QUERY_FAILURE"

class ScopeResponse(BaseModel):
    status: GraphScopeStatus
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    query_name: Optional[str] = None
    data: Any = None
    message: str = ""
    error_details: Optional[str] = None

class GraphScope:
    """Manages explicit data boundary contracts for graph exploration.
    
    Distinguishes:
    - DATA_AVAILABLE: Entity/neighborhood exists and query returned evidence.
    - NO_MATCH: Entity exists in scope, but specific pattern/relationship was not found.
    - DATA_OUT_OF_SCOPE: Entity was not part of the ingested portfolio/cohort slice.
    - GRAPH_QUERY_FAILURE: Underlying database/network failed during query execution.
    """

    def __init__(self, in_scope_customers: Optional[Set[str]] = None, in_scope_cards: Optional[Set[str]] = None):
        self.in_scope_customers: Set[str] = in_scope_customers or set()
        self.in_scope_cards: Set[str] = in_scope_cards or set()

    def register_portfolio(self, customer_ids: List[str], card_ids: List[str]):
        """Registers the known portfolio boundary from the ingestion layer."""
        self.in_scope_customers.update(customer_ids)
        self.in_scope_cards.update(card_ids)

    def is_in_scope(self, entity_type: str, entity_id: str) -> bool:
        """Determines if an entity falls within the currently ingested graph scope."""
        if not entity_id:
            return False
        
        # If no scope filter has been explicitly configured, default to active graph check
        if not self.in_scope_customers and not self.in_scope_cards:
            return True

        if entity_type.lower() in ["customer", "cust", "customer_id"]:
            return entity_id in self.in_scope_customers
        elif entity_type.lower() in ["card", "card_id"]:
            return entity_id in self.in_scope_cards
        
        # Transactions and devices are evaluated via their parent card/customer scope
        return True

    def query_with_scope(
        self,
        conn: Any,
        query_name: str,
        params: Dict[str, Any],
        target_entity_type: str,
        target_entity_id: str
    ) -> ScopeResponse:
        """Executes a GSQL query with strict scope boundary checking.
        
        Ensures DATA_OUT_OF_SCOPE is never silently confused with NO_MATCH.
        """
        # 1. Scope Boundary Check
        if not self.is_in_scope(target_entity_type, target_entity_id):
            return ScopeResponse(
                status=GraphScopeStatus.DATA_OUT_OF_SCOPE,
                entity_type=target_entity_type,
                entity_id=target_entity_id,
                query_name=query_name,
                data=None,
                message=(
                    f"Entity {target_entity_type}='{target_entity_id}' is outside the currently "
                    f"ingested graph slice. Historical data is unobserved, NOT confirmed negative."
                )
            )

        # 2. Query Execution with Explicit Failure Capture
        try:
            res = conn.runInstalledQuery(query_name, params)
        except Exception as e:
            logger.error(f"Graph query execution failed for {query_name}: {e}")
            return ScopeResponse(
                status=GraphScopeStatus.GRAPH_QUERY_FAILURE,
                entity_type=target_entity_type,
                entity_id=target_entity_id,
                query_name=query_name,
                data=None,
                message=f"Query {query_name} execution failed against TigerGraph.",
                error_details=str(e)
            )

        # 3. Analyze Response for Match vs Empty
        if not res or len(res) == 0:
            return ScopeResponse(
                status=GraphScopeStatus.NO_MATCH,
                entity_type=target_entity_type,
                entity_id=target_entity_id,
                query_name=query_name,
                data=[],
                message=f"Query {query_name} executed successfully; no matching entities found."
            )

        # Handle queries that return empty result dictionaries (e.g. Matched: [])
        first_res = res[0] if isinstance(res, list) else res
        if isinstance(first_res, dict):
            # Check for empty matched lists or zero aggregations
            if "Matched" in first_res and len(first_res["Matched"]) == 0:
                return ScopeResponse(
                    status=GraphScopeStatus.NO_MATCH,
                    entity_type=target_entity_type,
                    entity_id=target_entity_id,
                    query_name=query_name,
                    data=res,
                    message=f"Query {query_name} returned 0 matching historical cases."
                )
            if first_res.get("total_txns", 1) == 0 and first_res.get("txn_count", 1) == 0 and first_res.get("shared_card_count", 1) == 0:
                return ScopeResponse(
                    status=GraphScopeStatus.NO_MATCH,
                    entity_type=target_entity_type,
                    entity_id=target_entity_id,
                    query_name=query_name,
                    data=res,
                    message=f"Query {query_name} returned 0 instances for entity."
                )

        return ScopeResponse(
            status=GraphScopeStatus.DATA_AVAILABLE,
            entity_type=target_entity_type,
            entity_id=target_entity_id,
            query_name=query_name,
            data=res,
            message="Evidence successfully retrieved from graph."
        )
