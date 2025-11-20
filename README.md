# UTurn Credit Card Customer Service Call Center

An AI-powered credit card customer service system built with AWS Bedrock Agent Core, Nova models, and Strands for multi-agent orchestration with speech-to-speech capabilities.

## 🎯 Overview

This project implements a sophisticated multi-agent call center system for credit card customer service using:

- **AWS Bedrock Agent Core** - Serverless agent deployment platform
- **Amazon Nova Models** - Latest LLM models for natural conversations
- **Strands** - Advanced agent orchestration framework
- **OpenSearch/Knowledge Bases** - Vector storage for RAG capabilities
- **Speech-to-Speech** - Real-time voice interactions

## 🏗️ Architecture

```
┌─────────────┐
│   Customer  │ (Voice/Text Input)
└──────┬──────┘
       │
       v
┌──────────────────────────┐
│  WebSocket Orchestrator  │ (Python Server)
│  + Nova Sonic (S2S)      │
└───────────┬──────────────┘
            │
            ├─────────────┬─────────────┬──────────────┐
            v             v             v              v
    ┌───────────────┐ ┌──────────┐ ┌─────────┐  ┌──────────┐
    │ Authorization │ │ Account  │ │  Sales  │  │Knowledge │
    │     Agent     │ │  Agent   │ │  Agent  │  │  Bases   │
    └───────────────┘ └──────────┘ └─────────┘  └──────────┘
         │                 │            │             │
         └─────────────────┴────────────┴─────────────┘
                           │
                    Customer Data Store
```

## 🤖 Three Specialized Agents

### 1. Authorization Agent
**Handles:** Security, Authentication, Fraud Detection

**Capabilities:**
- Customer identity verification (PIN, security questions, biometrics)
- Fraud status monitoring and alerts
- Card lock/unlock operations
- Security settings management (PIN updates, security questions)
- Suspicious transaction reporting
- Real-time fraud detection

**Tools:**
- `verify_customer_identity()` - Multi-factor authentication
- `check_fraud_status()` - Real-time fraud monitoring
- `lock_unlock_card()` - Card security controls
- `update_security_settings()` - Security configuration
- `report_suspicious_transaction()` - Fraud reporting
- `get_security_summary()` - Comprehensive security overview

### 2. Account Agent
**Handles:** Account Information, Transactions, Payments

**Capabilities:**
- Account balance and credit inquiries
- Transaction history retrieval and search
- Payment processing
- Statement generation
- Rewards balance management
- Autopay configuration
- Credit utilization monitoring

**Tools:**
- `get_account_balance()` - Real-time balance information
- `get_transaction_history()` - Transaction retrieval
- `search_transactions()` - Transaction search
- `make_payment()` - Payment processing
- `get_statement()` - Statement generation
- `get_rewards_balance()` - Rewards information
- `update_autopay()` - Autopay configuration
- `get_account_summary()` - Comprehensive account overview

### 3. Sales Agent
**Handles:** Product Information, Eligibility, Applications

**Capabilities:**
- Credit card product catalog
- Eligibility assessment
- Personalized offers and recommendations
- Application processing
- Product comparisons
- Upgrade recommendations
- Credit limit increase requests

**Tools:**
- `get_available_products()` - Product catalog browsing
- `get_product_details()` - Detailed product information
- `check_eligibility()` - Eligibility assessment
- `get_personalized_offers()` - Personalized recommendations
- `process_application()` - Application processing
- `compare_products()` - Side-by-side comparison

## 📊 Synthetic Data

The system includes comprehensive synthetic data for testing:

- **50 Customer Accounts** with realistic profiles
- **6 Credit Card Products** (Student, Cash Back, Rewards, Premium, Business, Travel)
- **Complete Transaction Histories** (10-50 transactions per customer)
- **Credit Profiles** (scores, income, employment)
- **Security Information** (PINs, security questions, fraud alerts)
- **Knowledge Base Documents** (FAQs, policies, procedures)

### Data Statistics
- Total Credit Limit: $889,443
- Total Outstanding Balance: $396,502
- Average Credit Score: 722
- Fraud Alerts: 5 flagged accounts

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** with permissions for:
   - AWS Bedrock Agent Core
   - Amazon Bedrock
   - Amazon OpenSearch/Knowledge Bases
   - ECR (Elastic Container Registry)
   - Lambda
   - IAM

2. **AWS Credentials** configured:
   ```bash
   export AWS_ACCESS_KEY_ID="your_key"
   export AWS_SECRET_ACCESS_KEY="your_secret"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

3. **Python 3.8+** installed

### Installation

1. **Clone the repository:**
   ```bash
   cd UTurnCreditAgent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r agent-core/requirements.txt
   ```

3. **Generate synthetic data:**
   ```bash
   python3 data/generate_synthetic_data.py
   ```

### Deploy Agents

**Option 1: Deploy all agents at once**
```bash
cd agent-core
./deploy_all_agents.sh
```

**Option 2: Deploy agents individually**
```bash
# Deploy Authorization Agent
cd agent-core/authorization_agent
python3 deploy.py

# Deploy Account Agent
cd agent-core/account_agent
python3 deploy.py

# Deploy Sales Agent
cd agent-core/sales_agent
python3 deploy.py
```

Deployment takes 5-10 minutes per agent.

## 📁 Project Structure

```
UTurnCreditAgent/
├── agent-core/
│   ├── authorization_agent/
│   │   ├── authorization_agent.py    # Agent implementation
│   │   ├── deploy.py                 # Deployment script
│   │   └── requirements.txt
│   ├── account_agent/
│   │   ├── account_agent.py
│   │   ├── deploy.py
│   │   └── requirements.txt
│   ├── sales_agent/
│   │   ├── sales_agent.py
│   │   ├── deploy.py
│   │   └── requirements.txt
│   ├── deploy_all_agents.sh          # Master deployment script
│   └── requirements.txt
├── data/
│   ├── customer_data/
│   │   ├── customers.json            # 50 synthetic customers
│   │   ├── knowledge_base_faqs.json
│   │   └── knowledge_base_policies.json
│   ├── product_data/
│   │   └── credit_card_products.json # 6 credit card products
│   └── generate_synthetic_data.py
├── python-server/                     # WebSocket orchestrator (to be added)
│   ├── server.py
│   ├── s2s_session_manager.py
│   └── integration/
└── README.md
```

## 🔧 Configuration

### Region Configuration
Default region: `us-east-1`

To change region, update in deployment scripts:
```python
REGION = "us-west-2"  # Your preferred region
```

### Agent Names
- Authorization Agent: `uturn_authorization_agent`
- Account Agent: `uturn_account_agent`
- Sales Agent: `uturn_sales_agent`

### Models Used
- **Orchestrator**: `amazon.nova-sonic-v1:0` (Speech-to-Speech)
- **Agents**: `amazon.nova-lite-v1:0` (Fast, cost-effective)

## 🧪 Testing Agents

Each agent can be tested locally before deployment:

```bash
# Test Authorization Agent
python3 agent-core/authorization_agent/authorization_agent.py

# Test Account Agent
python3 agent-core/account_agent/account_agent.py

# Test Sales Agent
python3 agent-core/sales_agent/sales_agent.py
```

### Sample Test Customer
- Customer ID: `CUST-010000`
- Name: Linda Johnson
- Card: UTurn Travel Elite
- PIN: `1488`
- Balance: $24,989.54
- Credit Limit: $42,174

## 📚 Knowledge Bases

### Setup Knowledge Bases

The system uses separate knowledge bases for different agent types:

1. **Authorization/Account KB** - Shared customer data, account info, security
2. **Sales KB** - Product catalog, offers, eligibility criteria

### Creating Knowledge Bases

**Option 1: AWS Bedrock Knowledge Bases** (Recommended)
- Fully managed vector store
- Built-in OpenSearch Serverless
- Easy integration with agents

**Option 2: Self-Managed OpenSearch**
- More control over configuration
- Custom indexing strategies
- Advanced query capabilities

Script to create knowledge bases (to be run after getting valid AWS credentials):
```bash
python3 scripts/create_knowledge_bases.py
```

## 🎙️ WebSocket Orchestrator

The WebSocket server coordinates between:
- Frontend (voice/text input)
- Nova Sonic (speech-to-speech)
- Three specialized agents
- Knowledge bases

### Key Features:
- Real-time audio streaming
- Session state management
- Multi-agent routing
- Tool execution coordination
- Response synthesis

## 🔐 Security Considerations

- Customer PINs and sensitive data encrypted at rest
- All agent communications over TLS
- IAM roles with least privilege
- Audit logging for compliance
- No hard-coded credentials
- Fraud detection on all transactions

## 💡 Example Interactions

### Authorization Agent
```
Customer: "I need to reset my PIN"
Agent: "I can help you with that. First, let me verify your identity.
        Can you please provide your date of birth?"
Customer: "May 27, 2003"
Agent: "Thank you. Your identity has been verified. What would you
        like your new 4-digit PIN to be?"
```

### Account Agent
```
Customer: "What's my current balance?"
Agent: "Your current balance is $24,989.54 with available credit of
        $17,184.46. Your minimum payment of $499.79 is due on
        December 23rd. Would you like to make a payment now?"
```

### Sales Agent
```
Customer: "I'm interested in a card with better travel rewards"
Agent: "Based on your excellent credit score of 677 and income,
        I recommend the UTurn Travel Elite Card. You'll earn 10x
        miles on hotels and 5x on flights, plus a $250 annual
        travel credit. Would you like to apply?"
```

## 🚧 Roadmap

- [x] Build three specialized agents
- [x] Generate synthetic customer data
- [x] Create deployment scripts
- [ ] Set up OpenSearch Knowledge Bases
- [ ] Implement WebSocket orchestrator
- [ ] Add React frontend
- [ ] Integrate Nova Sonic for S2S
- [ ] Add call recording and transcription
- [ ] Implement analytics dashboard
- [ ] Add A/B testing capabilities

## 📊 Cost Estimation

### Per-Agent Costs (AWS us-east-1)
- AgentCore Runtime: ~$0.06/hour when idle, $0.24/hour active
- Nova Lite inference: ~$0.06/1M input tokens, $0.24/1M output tokens
- ECR storage: ~$0.10/GB-month
- CloudWatch logs: ~$0.50/GB

### Estimated Monthly Cost (Low Traffic)
- 3 Agents: ~$150/month
- OpenSearch Serverless: ~$700/month (can use free tier initially)
- **Total: ~$850/month** for development/testing

## 🤝 Contributing

This is a demonstration project. For production use:
1. Replace synthetic data with real database
2. Add proper authentication and authorization
3. Implement comprehensive error handling
4. Add monitoring and alerting
5. Conduct security audit
6. Add unit and integration tests
7. Implement CI/CD pipeline

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## 🆘 Support

For issues or questions:
1. Check AWS Bedrock Agent Core documentation
2. Review CloudWatch logs for agent execution
3. Test agents locally before deployment
4. Verify IAM permissions are correct

## 🔗 Resources

- [AWS Bedrock Agent Core Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Nova Models](https://aws.amazon.com/bedrock/nova/)
- [Strands Agent Framework](https://github.com/awslabs/strands)
- [AWS OpenSearch Service](https://aws.amazon.com/opensearch-service/)

---

**Built with ❤️ using AWS Bedrock Agent Core and Amazon Nova**

*Ready to deploy once valid AWS credentials are provided!*
