#!/usr/bin/env python3
"""
Sales Agent for UTurn Credit Card Customer Service
Handles: Product Information, Eligibility Checks, Card Applications, Upgrades, Offers
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Load customer and product data
CUSTOMER_DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data/customer_data/customers.json')
PRODUCT_DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data/product_data/credit_card_products.json')

def load_customer_data() -> Dict:
    """Load customer data from JSON file."""
    try:
        with open(CUSTOMER_DATA_PATH, 'r') as f:
            customers = json.load(f)
        return {c['customer_id']: c for c in customers}
    except Exception as e:
        print(f"Error loading customer data: {e}")
        return {}

def load_product_data() -> List[Dict]:
    """Load product data from JSON file."""
    try:
        with open(PRODUCT_DATA_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading product data: {e}")
        return []

# Load data at module level
CUSTOMERS = load_customer_data()
PRODUCTS = load_product_data()
PRODUCTS_BY_ID = {p['product_id']: p for p in PRODUCTS}


def get_available_products(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get available credit card products.

    Args:
        category: Optional filter by category (Student, Cashback, Rewards, Premium, Business, Travel)

    Returns:
        Dict with product information
    """
    if category:
        filtered_products = [p for p in PRODUCTS if p['category'].lower() == category.lower()]
    else:
        filtered_products = PRODUCTS

    return {
        "total_products": len(filtered_products),
        "category_filter": category,
        "products": [
            {
                "product_id": p['product_id'],
                "product_name": p['product_name'],
                "category": p['category'],
                "description": p['description'],
                "annual_fee": p['annual_fee'],
                "apr_range": p['apr_range'],
                "rewards_rate": p['rewards_program']['rate'],
                "key_features": p['features'][:3]  # Top 3 features
            }
            for p in filtered_products
        ],
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_product_details(product_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific credit card product.

    Args:
        product_id: Product ID

    Returns:
        Dict with detailed product information
    """
    if product_id not in PRODUCTS_BY_ID:
        return {
            "error": f"Product ID {product_id} not found",
            "available_products": [p['product_id'] for p in PRODUCTS]
        }

    product = PRODUCTS_BY_ID[product_id]

    return {
        "product_id": product['product_id'],
        "product_name": product['product_name'],
        "category": product['category'],
        "description": product['description'],
        "annual_fee": product['annual_fee'],
        "apr_range": product['apr_range'],
        "credit_limit_range": product['credit_limit_range'],
        "features": product['features'],
        "rewards_program": product['rewards_program'],
        "benefits": product['benefits'],
        "eligibility_requirements": product['eligibility'],
        "best_for": get_product_recommendation_reason(product),
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_product_recommendation_reason(product: Dict) -> str:
    """Generate a recommendation reason for a product."""
    category = product['category']

    reasons = {
        "Student": "Students and young adults building credit history",
        "Cashback": "Everyday spending with simple, straightforward rewards",
        "Rewards": "Maximizing rewards on dining, entertainment, and travel",
        "Premium": "Frequent travelers seeking luxury benefits and comprehensive insurance",
        "Business": "Small business owners managing expenses and earning rewards",
        "Travel": "Dedicated travelers who want to maximize airline and hotel rewards"
    }

    return reasons.get(category, "Great all-around credit card option")


def check_eligibility(customer_id: str, product_id: str) -> Dict[str, Any]:
    """
    Check if a customer is eligible for a specific credit card product.

    Args:
        customer_id: Customer ID
        product_id: Product ID to check eligibility for

    Returns:
        Dict with eligibility results and recommendations
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    if product_id not in PRODUCTS_BY_ID:
        return {
            "error": f"Product ID {product_id} not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    product = PRODUCTS_BY_ID[product_id]

    credit_profile = customer['credit_profile']
    requirements = product['eligibility']

    # Check each requirement
    checks = []
    eligible = True

    # Credit score check
    min_credit_score = requirements['minimum_credit_score']
    customer_score = credit_profile['credit_score']
    credit_score_check = customer_score >= min_credit_score

    checks.append({
        "requirement": "Credit Score",
        "required": f"{min_credit_score}+" if min_credit_score > 0 else "Any",
        "customer_value": customer_score,
        "passed": credit_score_check
    })

    if not credit_score_check:
        eligible = False

    # Income check
    min_income = requirements['minimum_income']
    customer_income = credit_profile['income']
    income_check = customer_income >= min_income

    checks.append({
        "requirement": "Minimum Income",
        "required": f"${min_income:,}" if min_income > 0 else "Any",
        "customer_value": f"${customer_income:,}",
        "passed": income_check
    })

    if not income_check:
        eligible = False

    # Student status check (if required)
    if requirements.get('student_status_required'):
        is_student = credit_profile['employment_status'] == 'Student'
        checks.append({
            "requirement": "Student Status",
            "required": "Yes",
            "customer_value": "Yes" if is_student else "No",
            "passed": is_student
        })
        if not is_student:
            eligible = False

    # Business check (if required)
    if requirements.get('business_required'):
        # For demo purposes, assume business customers have higher income
        has_business = customer_income > 50000
        checks.append({
            "requirement": "Business Owner",
            "required": "Yes",
            "customer_value": "Yes" if has_business else "No",
            "passed": has_business
        })
        if not has_business:
            eligible = False

    # Generate recommendation
    if eligible:
        recommendation = f"Great news! You're eligible for the {product['product_name']}. Would you like to proceed with an application?"
    else:
        # Find alternative products
        alternatives = find_alternative_products(customer)
        recommendation = f"You don't meet all requirements for the {product['product_name']} yet. " + \
                        f"Consider these alternatives: {', '.join([p['product_name'] for p in alternatives[:2]])}"

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "product_id": product_id,
        "product_name": product['product_name'],
        "eligible": eligible,
        "eligibility_checks": checks,
        "recommendation": recommendation,
        "alternative_products": find_alternative_products(customer) if not eligible else [],
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def find_alternative_products(customer: Dict) -> List[Dict]:
    """Find alternative products that match customer's profile."""
    credit_score = customer['credit_profile']['credit_score']
    income = customer['credit_profile']['income']

    suitable_products = []

    for product in PRODUCTS:
        requirements = product['eligibility']

        if (credit_score >= requirements['minimum_credit_score'] and
            income >= requirements['minimum_income']):
            suitable_products.append({
                "product_id": product['product_id'],
                "product_name": product['product_name'],
                "category": product['category'],
                "annual_fee": product['annual_fee'],
                "rewards_rate": product['rewards_program']['rate']
            })

    return suitable_products


def get_personalized_offers(customer_id: str) -> Dict[str, Any]:
    """
    Get personalized credit card offers for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        Dict with personalized offers
    """
    if customer_id not in CUSTOMERS:
        return {
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    current_card = customer['account_info']['card_type']
    credit_score = customer['credit_profile']['credit_score']
    income = customer['credit_profile']['income']
    current_balance = customer['account_info']['current_balance']

    offers = []

    # Upgrade offer (if eligible for better card)
    if "Student" in current_card or "Cash Back" in current_card:
        if credit_score >= 700 and income >= 40000:
            offers.append({
                "offer_type": "Upgrade",
                "product_id": "CARD-003",
                "product_name": "UTurn Rewards Plus Card",
                "offer_details": "Upgrade to earn 3x points on dining! No hard credit inquiry required.",
                "bonus": "25,000 bonus points after first purchase",
                "expiration": "Offer expires in 30 days"
            })

    # Balance transfer offer (if they have balance)
    if current_balance > 1000:
        offers.append({
            "offer_type": "Balance Transfer",
            "product_name": "Current Card - Balance Transfer Offer",
            "offer_details": "0% APR on balance transfers for 12 months",
            "bonus": "No balance transfer fee for the first 60 days",
            "potential_savings": round(current_balance * 0.15, 2),  # Assume 15% APR savings
            "expiration": "Limited time offer"
        })

    # New product offers based on eligibility
    suitable_products = find_alternative_products(customer)

    for product_dict in suitable_products:
        product = PRODUCTS_BY_ID[product_dict['product_id']]

        # Don't offer their current card
        if product['product_name'] == current_card:
            continue

        # Create offer based on product category
        if product['category'] == "Travel" and credit_score >= 720:
            offers.append({
                "offer_type": "New Product",
                "product_id": product['product_id'],
                "product_name": product['product_name'],
                "offer_details": product['rewards_program']['rate'],
                "bonus": "100,000 bonus miles after $3,000 spend in 3 months",
                "expiration": "Apply by end of month"
            })

        elif product['category'] == "Premium" and credit_score >= 750 and income >= 75000:
            offers.append({
                "offer_type": "Premium Invitation",
                "product_id": product['product_id'],
                "product_name": product['product_name'],
                "offer_details": "Exclusive invitation to our premium card with luxury benefits",
                "bonus": "$300 annual travel credit + 75,000 bonus points",
                "expiration": "Invitation valid for 60 days"
            })

    return {
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "current_card": current_card,
        "total_offers": len(offers),
        "personalized_offers": offers,
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def process_application(customer_id: str, product_id: str) -> Dict[str, Any]:
    """
    Process a credit card application.

    Args:
        customer_id: Customer ID
        product_id: Product ID to apply for

    Returns:
        Dict with application result
    """
    if customer_id not in CUSTOMERS:
        return {
            "success": False,
            "error": "Customer ID not found",
            "customer_id": customer_id
        }

    if product_id not in PRODUCTS_BY_ID:
        return {
            "success": False,
            "error": f"Product ID {product_id} not found",
            "customer_id": customer_id
        }

    customer = CUSTOMERS[customer_id]
    product = PRODUCTS_BY_ID[product_id]

    # Check eligibility first
    eligibility = check_eligibility(customer_id, product_id)

    if not eligibility['eligible']:
        return {
            "success": False,
            "message": "Application cannot be processed - eligibility requirements not met",
            "customer_id": customer_id,
            "product_name": product['product_name'],
            "eligibility_details": eligibility['eligibility_checks'],
            "alternatives": eligibility['alternative_products']
        }

    # Simulate application processing
    application_id = f"APP-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Determine approval (for demo, high credit score = instant approval)
    credit_score = customer['credit_profile']['credit_score']

    if credit_score >= 720:
        status = "Approved"
        message = f"Congratulations! Your application for {product['product_name']} has been approved!"
        credit_limit = int(product['credit_limit_range'].split('$')[1].split(' - ')[1].replace(',', ''))
    elif credit_score >= 650:
        status = "Under Review"
        message = f"Your application for {product['product_name']} is under review. You'll receive a decision within 7-10 business days."
        credit_limit = None
    else:
        status = "Pending Additional Information"
        message = "We need additional information to process your application. A specialist will contact you within 2 business days."
        credit_limit = None

    return {
        "success": True,
        "application_id": application_id,
        "status": status,
        "message": message,
        "customer_id": customer_id,
        "customer_name": customer['personal_info']['full_name'],
        "product_applied": {
            "product_id": product_id,
            "product_name": product['product_name'],
            "annual_fee": product['annual_fee'],
            "apr": product['apr_range']
        },
        "approved_credit_limit": credit_limit,
        "next_steps": get_application_next_steps(status),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_application_next_steps(status: str) -> List[str]:
    """Get next steps based on application status."""
    steps = {
        "Approved": [
            "Your new card will arrive in 7-10 business days",
            "Activate your card when it arrives",
            "Set up online account access",
            "Consider setting up autopay"
        ],
        "Under Review": [
            "Check your email for updates",
            "Ensure your phone number is up to date",
            "Have your employment information ready",
            "Decision within 7-10 business days"
        ],
        "Pending Additional Information": [
            "Watch for a call from our application specialists",
            "Gather income verification documents",
            "Check your email for requested information",
            "Response required within 30 days"
        ]
    }

    return steps.get(status, ["Contact customer service for more information"])


def compare_products(product_ids: List[str]) -> Dict[str, Any]:
    """
    Compare multiple credit card products side-by-side.

    Args:
        product_ids: List of product IDs to compare

    Returns:
        Dict with product comparison
    """
    if not product_ids or len(product_ids) < 2:
        return {
            "error": "Please provide at least 2 product IDs to compare",
            "available_products": [p['product_id'] for p in PRODUCTS]
        }

    products_to_compare = []

    for pid in product_ids:
        if pid in PRODUCTS_BY_ID:
            products_to_compare.append(PRODUCTS_BY_ID[pid])
        else:
            return {
                "error": f"Product ID {pid} not found",
                "available_products": [p['product_id'] for p in PRODUCTS]
            }

    # Build comparison matrix
    comparison = {
        "products_compared": len(products_to_compare),
        "comparison": []
    }

    for product in products_to_compare:
        comparison["comparison"].append({
            "product_id": product['product_id'],
            "product_name": product['product_name'],
            "category": product['category'],
            "annual_fee": product['annual_fee'],
            "apr_range": product['apr_range'],
            "rewards_program": product['rewards_program'],
            "credit_limit_range": product['credit_limit_range'],
            "key_features": product['features'][:5],
            "eligibility": product['eligibility'],
            "best_for": get_product_recommendation_reason(product)
        })

    # Add recommendation
    comparison["recommendation"] = generate_comparison_recommendation(products_to_compare)

    return comparison


def generate_comparison_recommendation(products: List[Dict]) -> str:
    """Generate a recommendation based on product comparison."""
    # Simple logic: recommend based on annual fee and rewards
    no_fee_products = [p for p in products if p['annual_fee'] == 0]
    premium_products = [p for p in products if p['annual_fee'] > 200]

    if no_fee_products:
        return f"If you want no annual fee, consider {no_fee_products[0]['product_name']}"
    elif premium_products:
        return f"For premium benefits and travel rewards, {premium_products[0]['product_name']} is the best choice"
    else:
        return f"All are solid choices. Choose based on your spending habits and reward preferences."


# ============================================================================
# AgentCore Entry Point
# ============================================================================

def sales_agent_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for the Sales Agent.
    Handles all sales, product information, and eligibility-related requests.

    This function is called by AWS Bedrock AgentCore when the agent is invoked.
    """

    # Extract input from the event
    user_input = event.get('input', '')
    session_id = event.get('sessionId', 'unknown')

    response_text = f"""Sales Agent activated. I can help you with:
- Browse available credit card products
- Get detailed product information
- Check eligibility for specific cards
- Get personalized offers and recommendations
- Process credit card applications
- Compare different products side-by-side

Please let me know what you're interested in!"""

    return {
        "response": response_text,
        "sessionId": session_id,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test the agent functions
    print("Testing Sales Agent functions...")

    # Test with first customer
    test_customer_id = "CUST-010000"

    print("\n1. Testing get_available_products...")
    result = get_available_products()
    print(f"Found {result['total_products']} products")

    print("\n2. Testing check_eligibility...")
    result = check_eligibility(test_customer_id, "CARD-003")
    print(json.dumps(result, indent=2))

    print("\n3. Testing get_personalized_offers...")
    result = get_personalized_offers(test_customer_id)
    print(json.dumps(result, indent=2))

    print("\n✓ Sales Agent functions tested successfully!")
