import uuid
import datetime
from typing import Dict, Any, Optional, List

from src.evidence.types import EvidenceItem, EvidenceType, EvidenceDirection
from src.graph.scope import GraphScopeStatus

class EvidenceNormalizer:
    """Normalizes raw tool and GSQL outputs into canonical, uncertainty-aware EvidenceItems.
    
    Guarantees:
    - DATA_OUT_OF_SCOPE and GRAPH_QUERY_FAILURE produce explicit uninformative items (LR=1.0, log-LR=0.0).
    - NO_MATCH is treated neutrally (LR=1.0, log-LR=0.0) without fabricating negative proof.
    - Full provenance and entity attribution are preserved.
    """

    @classmethod
    def normalize(
        cls,
        action_id: str,
        tool_name: str,
        scope_status: GraphScopeStatus,
        raw_data: Any,
        target_entities: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ) -> EvidenceItem:
        ctx = context or {}
        evidence_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        card_id = target_entities.get("card_id")
        customer_id = target_entities.get("customer_id")
        txn_id = target_entities.get("flagged_txn_id") or target_entities.get("txn_id")

        # 1. Handle DATA_OUT_OF_SCOPE
        if scope_status == GraphScopeStatus.DATA_OUT_OF_SCOPE:
            return EvidenceItem(
                evidence_id=evidence_id,
                evidence_type=cls._fallback_type_for_action(action_id),
                value="DATA_OUT_OF_SCOPE",
                source=f"tigergraph_scope:{tool_name}",
                finding=f"Query {tool_name} reported DATA_OUT_OF_SCOPE: Target entity is outside the ingested graph horizon.",
                provenance=f"TigerGraph scope boundary guard ({tool_name})",
                source_entity=card_id or customer_id,
                target_entity=txn_id,
                graph_query=tool_name,
                timestamp=now_ts,
                lr=1.0,
                log_lr=0.0,
                direction=EvidenceDirection.NEUTRAL,
                is_exculpatory=False,
                details={"scope_status": "DATA_OUT_OF_SCOPE", "raw": raw_data}
            )

        # 2. Handle GRAPH_QUERY_FAILURE
        if scope_status == GraphScopeStatus.GRAPH_QUERY_FAILURE:
            return EvidenceItem(
                evidence_id=evidence_id,
                evidence_type=cls._fallback_type_for_action(action_id),
                value="GRAPH_QUERY_FAILURE",
                source=f"tigergraph_error:{tool_name}",
                finding=f"Query {tool_name} reported GRAPH_QUERY_FAILURE: Database execution or connection error.",
                provenance=f"TigerGraph execution error ({tool_name})",
                source_entity=card_id or customer_id,
                target_entity=txn_id,
                graph_query=tool_name,
                timestamp=now_ts,
                lr=1.0,
                log_lr=0.0,
                direction=EvidenceDirection.NEUTRAL,
                is_exculpatory=False,
                details={"scope_status": "GRAPH_QUERY_FAILURE", "raw": raw_data}
            )

        # 3. Handle NO_MATCH
        if scope_status == GraphScopeStatus.NO_MATCH:
            fallback_type = cls._fallback_type_for_action(action_id)
            is_gateway = tool_name.startswith("simulate_") or "gateway" in tool_name
            src = f"gateway:{tool_name}" if is_gateway else f"tigergraph_query:{tool_name}"
            prov = f"External communication gateway ({tool_name})" if is_gateway else f"TigerGraph GSQL execution ({tool_name})"
            finding_text = (
                f"Customer communication tool {tool_name} completed without cardholder response (UNAVAILABLE/TIMEOUT)."
                if fallback_type == EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
                else f"Queried pattern {tool_name} was not observed within available query scope."
            )
            return EvidenceItem(
                evidence_id=evidence_id,
                evidence_type=fallback_type,
                value="NO_MATCH",
                source=src,
                finding=finding_text,
                provenance=prov,
                source_entity=card_id or customer_id,
                target_entity=txn_id,
                graph_query=None if is_gateway else tool_name,
                timestamp=now_ts,
                lr=1.0,
                log_lr=0.0,
                direction=EvidenceDirection.NEUTRAL,
                is_exculpatory=False,
                details={"scope_status": "NO_MATCH", "raw": raw_data}
            )

        # 4. Handle DATA_AVAILABLE with Tool-Specific Interpretation
        first_row = raw_data[0] if isinstance(raw_data, list) and len(raw_data) > 0 else (raw_data if isinstance(raw_data, dict) else {})
        
        # Tool: device_analysis
        if tool_name == "device_analysis":
            shared_count = first_row.get("shared_card_count", 0)
            is_proxy = first_row.get("is_proxy", False)
            device_id = first_row.get("device_id", "")
            connected_cards = first_row.get("connected_cards", [])

            if shared_count >= 3:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.SHARED_DEVICE_RING,
                    value={"device_id": device_id, "shared_card_count": shared_count, "is_proxy": is_proxy},
                    source="tigergraph_query:device_analysis",
                    finding=f"Device {device_id} is shared across {shared_count} distinct cards in graph ring (proxy={is_proxy}).",
                    provenance="TigerGraph GSQL device_analysis",
                    source_entity=device_id,
                    target_entity=txn_id,
                    graph_query="device_analysis",
                    supporting_entities=connected_cards,
                    timestamp=now_ts,
                    lr=14.2,
                    log_lr=2.653,
                    direction=EvidenceDirection.SUPPORTS,
                    is_exculpatory=False,
                    details={"shared_count": shared_count, "device_id": device_id, "is_proxy": is_proxy}
                )
            elif is_proxy:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.PROXY_DETECTED,
                    value={"device_id": device_id, "is_proxy": True},
                    source="tigergraph_query:device_analysis",
                    finding=f"Device {device_id} proxy connection detected in graph.",
                    provenance="TigerGraph GSQL device_analysis",
                    source_entity=device_id,
                    target_entity=txn_id,
                    graph_query="device_analysis",
                    timestamp=now_ts,
                    lr=3.8,
                    log_lr=1.335,
                    direction=EvidenceDirection.SUPPORTS,
                    is_exculpatory=False,
                    details={"device_id": device_id, "is_proxy": True}
                )
            else:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.SHARED_DEVICE_RING,
                    value="NO_MATCH",
                    source="tigergraph_query:device_analysis",
                    finding=f"Device {device_id} shows clean single-card profile; no multi-card ring observed.",
                    provenance="TigerGraph GSQL device_analysis",
                    source_entity=device_id,
                    target_entity=txn_id,
                    graph_query="device_analysis",
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"scope_status": "NO_MATCH", "device_id": device_id}
                )

        # Tool: card_sequence
        elif tool_name == "card_sequence":
            is_testing = first_row.get("is_card_testing", False)
            micro_count = first_row.get("micro_count", 0)
            micro_txn_ids = first_row.get("micro_txn_ids", [])
            total_spend = first_row.get("total_spend", 0.0)

            if is_testing and micro_count >= 3:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
                    value={"micro_count": micro_count, "total_spend": total_spend},
                    source="tigergraph_query:card_sequence",
                    finding=f"Card testing sequence observed: {micro_count} micro-authorizations totaling ${total_spend:.2f}.",
                    provenance="TigerGraph GSQL card_sequence",
                    source_entity=card_id,
                    target_entity=txn_id,
                    graph_query="card_sequence",
                    supporting_transaction_ids=micro_txn_ids,
                    timestamp=now_ts,
                    lr=34.3,
                    log_lr=3.535,
                    direction=EvidenceDirection.SUPPORTS,
                    is_exculpatory=False,
                    details={"micro_count": micro_count, "total_spend": total_spend}
                )
            else:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CARD_TESTING_SEQUENCE,
                    value="NO_MATCH",
                    source="tigergraph_query:card_sequence",
                    finding="No micro-authorization card testing sequence observed within 24h window.",
                    provenance="TigerGraph GSQL card_sequence",
                    source_entity=card_id,
                    target_entity=txn_id,
                    graph_query="card_sequence",
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"scope_status": "NO_MATCH"}
                )

        # Tool: txn_velocity
        elif tool_name == "txn_velocity":
            txn_count = first_row.get("txn_count", 0)
            total_spend = first_row.get("total_spend", 0.0)
            txn_ids = first_row.get("txn_ids", [])

            if txn_count >= 10:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.HIGH_VELOCITY,
                    value={"txn_count": txn_count, "total_spend": total_spend},
                    source="tigergraph_query:txn_velocity",
                    finding=f"High transaction velocity: {txn_count} transactions totaling ${total_spend:.2f} within 24h.",
                    provenance="TigerGraph GSQL txn_velocity",
                    source_entity=card_id,
                    target_entity=txn_id,
                    graph_query="txn_velocity",
                    supporting_transaction_ids=txn_ids,
                    timestamp=now_ts,
                    lr=2.5,
                    log_lr=0.916,
                    direction=EvidenceDirection.SUPPORTS,
                    is_exculpatory=False,
                    details={"txn_count": txn_count, "total_spend": total_spend}
                )
            else:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.HIGH_VELOCITY,
                    value="NO_MATCH",
                    source="tigergraph_query:txn_velocity",
                    finding=f"Transaction velocity within normal bounds ({txn_count} transactions within 24h window).",
                    provenance="TigerGraph GSQL txn_velocity",
                    source_entity=card_id,
                    target_entity=txn_id,
                    graph_query="txn_velocity",
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"scope_status": "NO_MATCH", "txn_count": txn_count}
                )

        # Tool: region_analysis
        elif tool_name == "region_analysis":
            is_out_of_region = first_row.get("is_out_of_region", False)
            known_regions = first_row.get("known_regions", {})
            total_history_txns = first_row.get("total_history_txns", 0)

            if is_out_of_region:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.OUT_OF_REGION,
                    value={"is_out_of_region": True, "known_regions": known_regions},
                    source="tigergraph_query:region_analysis",
                    finding=f"Transaction billing region is outside customer's historical modal regions (history txns: {total_history_txns}).",
                    provenance="TigerGraph GSQL region_analysis",
                    source_entity=customer_id,
                    target_entity=txn_id,
                    graph_query="region_analysis",
                    timestamp=now_ts,
                    lr=0.26,
                    log_lr=-1.357,
                    direction=EvidenceDirection.CONTRADICTS,
                    is_exculpatory=False,
                    details={"is_out_of_region": True, "known_regions": known_regions}
                )
            else:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.OUT_OF_REGION,
                    value="NO_MATCH",
                    source="tigergraph_query:region_analysis",
                    finding="Transaction billing region matches customer historical profile.",
                    provenance="TigerGraph GSQL region_analysis",
                    source_entity=customer_id,
                    target_entity=txn_id,
                    graph_query="region_analysis",
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"scope_status": "NO_MATCH"}
                )

        # Tool: customer_profile
        elif tool_name == "customer_profile":
            total_txns = first_row.get("total_txns", 0)
            avg_amount = first_row.get("avg_amount", 0.0)
            primary_channel = first_row.get("primary_channel", "unknown")
            return EvidenceItem(
                evidence_id=evidence_id,
                evidence_type=EvidenceType.BEHAVIORAL_BASELINE,
                value={"total_txns": total_txns, "avg_amount": avg_amount, "primary_channel": primary_channel},
                source="tigergraph_query:customer_profile",
                finding=f"Customer baseline: {total_txns} historical txns, avg ${avg_amount:.2f}, primary channel: {primary_channel}.",
                provenance="TigerGraph GSQL customer_profile",
                source_entity=customer_id,
                target_entity=card_id,
                graph_query="customer_profile",
                timestamp=now_ts,
                lr=1.0,
                log_lr=0.0,
                direction=EvidenceDirection.NEUTRAL,
                is_exculpatory=False,
                details={"total_txns": total_txns, "avg_amount": avg_amount, "primary_channel": primary_channel}
            )

        # Tool: similar_cases
        elif tool_name == "similar_cases":
            matched = first_row.get("Matched", [])
            if matched and len(matched) > 0:
                supporting_cids = [m.get("v_id", "") for m in matched if isinstance(m, dict)]
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.SIMILAR_CASE_PRECEDENT,
                    value={"matched_case_count": len(matched)},
                    source="tigergraph_query:similar_cases",
                    finding=f"Retrieved {len(matched)} precedent closed cases matching investigative pattern.",
                    provenance="TigerGraph GSQL similar_cases",
                    source_entity=card_id,
                    target_entity=txn_id,
                    graph_query="similar_cases",
                    supporting_entities=supporting_cids,
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"matched_case_count": len(matched), "cases": matched}
                )
            else:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.SIMILAR_CASE_PRECEDENT,
                    value="NO_MATCH",
                    source="tigergraph_query:similar_cases",
                    finding="No historical closed case precedents found matching pattern.",
                    provenance="TigerGraph GSQL similar_cases",
                    source_entity=card_id,
                    target_entity=txn_id,
                    graph_query="similar_cases",
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"scope_status": "NO_MATCH"}
                )

        # Tool: simulate_customer_reply (Customer Interaction)
        elif tool_name == "simulate_customer_reply":
            customer_denied = raw_data.get("customer_denied")
            reply = raw_data.get("reply", "")
            prov = raw_data.get("provenance", "external_customer_gateway")

            if customer_denied is True:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CUSTOMER_DENIAL,
                    value=reply,
                    source="gateway:simulate_customer_reply",
                    finding=f"Cardholder explicitly disputed and denied transaction authorization: '{reply}'",
                    provenance=prov,
                    source_entity=customer_id,
                    target_entity=txn_id,
                    timestamp=now_ts,
                    lr=18.5,
                    log_lr=2.918,
                    direction=EvidenceDirection.SUPPORTS,
                    is_exculpatory=False,
                    details={"reply": reply, "customer_denied": True}
                )
            elif customer_denied is False:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
                    value=reply,
                    source="gateway:simulate_customer_reply",
                    finding=f"Cardholder confirmed transaction was legitimate: '{reply}'",
                    provenance=prov,
                    source_entity=customer_id,
                    target_entity=txn_id,
                    timestamp=now_ts,
                    lr=0.05,
                    log_lr=-2.996,
                    direction=EvidenceDirection.CONTRADICTS,
                    is_exculpatory=True,
                    details={"reply": reply, "customer_denied": False}
                )
            else:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE,
                    value="NO_MATCH",
                    source="gateway:simulate_customer_reply",
                    finding="Customer verification challenge timed out; no out-of-band response received.",
                    provenance=prov,
                    source_entity=customer_id,
                    target_entity=txn_id,
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"scope_status": "NO_MATCH", "reply": reply, "status": "UNAVAILABLE"}
                )

        # Tool: simulate_step_up_auth (MFA Authentication Challenge)
        elif tool_name == "simulate_step_up_auth":
            auth_passed = raw_data.get("auth_passed")
            prov = raw_data.get("provenance", "fido2_mfa_gateway")

            if auth_passed is False:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CUSTOMER_DENIAL,
                    value={"auth_passed": False},
                    source="gateway:simulate_step_up_auth",
                    finding="Cardholder step-up authentication challenge failed.",
                    provenance=prov,
                    source_entity=customer_id,
                    target_entity=txn_id,
                    timestamp=now_ts,
                    lr=15.0,
                    log_lr=2.708,
                    direction=EvidenceDirection.SUPPORTS,
                    is_exculpatory=False,
                    details={"auth_passed": False}
                )
            elif auth_passed is True:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CUSTOMER_CONFIRMATION,
                    value={"auth_passed": True},
                    source="gateway:simulate_step_up_auth",
                    finding="Cardholder successfully completed cryptographic step-up MFA challenge.",
                    provenance=prov,
                    source_entity=customer_id,
                    target_entity=txn_id,
                    timestamp=now_ts,
                    lr=0.10,
                    log_lr=-2.302,
                    direction=EvidenceDirection.CONTRADICTS,
                    is_exculpatory=True,
                    details={"auth_passed": True}
                )
            else:
                return EvidenceItem(
                    evidence_id=evidence_id,
                    evidence_type=EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE,
                    value="NO_MATCH",
                    source="gateway:simulate_step_up_auth",
                    finding="Step-up authentication challenge expired without interaction.",
                    provenance=prov,
                    source_entity=customer_id,
                    target_entity=txn_id,
                    timestamp=now_ts,
                    lr=1.0,
                    log_lr=0.0,
                    direction=EvidenceDirection.NEUTRAL,
                    is_exculpatory=False,
                    details={"scope_status": "NO_MATCH", "status": "TIMEOUT"}
                )

        # Generic Fallback
        return EvidenceItem(
            evidence_id=evidence_id,
            evidence_type=cls._fallback_type_for_action(action_id),
            value=raw_data,
            source=f"tool:{tool_name}",
            finding=f"Tool {tool_name} returned unclassified observational data.",
            provenance=f"Execution of {tool_name}",
            timestamp=now_ts,
            lr=1.0,
            log_lr=0.0,
            direction=EvidenceDirection.NEUTRAL,
            is_exculpatory=False,
            details={"raw": raw_data}
        )

    @staticmethod
    def _fallback_type_for_action(action_id: str) -> EvidenceType:
        act = action_id.upper()
        if "DEVICE" in act:
            return EvidenceType.SHARED_DEVICE_RING
        elif "SEQUENCE" in act or "TESTING" in act:
            return EvidenceType.CARD_TESTING_SEQUENCE
        elif "VELOCITY" in act:
            return EvidenceType.HIGH_VELOCITY
        elif "REGION" in act:
            return EvidenceType.OUT_OF_REGION
        elif "CUSTOMER" in act or "DISPUTE" in act or "STEP_UP" in act:
            return EvidenceType.CUSTOMER_COMMUNICATION_UNAVAILABLE
        elif "SIMILAR" in act or "CASE" in act:
            return EvidenceType.SIMILAR_CASE_PRECEDENT
        return EvidenceType.BEHAVIORAL_BASELINE
