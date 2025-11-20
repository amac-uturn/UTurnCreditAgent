"""
Lambda function for handling UTurn Credit Card agent invocations
Integrates with Bedrock Agent Core and Knowledge Bases
"""

import json
import os
import boto3
from typing import Dict, List, Any

# Initialize clients
bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

# Agent configuration
AGENT_CONFIG = {
    'authorization': {
        'arn': os.environ.get('AUTH_AGENT_ARN', 'arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_authorization_agent-wAauASEhv8'),
        'kb_id': os.environ.get('CUSTOMER_KB_ID', 'CHLRUJKM5Q')
    },
    'account': {
        'arn': os.environ.get('ACCOUNT_AGENT_ARN', 'arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_account_agent-55xVu6Cv86'),
        'kb_id': os.environ.get('CUSTOMER_KB_ID', 'CHLRUJKM5Q')
    },
    'sales': {
        'arn': os.environ.get('SALES_AGENT_ARN', 'arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_sales_agent-GcC04WEVGN'),
        'kb_id': os.environ.get('SALES_KB_ID', 'FNW2BSTB0J')
    }
}


def route_to_agent(user_input: str, customer_id: str = None) -> str:
    """
    Route user input to the appropriate agent based on keywords
    """
    input_lower = user_input.lower()

    # Authorization keywords
    auth_keywords = ['pin', 'security', 'fraud', 'lock', 'unlock', 'stolen', 'lost', 'verify', 'identity']
    # Account keywords
    account_keywords = ['balance', 'transaction', 'payment', 'statement', 'due', 'history', 'autopay']
    # Sales keywords
    sales_keywords = ['apply', 'new card', 'upgrade', 'offer', 'product', 'eligibility', 'compare']

    auth_score = sum(1 for k in auth_keywords if k in input_lower)
    account_score = sum(1 for k in account_keywords if k in input_lower)
    sales_score = sum(1 for k in sales_keywords if k in input_lower)

    if auth_score >= account_score and auth_score >= sales_score and auth_score > 0:
        return 'authorization'
    elif account_score >= sales_score and account_score > 0:
        return 'account'
    elif sales_score > 0:
        return 'sales'
    else:
        return 'account'  # Default to account agent


def query_knowledge_base(kb_id: str, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Query a Bedrock Knowledge Base
    """
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )

        results = []
        for result in response.get('retrievalResults', []):
            results.append({
                'content': result.get('content', {}).get('text', ''),
                'score': result.get('score', 0.0),
                'metadata': result.get('metadata', {})
            })

        return results
    except Exception as e:
        print(f"Error querying KB {kb_id}: {e}")
        return []


def invoke_agent(agent_type: str, user_input: str, customer_id: str = None, session_id: str = None) -> Dict[str, Any]:
    """
    Invoke an Agent Core agent
    """
    agent_config = AGENT_CONFIG.get(agent_type)
    if not agent_config:
        return {
            'error': f'Unknown agent type: {agent_type}',
            'agent': agent_type
        }

    # First, query the Knowledge Base for context
    kb_context = ''
    kb_results = query_knowledge_base(agent_config['kb_id'], user_input)
    if kb_results:
        kb_context = '\n\nRelevant information from knowledge base:\n'
        for idx, result in enumerate(kb_results[:3], 1):
            kb_context += f"{idx}. {result['content'][:200]}...\n"

    # Prepare the prompt with KB context and customer ID
    enhanced_input = user_input
    if customer_id:
        enhanced_input = f"Customer ID: {customer_id}\n\n{user_input}"
    if kb_context:
        enhanced_input += kb_context

    try:
        # Note: Agent Core runtime endpoint invocation
        # For now, we'll return a simulated response since Agent Core
        # requires specific runtime invocation patterns

        # TODO: Implement actual Agent Core invocation
        # This would involve calling the agent runtime endpoint

        response = {
            'agent': agent_type,
            'customer_id': customer_id,
            'message': f"[{agent_type.upper()} AGENT] Processed your request: {user_input[:50]}...",
            'kb_results_used': len(kb_results),
            'session_id': session_id or 'new-session'
        }

        return response

    except Exception as e:
        print(f"Error invoking agent {agent_type}: {e}")
        return {
            'error': str(e),
            'agent': agent_type
        }


def lambda_handler(event, context):
    """
    Main Lambda handler for agent invocations
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})

        user_input = body.get('message', body.get('input', ''))
        customer_id = body.get('customer_id', 'CUST-010000')
        agent_type = body.get('agent_type')
        session_id = body.get('session_id')

        if not user_input:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required field: message'
                })
            }

        # Route to agent if not specified
        if not agent_type:
            agent_type = route_to_agent(user_input, customer_id)

        # Invoke the agent
        response = invoke_agent(agent_type, user_input, customer_id, session_id)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(response)
        }

    except Exception as e:
        print(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }


# For testing locally
if __name__ == '__main__':
    test_event = {
        'body': json.dumps({
            'message': 'What is my current balance?',
            'customer_id': 'CUST-010000'
        })
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
