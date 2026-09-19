from typing import Dict, Any, Optional

# Independent external response fixture.
# Completely decoupled from Tark's internal belief or model posterior.
# In a real production banking environment, this represents an external webhook from the SMS/IVR gateway.
EXTERNAL_COMMUNICATION_FIXTURES: Dict[str, Dict[str, Any]] = {}

def simulate_customer_reply(case_id: str, prompt: str, trigger_type: str, fixture_response: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves an independent external cardholder communication response.
    Completely decoupled from the internal fraud belief or model posterior.
    """
    # 1. If trigger itself was an inbound customer dispute/report, cardholder already established denial
    if trigger_type == "customer_report":
        return {
            "status": "COMPLETED",
            "reply": "I did not authorize or make this transaction. My card is in my possession.",
            "customer_denied": True,
            "provenance": "inbound_customer_ticket"
        }
    
    # 2. Check independent explicit test/case fixture
    if fixture_response is not None:
        denied = any(kw in fixture_response.lower() for kw in ["not", "never", "unauthorized", "dispute", "fraud"])
        return {
            "status": "COMPLETED",
            "reply": fixture_response,
            "customer_denied": denied,
            "provenance": "external_gateway_fixture"
        }
    
    # 3. Check registered external fixtures table
    if case_id in EXTERNAL_COMMUNICATION_FIXTURES:
        record = EXTERNAL_COMMUNICATION_FIXTURES[case_id]
        return {
            "status": "COMPLETED",
            "reply": record["reply"],
            "customer_denied": record["customer_denied"],
            "provenance": f"external_gateway_ticket_{record.get('ticket_id', 'unknown')}"
        }
    
    # 4. Standard operational reality: When no external out-of-band response is available
    return {
        "status": "UNAVAILABLE",
        "reply": "Customer verification challenge timed out; no out-of-band response received via SMS/Email gateway.",
        "customer_denied": None,
        "provenance": "external_gateway_timeout"
    }

def simulate_step_up_auth(case_id: str, fixture_result: Optional[bool] = None) -> Dict[str, Any]:
    """Evaluates cryptographic MFA / Step-up challenge response.
    Independent of internal posterior belief.
    """
    if fixture_result is not None:
        return {
            "status": "COMPLETED",
            "auth_passed": fixture_result,
            "provenance": "fido2_mfa_gateway"
        }
    
    # Without customer active interaction, challenge expires
    return {
        "status": "TIMEOUT",
        "auth_passed": False,
        "provenance": "mfa_challenge_expired"
    }
