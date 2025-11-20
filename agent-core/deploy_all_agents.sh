#!/bin/bash
#
# Master Deployment Script for UTurn Credit Card Customer Service Agents
# Deploys all three agents: Authorization, Account, and Sales
#

set -e

echo "======================================================================"
echo "  UTurn Credit Card Customer Service - Agent Deployment"
echo "======================================================================"
echo ""
echo "This script will deploy three agents to AWS Bedrock AgentCore:"
echo "  1. Authorization Agent - Security, fraud detection, identity verification"
echo "  2. Account Agent - Balances, transactions, payments, statements"
echo "  3. Sales Agent - Products, eligibility, applications, offers"
echo ""
echo "Prerequisites:"
echo "  ✓ AWS credentials configured"
echo "  ✓ Sufficient IAM permissions for AgentCore, ECR, Lambda"
echo "  ✓ Python 3.8+ installed"
echo ""
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deployment cancelled."
    exit 1
fi

# Setup Python virtual environment
echo ""
echo "Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "✓ Virtual environment activated"

# Install core dependencies
echo ""
echo "Installing core dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Core dependencies installed"

# Deploy Authorization Agent
echo ""
echo "======================================================================"
echo "  Deploying Authorization Agent (1/3)"
echo "======================================================================"
cd authorization_agent
pip install -q -r requirements.txt
python3 deploy.py
if [ $? -eq 0 ]; then
    echo "✓ Authorization Agent deployed successfully"
else
    echo "✗ Authorization Agent deployment failed"
    exit 1
fi
cd ..

# Deploy Account Agent
echo ""
echo "======================================================================"
echo "  Deploying Account Agent (2/3)"
echo "======================================================================"
cd account_agent
pip install -q -r requirements.txt
python3 deploy.py
if [ $? -eq 0 ]; then
    echo "✓ Account Agent deployed successfully"
else
    echo "✗ Account Agent deployment failed"
    exit 1
fi
cd ..

# Deploy Sales Agent
echo ""
echo "======================================================================"
echo "  Deploying Sales Agent (3/3)"
echo "======================================================================"
cd sales_agent
pip install -q -r requirements.txt
python3 deploy.py
if [ $? -eq 0 ]; then
    echo "✓ Sales Agent deployed successfully"
else
    echo "✗ Sales Agent deployment failed"
    exit 1
fi
cd ..

# Summary
echo ""
echo "======================================================================"
echo "  All Agents Deployed Successfully!"
echo "======================================================================"
echo ""
echo "Agent Summary:"
echo "  • Authorization Agent: uturn_authorization_agent"
echo "  • Account Agent: uturn_account_agent"
echo "  • Sales Agent: uturn_sales_agent"
echo ""
echo "Next Steps:"
echo "  1. Create OpenSearch Knowledge Bases"
echo "  2. Configure WebSocket orchestrator"
echo "  3. Deploy React frontend"
echo "  4. Test end-to-end system"
echo ""
echo "View agent details in AWS Console:"
echo "  https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore"
echo ""
