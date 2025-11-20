#!/usr/bin/env python3
"""
Generate synthetic customer and credit card product data for the call center application.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict

# Seed for reproducibility
random.seed(42)

# Sample data pools
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Daniel", "Nancy", "Matthew", "Lisa",
    "Anthony", "Betty", "Mark", "Margaret", "Donald", "Sandra", "Steven", "Ashley",
    "Andrew", "Kimberly", "Paul", "Emily", "Joshua", "Donna", "Kenneth", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young"
]

STREET_NAMES = [
    "Main", "Oak", "Maple", "Cedar", "Elm", "Washington", "Lake", "Hill",
    "Park", "River", "Pine", "Sunset", "First", "Second", "Third", "Broadway",
    "Lincoln", "Madison", "Church", "Market"
]

CITIES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"), ("Houston", "TX"),
    ("Phoenix", "AZ"), ("Philadelphia", "PA"), ("San Antonio", "TX"), ("San Diego", "CA"),
    ("Dallas", "TX"), ("San Jose", "CA"), ("Austin", "TX"), ("Jacksonville", "FL"),
    ("Fort Worth", "TX"), ("Columbus", "OH"), ("Charlotte", "NC"), ("San Francisco", "CA"),
    ("Indianapolis", "IN"), ("Seattle", "WA"), ("Denver", "CO"), ("Boston", "MA")
]

SECURITY_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "What is your favorite color?",
    "What was the make of your first car?",
    "What is your favorite movie?",
    "What elementary school did you attend?"
]

CREDIT_CARD_TYPES = [
    "UTurn Rewards Plus", "UTurn Cash Back", "UTurn Premium",
    "UTurn Student", "UTurn Business", "UTurn Travel Elite"
]

TRANSACTION_MERCHANTS = [
    "Amazon", "Walmart", "Target", "Starbucks", "Shell Gas Station",
    "McDonald's", "Whole Foods", "Home Depot", "Best Buy", "Apple Store",
    "Netflix", "Spotify", "Uber", "DoorDash", "CVS Pharmacy",
    "Delta Airlines", "Hilton Hotels", "Restaurant XYZ", "Local Coffee Shop"
]


def generate_customer_id(index: int) -> str:
    """Generate unique customer ID."""
    return f"CUST-{str(index + 10000).zfill(6)}"


def generate_card_number() -> str:
    """Generate realistic masked credit card number."""
    last_four = str(random.randint(1000, 9999))
    return f"****-****-****-{last_four}"


def generate_phone() -> str:
    """Generate US phone number."""
    area_code = random.randint(200, 999)
    exchange = random.randint(200, 999)
    number = random.randint(1000, 9999)
    return f"({area_code}) {exchange}-{number}"


def generate_address() -> Dict[str, str]:
    """Generate random US address."""
    street_num = random.randint(100, 9999)
    street_name = random.choice(STREET_NAMES)
    street_type = random.choice(["St", "Ave", "Blvd", "Dr", "Ln"])
    city, state = random.choice(CITIES)
    zip_code = str(random.randint(10000, 99999))

    return {
        "street": f"{street_num} {street_name} {street_type}",
        "city": city,
        "state": state,
        "zip_code": zip_code
    }


def generate_transactions(num_transactions: int, card_type: str) -> List[Dict]:
    """Generate transaction history."""
    transactions = []
    current_date = datetime.now()

    for i in range(num_transactions):
        days_ago = random.randint(0, 90)
        transaction_date = current_date - timedelta(days=days_ago)

        merchant = random.choice(TRANSACTION_MERCHANTS)

        # Different spending patterns by card type
        if "Premium" in card_type or "Travel" in card_type:
            amount = round(random.uniform(50, 1500), 2)
        elif "Student" in card_type:
            amount = round(random.uniform(5, 150), 2)
        else:
            amount = round(random.uniform(10, 500), 2)

        transaction_type = random.choice(["Purchase", "Purchase", "Purchase", "Refund"])

        if transaction_type == "Refund":
            amount = -abs(amount)

        transactions.append({
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "date": transaction_date.strftime("%Y-%m-%d"),
            "merchant": merchant,
            "amount": amount,
            "type": transaction_type,
            "status": "Posted" if days_ago > 2 else "Pending"
        })

    # Sort by date descending
    transactions.sort(key=lambda x: x['date'], reverse=True)
    return transactions


def generate_customer(index: int) -> Dict:
    """Generate a complete customer record."""
    customer_id = generate_customer_id(index)
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    card_type = random.choice(CREDIT_CARD_TYPES)

    # Credit limit based on card type
    credit_limits = {
        "UTurn Student": random.randint(500, 2000),
        "UTurn Cash Back": random.randint(2000, 10000),
        "UTurn Rewards Plus": random.randint(5000, 15000),
        "UTurn Premium": random.randint(10000, 30000),
        "UTurn Business": random.randint(15000, 50000),
        "UTurn Travel Elite": random.randint(20000, 50000)
    }

    credit_limit = credit_limits.get(card_type, 5000)

    # Generate realistic balance (0-80% of credit limit)
    current_balance = round(random.uniform(0, credit_limit * 0.8), 2)
    available_credit = round(credit_limit - current_balance, 2)

    # Generate payment info
    min_payment = round(max(25, current_balance * 0.02), 2)
    last_payment = round(random.uniform(min_payment, current_balance * 0.5), 2) if current_balance > 0 else 0

    # Payment due date (random day 5-28 of next month)
    payment_due_day = random.randint(5, 28)
    next_month = datetime.now() + timedelta(days=30)
    payment_due_date = next_month.replace(day=payment_due_day).strftime("%Y-%m-%d")

    # Account open date (1-10 years ago)
    days_open = random.randint(365, 3650)
    account_open_date = (datetime.now() - timedelta(days=days_open)).strftime("%Y-%m-%d")

    # Security settings
    security_question = random.choice(SECURITY_QUESTIONS)
    pin = str(random.randint(1000, 9999))

    # Fraud status
    fraud_flag = random.choice([False] * 95 + [True] * 5)  # 5% fraud rate
    card_status = "Locked" if fraud_flag else random.choice(["Active"] * 95 + ["Inactive"] * 5)

    # APR based on card type and customer profile
    apr_ranges = {
        "UTurn Student": (18.99, 24.99),
        "UTurn Cash Back": (15.99, 21.99),
        "UTurn Rewards Plus": (13.99, 19.99),
        "UTurn Premium": (11.99, 16.99),
        "UTurn Business": (12.99, 18.99),
        "UTurn Travel Elite": (10.99, 15.99)
    }
    apr_range = apr_ranges.get(card_type, (15.99, 21.99))
    apr = round(random.uniform(apr_range[0], apr_range[1]), 2)

    # Generate transactions
    num_transactions = random.randint(10, 50)
    transactions = generate_transactions(num_transactions, card_type)

    # Credit score (for eligibility checks)
    credit_score = random.randint(580, 850)

    customer = {
        "customer_id": customer_id,
        "personal_info": {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "email": f"{first_name.lower()}.{last_name.lower()}@email.com",
            "phone": generate_phone(),
            "address": generate_address(),
            "date_of_birth": (datetime.now() - timedelta(days=random.randint(6570, 25550))).strftime("%Y-%m-%d")
        },
        "account_info": {
            "card_number_masked": generate_card_number(),
            "card_type": card_type,
            "card_status": card_status,
            "account_open_date": account_open_date,
            "credit_limit": credit_limit,
            "current_balance": current_balance,
            "available_credit": available_credit,
            "apr": apr,
            "annual_fee": 0 if "Student" in card_type or "Cash Back" in card_type else random.choice([95, 195, 450]),
            "rewards_balance": random.randint(0, 50000),
            "rewards_program": "Points" if "Rewards" in card_type else "Cash Back" if "Cash" in card_type else "Miles"
        },
        "payment_info": {
            "minimum_payment_due": min_payment,
            "payment_due_date": payment_due_date,
            "last_payment_amount": last_payment,
            "last_payment_date": (datetime.now() - timedelta(days=random.randint(5, 30))).strftime("%Y-%m-%d"),
            "autopay_enabled": random.choice([True, False])
        },
        "security": {
            "pin": pin,
            "security_question": security_question,
            "security_answer": "SecureAnswer123",  # Simplified for demo
            "fraud_alerts": [
                {
                    "alert_id": f"FRAUD-{random.randint(1000, 9999)}",
                    "date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                    "description": "Unusual spending pattern detected",
                    "status": "Resolved"
                }
            ] if fraud_flag else [],
            "card_locked": fraud_flag,
            "last_verified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "credit_profile": {
            "credit_score": credit_score,
            "income": random.randint(30000, 200000),
            "employment_status": random.choice(["Employed", "Self-Employed", "Student"])
        },
        "transactions": transactions[:10],  # Most recent 10 for quick access
        "full_transaction_history": transactions  # Complete history
    }

    return customer


def generate_credit_card_products() -> List[Dict]:
    """Generate credit card product catalog."""
    products = [
        {
            "product_id": "CARD-001",
            "product_name": "UTurn Student Card",
            "category": "Student",
            "description": "Perfect for students building credit. No annual fee and easy approval.",
            "features": [
                "No annual fee",
                "1% cash back on all purchases",
                "No foreign transaction fees",
                "Free credit score monitoring",
                "Late fee waiver for first late payment"
            ],
            "apr_range": "18.99% - 24.99%",
            "annual_fee": 0,
            "credit_limit_range": "$500 - $2,000",
            "rewards_program": {
                "type": "Cash Back",
                "rate": "1% on all purchases"
            },
            "eligibility": {
                "minimum_credit_score": 0,
                "minimum_income": 0,
                "student_status_required": True
            },
            "benefits": [
                "Build credit history",
                "Financial literacy resources",
                "Upgrade path to premium cards"
            ]
        },
        {
            "product_id": "CARD-002",
            "product_name": "UTurn Cash Back Card",
            "category": "Cashback",
            "description": "Earn generous cash back on everyday purchases with no annual fee.",
            "features": [
                "No annual fee",
                "2% cash back on groceries and gas",
                "1.5% cash back on all other purchases",
                "0% intro APR for 12 months on purchases",
                "No rotating categories"
            ],
            "apr_range": "15.99% - 21.99%",
            "annual_fee": 0,
            "credit_limit_range": "$2,000 - $10,000",
            "rewards_program": {
                "type": "Cash Back",
                "rate": "Up to 2% on select categories, 1.5% on everything else"
            },
            "eligibility": {
                "minimum_credit_score": 670,
                "minimum_income": 25000,
                "student_status_required": False
            },
            "benefits": [
                "Simple cash back structure",
                "No annual fee",
                "Fraud protection",
                "Purchase protection"
            ]
        },
        {
            "product_id": "CARD-003",
            "product_name": "UTurn Rewards Plus Card",
            "category": "Rewards",
            "description": "Maximize your rewards with points that never expire and flexible redemption.",
            "features": [
                "3x points on dining and entertainment",
                "2x points on travel",
                "1x points on all other purchases",
                "50,000 point sign-up bonus after $3,000 spend in 3 months",
                "No foreign transaction fees",
                "Points never expire"
            ],
            "apr_range": "13.99% - 19.99%",
            "annual_fee": 95,
            "credit_limit_range": "$5,000 - $15,000",
            "rewards_program": {
                "type": "Points",
                "rate": "Up to 3x points on select categories"
            },
            "eligibility": {
                "minimum_credit_score": 700,
                "minimum_income": 40000,
                "student_status_required": False
            },
            "benefits": [
                "Travel insurance",
                "Purchase protection",
                "Extended warranty",
                "24/7 concierge service",
                "Points transfer to airline partners"
            ]
        },
        {
            "product_id": "CARD-004",
            "product_name": "UTurn Premium Card",
            "category": "Premium",
            "description": "Elite benefits and luxury perks for discerning cardholders.",
            "features": [
                "5x points on travel booked through UTurn Travel",
                "3x points on dining",
                "1x points on all other purchases",
                "75,000 point sign-up bonus",
                "$300 annual travel credit",
                "Global Entry or TSA PreCheck credit",
                "Priority Pass lounge access"
            ],
            "apr_range": "11.99% - 16.99%",
            "annual_fee": 450,
            "credit_limit_range": "$10,000 - $30,000",
            "rewards_program": {
                "type": "Points",
                "rate": "Up to 5x points on travel and dining"
            },
            "eligibility": {
                "minimum_credit_score": 750,
                "minimum_income": 75000,
                "student_status_required": False
            },
            "benefits": [
                "Comprehensive travel insurance",
                "Trip delay reimbursement",
                "Lost luggage insurance",
                "Rental car insurance",
                "24/7 premium concierge",
                "No foreign transaction fees",
                "Complimentary hotel elite status"
            ]
        },
        {
            "product_id": "CARD-005",
            "product_name": "UTurn Business Card",
            "category": "Business",
            "description": "Powerful rewards and tools for small business owners.",
            "features": [
                "2x points on all business purchases",
                "5% cash back on office supplies and telecom",
                "Employee cards at no additional cost",
                "Expense management tools",
                "Integration with accounting software",
                "0% intro APR for 9 months"
            ],
            "apr_range": "12.99% - 18.99%",
            "annual_fee": 0,
            "credit_limit_range": "$15,000 - $50,000",
            "rewards_program": {
                "type": "Points/Cash Back",
                "rate": "Up to 5% cash back on select business categories"
            },
            "eligibility": {
                "minimum_credit_score": 680,
                "minimum_income": 50000,
                "business_required": True
            },
            "benefits": [
                "Detailed expense reports",
                "Employee spending controls",
                "Business insurance options",
                "Extended payment terms",
                "Dedicated business support"
            ]
        },
        {
            "product_id": "CARD-006",
            "product_name": "UTurn Travel Elite Card",
            "category": "Travel",
            "description": "Ultimate travel rewards and benefits for frequent travelers.",
            "features": [
                "10x points on hotels and rental cars",
                "5x points on flights",
                "3x points on other travel",
                "100,000 point sign-up bonus",
                "$250 annual travel credit",
                "Free checked bags on partner airlines",
                "Priority boarding",
                "Travel accident insurance"
            ],
            "apr_range": "10.99% - 15.99%",
            "annual_fee": 195,
            "credit_limit_range": "$20,000 - $50,000",
            "rewards_program": {
                "type": "Miles",
                "rate": "Up to 10x miles on travel purchases"
            },
            "eligibility": {
                "minimum_credit_score": 720,
                "minimum_income": 60000,
                "student_status_required": False
            },
            "benefits": [
                "No foreign transaction fees",
                "Trip cancellation insurance",
                "Travel delay reimbursement",
                "Lost luggage reimbursement",
                "Rental car insurance",
                "Airport lounge access",
                "Airline fee credits",
                "Hotel elite status"
            ]
        }
    ]

    return products


def generate_knowledge_base_documents():
    """Generate documents for knowledge base ingestion."""

    # Customer FAQ documents
    faqs = [
        {
            "doc_id": "FAQ-001",
            "category": "Account Management",
            "question": "How do I activate my new credit card?",
            "answer": "You can activate your new UTurn credit card by calling our automated activation line at 1-800-UTURN-01, using our mobile app, or logging into your online account. Activation typically takes less than 2 minutes."
        },
        {
            "doc_id": "FAQ-002",
            "category": "Security",
            "question": "What should I do if my card is lost or stolen?",
            "answer": "Immediately call our 24/7 fraud hotline at 1-800-FRAUD-00 to report your card as lost or stolen. We'll lock your card and send you a replacement within 3-5 business days. You're not responsible for any fraudulent charges made after reporting."
        },
        {
            "doc_id": "FAQ-003",
            "category": "Payments",
            "question": "When is my payment due?",
            "answer": "Your payment due date is shown on your monthly statement and in your online account. Payments are typically due 25 days after your statement closing date. To avoid late fees, payments must be received by 5 PM ET on the due date."
        },
        {
            "doc_id": "FAQ-004",
            "category": "Rewards",
            "question": "How do I redeem my rewards?",
            "answer": "UTurn rewards can be redeemed through your online account or mobile app. Options include: statement credits, direct deposit to your bank account, gift cards, travel bookings, or merchandise. Most redemptions process within 1-2 business days."
        },
        {
            "doc_id": "FAQ-005",
            "category": "Credit Limit",
            "question": "Can I request a credit limit increase?",
            "answer": "Yes! You can request a credit limit increase through your online account or by calling customer service. We review requests based on your payment history, credit utilization, and overall credit profile. Most requests are reviewed within 24 hours."
        }
    ]

    # Policy documents
    policies = [
        {
            "doc_id": "POLICY-001",
            "category": "Fraud Protection",
            "title": "UTurn Fraud Protection Policy",
            "content": "UTurn provides comprehensive fraud protection for all cardholders. Our advanced monitoring systems detect suspicious activity 24/7. If fraud is suspected, we'll contact you immediately. You have zero liability for unauthorized charges. Our fraud resolution specialists work quickly to resolve issues and protect your account."
        },
        {
            "doc_id": "POLICY-002",
            "category": "Dispute Resolution",
            "title": "Transaction Dispute Process",
            "content": "If you notice an incorrect charge, you have 60 days from the statement date to dispute it. Contact us at 1-800-UTURN-01 or through your online account. We'll investigate the dispute and issue a provisional credit within 10 business days. Final resolution typically takes 30-90 days depending on merchant response."
        },
        {
            "doc_id": "POLICY-003",
            "category": "Privacy",
            "title": "Customer Privacy Policy",
            "content": "UTurn takes your privacy seriously. We never sell your personal information to third parties. Your data is encrypted and protected by industry-leading security measures. We only share information as required by law or as necessary to process your transactions. You can review our full privacy policy at uturn.com/privacy."
        }
    ]

    return {"faqs": faqs, "policies": policies}


def main():
    """Generate all synthetic data."""
    print("Generating synthetic data for UTurn Credit Card Customer Service...")

    # Generate 50 customer accounts
    print("\n📊 Generating 50 customer accounts...")
    customers = [generate_customer(i) for i in range(50)]

    # Save customer data
    with open('/home/user/UTurnCreditAgent/data/customer_data/customers.json', 'w') as f:
        json.dump(customers, f, indent=2)
    print(f"✓ Saved {len(customers)} customer records to data/customer_data/customers.json")

    # Generate credit card products
    print("\n💳 Generating credit card products...")
    products = generate_credit_card_products()

    with open('/home/user/UTurnCreditAgent/data/product_data/credit_card_products.json', 'w') as f:
        json.dump(products, f, indent=2)
    print(f"✓ Saved {len(products)} product records to data/product_data/credit_card_products.json")

    # Generate knowledge base documents
    print("\n📚 Generating knowledge base documents...")
    kb_docs = generate_knowledge_base_documents()

    with open('/home/user/UTurnCreditAgent/data/customer_data/knowledge_base_faqs.json', 'w') as f:
        json.dump(kb_docs['faqs'], f, indent=2)
    print(f"✓ Saved {len(kb_docs['faqs'])} FAQ documents to data/customer_data/knowledge_base_faqs.json")

    with open('/home/user/UTurnCreditAgent/data/customer_data/knowledge_base_policies.json', 'w') as f:
        json.dump(kb_docs['policies'], f, indent=2)
    print(f"✓ Saved {len(kb_docs['policies'])} policy documents to data/customer_data/knowledge_base_policies.json")

    # Generate summary statistics
    print("\n📈 Customer Data Summary:")
    print(f"  • Total Customers: {len(customers)}")
    print(f"  • Total Credit Limit: ${sum(c['account_info']['credit_limit'] for c in customers):,.2f}")
    print(f"  • Total Outstanding Balance: ${sum(c['account_info']['current_balance'] for c in customers):,.2f}")
    print(f"  • Average Credit Score: {sum(c['credit_profile']['credit_score'] for c in customers) / len(customers):.0f}")
    print(f"  • Fraud Alerts: {sum(1 for c in customers if c['security']['card_locked'])}")

    print("\n💳 Product Catalog Summary:")
    for product in products:
        print(f"  • {product['product_name']}: ${product['annual_fee']}/year, {product['rewards_program']['rate']}")

    print("\n✅ All synthetic data generated successfully!")
    print("\nNext steps:")
    print("  1. Create Bedrock Knowledge Bases")
    print("  2. Upload customer data and product data")
    print("  3. Deploy agents with access to these data sources")


if __name__ == "__main__":
    main()
