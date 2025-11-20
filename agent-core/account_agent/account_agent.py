#!/usr/bin/env python3
"""
Account Agent for UTurn Credit Card Customer Service
Handles: Account Information, Balances, Transactions, Payments, Statements
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

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


def get_account_balance(customer_id: str) -> Dict[str, Any]:
    """
    Get current account balance and credit information.

    Args:
        customer_id: Customer ID

    Returns:
        Dict with balance and credit information
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    account_info = customer['account_info']
    payment_info = customer['payment_info']

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "card_type": account_info['card_type'],
        "card_number": account_info['card_number_masked'],
        "credit_limit": account_info['credit_limit'],
        "current_balance": account_info['current_balance'],
        "available_credit": account_info['available_credit'],
        "minimum_payment_due": payment_info['minimum_payment_due'],
        "payment_due_date": payment_info['payment_due_date'],
        "apr": account_info['apr'],
        "rewards_balance": account_info['rewards_balance'],
        "rewards_program": account_info['rewards_program'],
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_transaction_history(customer_id: str, num_transactions: int = 10, days: Optional[int] = None) -> Dict[str, Any]:
    """
    Get transaction history for a customer.

    Args:
        customer_id: Customer ID
        num_transactions: Number of recent transactions to return (default 10)
        days: Optional - filter transactions from last N days

    Returns:
        Dict with transaction history
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    all_transactions = customer.get('full_transaction_history', customer.get('transactions', []))

    # Filter by days if specified
    if days:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        filtered_transactions = [
            txn for txn in all_transactions
            if txn['date'] >= cutoff_date
        ]
        transactions = filtered_transactions[:num_transactions]
    else:
        transactions = all_transactions[:num_transactions]

    # Calculate summary statistics
    total_spent = sum(txn['amount'] for txn in transactions if txn['amount'] > 0)
    total_refunds = sum(abs(txn['amount']) for txn in transactions if txn['amount'] < 0)
    pending_count = sum(1 for txn in transactions if txn['status'] == 'Pending')

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "transactions": transactions,
        "summary": {
            "total_transactions": len(transactions),
            "total_spent": round(total_spent, 2),
            "total_refunds": round(total_refunds, 2),
            "pending_transactions": pending_count,
            "date_range": {
                "from": transactions[-1]['date'] if transactions else None,
                "to": transactions[0]['date'] if transactions else None
            }
        },
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def search_transactions(customer_id: str, search_term: str) -> Dict[str, Any]:
    """
    Search transactions by merchant name or amount.

    Args:
        customer_id: Customer ID
        search_term: Search term (merchant name or amount)

    Returns:
        Dict with matching transactions
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    all_transactions = customer.get('full_transaction_history', customer.get('transactions', []))

    search_lower = search_term.lower()

    # Search in merchant names or match amount
    matching_transactions = []
    for txn in all_transactions:
        if (search_lower in txn['merchant'].lower() or
            search_term in str(txn['amount'])):
            matching_transactions.append(txn)

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "search_term": search_term,
        "matches_found": len(matching_transactions),
        "transactions": matching_transactions[:20],  # Limit to 20 results
        "searched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def make_payment(customer_id: str, payment_amount: float, payment_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Process a payment for the customer's account.

    Args:
        customer_id: Customer ID
        payment_amount: Amount to pay
        payment_date: Optional payment date (defaults to today)

    Returns:
        Dict with payment confirmation
    """
    if customer_id not in CUSTOMERS:
        return {
            "success": False,
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    account_info = customer['account_info']
    payment_info = customer['payment_info']

    # Validate payment amount
    if payment_amount <= 0:
        return {
            "success": False,
            "error": "Payment amount must be greater than zero",
            "customer_id": customer_id
        }

    if payment_amount > account_info['current_balance']:
        return {
            "success": False,
            "error": f"Payment amount ${payment_amount} exceeds current balance ${account_info['current_balance']}",
            "customer_id": customer_id
        }

    # Process payment
    payment_date = payment_date or datetime.now().strftime("%Y-%m-%d")

    # Update balances
    old_balance = account_info['current_balance']
    new_balance = old_balance - payment_amount
    account_info['current_balance'] = round(new_balance, 2)
    account_info['available_credit'] = round(account_info['credit_limit'] - new_balance, 2)

    # Update payment info
    payment_info['last_payment_amount'] = payment_amount
    payment_info['last_payment_date'] = payment_date
    payment_info['minimum_payment_due'] = round(max(25, new_balance * 0.02), 2)

    # Generate confirmation number
    confirmation_number = f"PMT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return {
        "success": True,
        "message": f"Payment of ${payment_amount} processed successfully",
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "confirmation_number": confirmation_number,
        "payment_details": {
            "payment_amount": payment_amount,
            "payment_date": payment_date,
            "old_balance": old_balance,
            "new_balance": new_balance,
            "available_credit": account_info['available_credit']
        },
        "next_payment_due": payment_info['payment_due_date'],
        "minimum_payment_due": payment_info['minimum_payment_due'],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_statement(customer_id: str, year_month: Optional[str] = None) -> Dict[str, Any]:
    """
    Get account statement for a specific month.

    Args:
        customer_id: Customer ID
        year_month: Optional month in YYYY-MM format (defaults to current month)

    Returns:
        Dict with statement information
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    account_info = customer['account_info']
    payment_info = customer['payment_info']

    # Use current month if not specified
    if not year_month:
        year_month = datetime.now().strftime("%Y-%m")

    # Filter transactions for the specified month
    all_transactions = customer.get('full_transaction_history', customer.get('transactions', []))
    month_transactions = [
        txn for txn in all_transactions
        if txn['date'].startswith(year_month)
    ]

    # Calculate statement summary
    total_purchases = sum(txn['amount'] for txn in month_transactions if txn['amount'] > 0)
    total_refunds = sum(abs(txn['amount']) for txn in month_transactions if txn['amount'] < 0)
    net_activity = total_purchases - total_refunds

    # Interest calculation (simplified)
    avg_daily_balance = account_info['current_balance']
    monthly_interest_rate = (account_info['apr'] / 100) / 12
    interest_charged = round(avg_daily_balance * monthly_interest_rate, 2)

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "statement_period": year_month,
        "card_type": account_info['card_type'],
        "card_number": account_info['card_number_masked'],
        "account_summary": {
            "previous_balance": round(account_info['current_balance'] - net_activity, 2),
            "purchases": round(total_purchases, 2),
            "refunds": round(total_refunds, 2),
            "interest_charged": interest_charged,
            "fees_charged": account_info.get('annual_fee', 0) / 12 if account_info.get('annual_fee') else 0,
            "new_balance": account_info['current_balance'],
            "minimum_payment_due": payment_info['minimum_payment_due'],
            "payment_due_date": payment_info['payment_due_date']
        },
        "transactions": month_transactions,
        "rewards_earned": round(total_purchases * 0.01, 2) if account_info['rewards_program'] else 0,
        "year_to_date_summary": {
            "total_spent": round(sum(txn['amount'] for txn in all_transactions if txn['amount'] > 0), 2),
            "total_rewards_earned": account_info['rewards_balance']
        },
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_rewards_balance(customer_id: str) -> Dict[str, Any]:
    """
    Get rewards balance and redemption options.

    Args:
        customer_id: Customer ID

    Returns:
        Dict with rewards information
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    account_info = customer['account_info']

    rewards_balance = account_info['rewards_balance']
    rewards_program = account_info['rewards_program']

    # Calculate redemption values
    if rewards_program == "Cash Back":
        cash_value = rewards_balance / 100
        redemption_options = [
            {"option": "Statement Credit", "value": f"${cash_value:.2f}"},
            {"option": "Direct Deposit", "value": f"${cash_value:.2f}"},
            {"option": "Gift Cards", "value": f"${cash_value * 1.1:.2f} (10% bonus)"}
        ]
    elif rewards_program == "Points":
        redemption_options = [
            {"option": "Travel", "value": f"{rewards_balance} points = ${rewards_balance/100:.2f}"},
            {"option": "Statement Credit", "value": f"{rewards_balance} points = ${rewards_balance/125:.2f}"},
            {"option": "Gift Cards", "value": f"{rewards_balance} points = ${rewards_balance/90:.2f}"},
            {"option": "Merchandise", "value": f"Check catalog for options"}
        ]
    else:  # Miles
        redemption_options = [
            {"option": "Airline Tickets", "value": f"{rewards_balance} miles"},
            {"option": "Hotel Stays", "value": f"{rewards_balance} miles"},
            {"option": "Car Rentals", "value": f"{rewards_balance} miles"},
            {"option": "Transfer to Partners", "value": "1:1 ratio"}
        ]

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "rewards_program": rewards_program,
        "rewards_balance": rewards_balance,
        "redemption_options": redemption_options,
        "expiration": "Never" if rewards_program != "Cash Back" else "End of calendar year",
        "next_reward_tier": "Spend $1,000 more to unlock 2x rewards for the quarter",
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def update_autopay(customer_id: str, enable: bool, payment_amount_type: str = "minimum") -> Dict[str, Any]:
    """
    Enable or disable autopay for a customer's account.

    Args:
        customer_id: Customer ID
        enable: True to enable, False to disable
        payment_amount_type: 'minimum', 'statement_balance', or 'fixed_amount'

    Returns:
        Dict with autopay update confirmation
    """
    if customer_id not in CUSTOMERS:
        return {
            "success": False,
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    payment_info = customer['payment_info']

    payment_info['autopay_enabled'] = enable

    if enable:
        message = f"Autopay enabled for {payment_amount_type} payment"
        payment_info['autopay_amount_type'] = payment_amount_type
    else:
        message = "Autopay disabled"
        payment_info['autopay_amount_type'] = None

    return {
        "success": True,
        "message": message,
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "autopay_enabled": enable,
        "payment_amount_type": payment_amount_type if enable else None,
        "next_payment_date": payment_info['payment_due_date'],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_account_summary(customer_id: str) -> Dict[str, Any]:
    """
    Get comprehensive account summary.

    Args:
        customer_id: Customer ID

    Returns:
        Dict with complete account overview
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    account_info = customer['account_info']
    payment_info = customer['payment_info']
    personal_info = customer['personal_info']

    recent_transactions = customer.get('transactions', [])[:5]

    return {
        "customer_id": customer_id,
        "customer_name": personal_info['full_name'],
        "contact": {
            "email": personal_info['email'],
            "phone": personal_info['phone']
        },
        "account": {
            "card_type": account_info['card_type'],
            "card_number": account_info['card_number_masked'],
            "card_status": account_info['card_status'],
            "account_open_date": account_info['account_open_date']
        },
        "balances": {
            "credit_limit": account_info['credit_limit'],
            "current_balance": account_info['current_balance'],
            "available_credit": account_info['available_credit'],
            "credit_utilization": round((account_info['current_balance'] / account_info['credit_limit']) * 100, 1)
        },
        "payment": {
            "minimum_payment_due": payment_info['minimum_payment_due'],
            "payment_due_date": payment_info['payment_due_date'],
            "last_payment_amount": payment_info['last_payment_amount'],
            "last_payment_date": payment_info['last_payment_date'],
            "autopay_enabled": payment_info['autopay_enabled']
        },
        "rewards": {
            "program": account_info['rewards_program'],
            "balance": account_info['rewards_balance']
        },
        "recent_transactions": recent_transactions,
        "apr": account_info['apr'],
        "annual_fee": account_info['annual_fee'],
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# ============================================================================
# AgentCore Entry Point
# ============================================================================

def account_agent_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the Account Agent.
    Handles all account, balance, transaction, and payment-related requests.

    This function is called by AWS Bedrock AgentCore when the agent is invoked.
    """

    # Extract input from the event
    user_input = event.get('input', '')
    session_id = event.get('sessionId', 'unknown')

    response_text = f"""Account Agent activated. I can help you with:
- Check account balance and credit information
- View transaction history
- Search for specific transactions
- Make a payment
- Get monthly statements
- Check rewards balance
- Set up or manage autopay
- Get comprehensive account summary

Please provide customer ID and specify what information you need."""

    return {
        "response": response_text,
        "sessionId": session_id,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test the agent functions
    print("Testing Account Agent functions...")

    # Test with first customer
    test_customer_id = "CUST-010000"

    print("\n1. Testing get_account_balance...")
    result = get_account_balance(test_customer_id)
    print(json.dumps(result, indent=2))

    print("\n2. Testing get_transaction_history...")
    result = get_transaction_history(test_customer_id, num_transactions=5)
    print(json.dumps(result, indent=2))

    print("\n3. Testing get_account_summary...")
    result = get_account_summary(test_customer_id)
    print(json.dumps(result, indent=2))

    print("\n✓ Account Agent functions tested successfully!")
