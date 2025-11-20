#!/usr/bin/env python3
"""
Authorization Agent for UTurn Credit Card Customer Service
Handles: Authentication, Security, Fraud Detection, Card Management
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import re

# In production, this would connect to actual customer database
# For demo, we load from our synthetic data
CUSTOMER_DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data/customer_data/customers.json')

def load_customer_data() -> Dict:
    """Load customer data from JSON file."""
    try:
        with open(CUSTOMER_DATA_PATH, 'r') as f:
            customers = json.load(f)
        return {c['customer_id']: c for c in customers}
    except Exception as e:
        print(f"Error loading customer data: {e}")
        return {}

# Load customer data at module level
CUSTOMERS = load_customer_data()


def verify_customer_identity(customer_id: str, verification_method: str, verification_value: str) -> Dict[str, Any]:
    """
    Verify customer identity using various methods.

    Args:
        customer_id: Customer ID to verify
        verification_method: Method of verification (PIN, security_question, phone, date_of_birth)
        verification_value: Value provided for verification

    Returns:
        Dict with verification result and details
    """
    if customer_id not in CUSTOMERS:
        return {
            "verified": False,
            "message": "Customer ID not found in system",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    verified = False
    message = ""

    if verification_method.lower() == "pin":
        stored_pin = customer['security']['pin']
        verified = verification_value == stored_pin
        message = "PIN verification successful" if verified else "PIN verification failed"

    elif verification_method.lower() == "security_question":
        # In real system, would ask the question first, then verify answer
        stored_answer = customer['security']['security_answer']
        verified = verification_value.lower() == stored_answer.lower()
        message = "Security question verification successful" if verified else "Security question verification failed"

    elif verification_method.lower() == "phone":
        stored_phone = customer['personal_info']['phone'].replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        input_phone = verification_value.replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        verified = stored_phone == input_phone
        message = "Phone verification successful" if verified else "Phone verification failed"

    elif verification_method.lower() == "date_of_birth" or verification_method.lower() == "dob":
        stored_dob = customer['personal_info']['date_of_birth']
        verified = verification_value == stored_dob
        message = "Date of birth verification successful" if verified else "Date of birth verification failed"

    else:
        return {
            "verified": False,
            "message": f"Unknown verification method: {verification_method}",
            "customer_id": customer_id
        }

    if verified:
        # Update last verified timestamp
        customer['security']['last_verified'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "verified": verified,
        "message": message,
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'] if verified else None,
        "verification_method": verification_method,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def check_fraud_status(customer_id: str) -> Dict[str, Any]:
    """
    Check fraud status and alerts for a customer account.

    Args:
        customer_id: Customer ID to check

    Returns:
        Dict with fraud status and any active alerts
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    security = customer['security']

    fraud_alerts = security.get('fraud_alerts', [])
    card_locked = security.get('card_locked', False)

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "card_locked": card_locked,
        "fraud_alert_active": len(fraud_alerts) > 0,
        "fraud_alerts": fraud_alerts,
        "card_status": customer['account_info']['card_status'],
        "recommendation": "Contact fraud department immediately" if card_locked else "No action needed",
        "fraud_hotline": "1-800-FRAUD-00"
    }


def lock_unlock_card(customer_id: str, action: str, reason: str = "") -> Dict[str, Any]:
    """
    Lock or unlock a customer's card.

    Args:
        customer_id: Customer ID
        action: 'lock' or 'unlock'
        reason: Reason for the action

    Returns:
        Dict with result of the action
    """
    if customer_id not in CUSTOMERS:
        return {
            "success": False,
            "message": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    action_lower = action.lower()

    if action_lower not in ['lock', 'unlock']:
        return {
            "success": False,
            "message": f"Invalid action: {action}. Must be 'lock' or 'unlock'",
            "customer_id": customer_id
        }

    # Update card status
    if action_lower == 'lock':
        customer['security']['card_locked'] = True
        customer['account_info']['card_status'] = 'Locked'
        message = f"Card successfully locked for customer {customer['personal_info']['full_name']}"

    else:  # unlock
        customer['security']['card_locked'] = False
        customer['account_info']['card_status'] = 'Active'
        message = f"Card successfully unlocked for customer {customer['personal_info']['full_name']}"

    # Add to fraud alerts if locked for fraud
    if action_lower == 'lock' and 'fraud' in reason.lower():
        alert = {
            "alert_id": f"FRAUD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": reason,
            "status": "Active"
        }
        customer['security']['fraud_alerts'].append(alert)

    return {
        "success": True,
        "message": message,
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "action": action_lower,
        "new_card_status": customer['account_info']['card_status'],
        "reason": reason,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def update_security_settings(customer_id: str, setting_type: str, new_value: str) -> Dict[str, Any]:
    """
    Update security settings for a customer.

    Args:
        customer_id: Customer ID
        setting_type: Type of setting to update (pin, security_question, security_answer)
        new_value: New value for the setting

    Returns:
        Dict with result of the update
    """
    if customer_id not in CUSTOMERS:
        return {
            "success": False,
            "message": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    setting_lower = setting_type.lower()

    if setting_lower == 'pin':
        # Validate PIN format (4 digits)
        if not re.match(r'^\d{4}$', new_value):
            return {
                "success": False,
                "message": "Invalid PIN format. PIN must be 4 digits.",
                "customer_id": customer_id
            }
        customer['security']['pin'] = new_value
        message = "PIN successfully updated"

    elif setting_lower == 'security_question':
        customer['security']['security_question'] = new_value
        message = "Security question successfully updated"

    elif setting_lower == 'security_answer':
        customer['security']['security_answer'] = new_value
        message = "Security answer successfully updated"

    else:
        return {
            "success": False,
            "message": f"Unknown setting type: {setting_type}",
            "customer_id": customer_id
        }

    return {
        "success": True,
        "message": message,
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "setting_updated": setting_type,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def report_suspicious_transaction(customer_id: str, transaction_id: str, description: str) -> Dict[str, Any]:
    """
    Report a suspicious transaction.

    Args:
        customer_id: Customer ID
        transaction_id: Transaction ID to report
        description: Description of why the transaction is suspicious

    Returns:
        Dict with fraud report details
    """
    if customer_id not in CUSTOMERS:
        return {
            "success": False,
            "message": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]

    # Create fraud alert
    alert = {
        "alert_id": f"FRAUD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "description": f"Suspicious transaction reported: {transaction_id} - {description}",
        "status": "Under Investigation",
        "transaction_id": transaction_id
    }

    customer['security']['fraud_alerts'].append(alert)

    # Find the transaction in customer's history
    transaction_found = None
    for txn in customer.get('full_transaction_history', []):
        if txn['transaction_id'] == transaction_id:
            transaction_found = txn
            break

    return {
        "success": True,
        "message": "Suspicious transaction report filed successfully",
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "fraud_alert_id": alert['alert_id'],
        "transaction_id": transaction_id,
        "transaction_details": transaction_found,
        "next_steps": "A fraud specialist will review this transaction within 24 hours. You will receive an email with updates.",
        "fraud_hotline": "1-800-FRAUD-00",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_security_summary(customer_id: str) -> Dict[str, Any]:
    """
    Get a comprehensive security summary for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        Dict with security summary
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    security = customer['security']
    account_info = customer['account_info']

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "card_status": account_info['card_status'],
        "card_locked": security['card_locked'],
        "last_verified": security['last_verified'],
        "fraud_alerts": len(security['fraud_alerts']),
        "active_fraud_alerts": len([a for a in security['fraud_alerts'] if a['status'] != 'Resolved']),
        "security_question_set": bool(security.get('security_question')),
        "pin_set": bool(security.get('pin')),
        "recent_alerts": security['fraud_alerts'][-3:] if security['fraud_alerts'] else [],
        "recommendations": [
            "Enable transaction alerts" if not account_info.get('alerts_enabled', True) else None,
            "Review recent transactions" if security['fraud_alerts'] else None,
            "Update security question" if not security.get('security_question') else None
        ]
    }


# ============================================================================
# AgentCore Entry Point
# ============================================================================

def authorization_agent_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the Authorization Agent.
    Handles all authorization, security, and fraud-related requests.

    This function is called by AWS Bedrock AgentCore when the agent is invoked.
    """

    # Extract input from the event
    user_input = event.get('input', '')
    session_id = event.get('sessionId', 'unknown')

    # Parse the request to determine which tool to call
    # In production, this would be handled by Bedrock's tool use capability
    # For now, we provide a simple routing based on keywords

    response_text = f"""Authorization Agent activated. I can help you with:
- Verify customer identity
- Check fraud status
- Lock or unlock cards
- Update security settings
- Report suspicious transactions
- Get security summary

Please provide customer ID and specify what action you need."""

    return {
        "response": response_text,
        "sessionId": session_id,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test the agent functions
    print("Testing Authorization Agent functions...")

    # Test with first customer
    test_customer_id = "CUST-010000"

    print("\n1. Testing verify_customer_identity...")
    result = verify_customer_identity(test_customer_id, "PIN", "1488")
    print(json.dumps(result, indent=2))

    print("\n2. Testing check_fraud_status...")
    result = check_fraud_status(test_customer_id)
    print(json.dumps(result, indent=2))

    print("\n3. Testing get_security_summary...")
    result = get_security_summary(test_customer_id)
    print(json.dumps(result, indent=2))

    print("\n✓ Authorization Agent functions tested successfully!")
