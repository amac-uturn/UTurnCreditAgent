"""
Lambda function for Nova Sonic Speech-to-Speech with Agent Core integration
Based on: https://aws.amazon.com/blogs/machine-learning/building-a-multi-agent-voice-assistant-with-amazon-nova-sonic-and-amazon-bedrock-agentcore/
"""

import json
import boto3
import base64
import os
from datetime import datetime
import uuid

# Initialize clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Tables
sessions_table = dynamodb.Table('UTurnVoiceSessions')
messages_table = dynamodb.Table('UTurnVoiceMessages')

# Configuration
NOVA_SONIC_MODEL_ID = 'amazon.nova-sonic-v1:0'

# Agent configuration
AGENTS = {
    'authorization': {
        'arn': os.environ.get('AUTH_AGENT_ARN'),
        'kb_id': os.environ.get('CUSTOMER_KB_ID')
    },
    'account': {
        'arn': os.environ.get('ACCOUNT_AGENT_ARN'),
        'kb_id': os.environ.get('CUSTOMER_KB_ID')
    },
    'sales': {
        'arn': os.environ.get('SALES_AGENT_ARN'),
        'kb_id': os.environ.get('SALES_KB_ID')
    }
}


def route_to_agent(text):
    """Route user input to appropriate agent based on keywords"""
    text_lower = text.lower()

    # Keyword matching
    auth_keywords = ['pin', 'security', 'fraud', 'lock', 'unlock', 'stolen', 'lost', 'verify', 'identity', 'suspicious']
    account_keywords = ['balance', 'transaction', 'payment', 'statement', 'due', 'history', 'autopay', 'credit', 'debt', 'owe']
    sales_keywords = ['apply', 'application', 'new card', 'upgrade', 'offer', 'product', 'eligibility', 'compare', 'reward', 'benefit']

    auth_score = sum(1 for k in auth_keywords if k in text_lower)
    account_score = sum(1 for k in account_keywords if k in text_lower)
    sales_score = sum(1 for k in sales_keywords if k in text_lower)

    if auth_score >= account_score and auth_score >= sales_score and auth_score > 0:
        return 'authorization'
    elif account_score >= sales_score and account_score > 0:
        return 'account'
    elif sales_score > 0:
        return 'sales'
    else:
        return 'account'  # Default


def query_knowledge_base(kb_id, query_text):
    """Query Bedrock Knowledge Base"""
    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': query_text},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 3
                }
            }
        )

        results = []
        for result in response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            if content:
                results.append(content)

        return '\n\n'.join(results[:2])  # Top 2 results

    except Exception as e:
        print(f"Error querying KB {kb_id}: {e}")
        return ""


def invoke_agent_core(agent_type, user_message, customer_id, kb_context=""):
    """
    Invoke Agent Core agent
    For now, returns simulated response. In production, this would call the actual agent endpoint.
    """
    agent_config = AGENTS.get(agent_type)
    if not agent_config:
        return f"Error: Unknown agent type {agent_type}"

    # Build context-aware prompt
    prompt = f"Customer ID: {customer_id}\n\n"

    if kb_context:
        prompt += f"Relevant Information:\n{kb_context}\n\n"

    prompt += f"User Request: {user_message}\n\n"
    prompt += "Please provide a helpful, concise response."

    # TODO: Replace with actual Agent Core runtime invocation
    # For now, simulate agent response based on type
    responses = {
        'authorization': f"I'm your authorization agent. Regarding your security inquiry about {user_message[:30]}... I can help verify your identity, check for fraud alerts, or lock/unlock your card. How would you like me to assist?",
        'account': f"I'm your account agent. Looking at your request about {user_message[:30]}... I can provide information about your balance, recent transactions, or help you make a payment. What specific information do you need?",
        'sales': f"I'm your sales agent. Regarding your interest in {user_message[:30]}... I can show you our available credit cards, check your eligibility, or help you apply. Would you like to see our current offers?"
    }

    return responses.get(agent_type, "I'm here to help with your credit card needs.")


def transcribe_audio_with_nova_sonic(audio_data):
    """
    Transcribe audio using Nova Sonic
    """
    try:
        # Prepare request for Nova Sonic (speech-to-text)
        request_body = {
            "audio": audio_data,  # Base64 encoded audio
            "task": "transcribe",
            "language": "en"
        }

        # Call Nova Sonic for transcription
        response = bedrock_runtime.invoke_model(
            modelId=NOVA_SONIC_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )

        response_body = json.loads(response['body'].read())
        transcription = response_body.get('transcription', {}).get('text', '')

        return transcription

    except Exception as e:
        print(f"Error transcribing with Nova Sonic: {e}")
        # Fallback: return placeholder
        return "[Audio transcription pending - Nova Sonic integration in progress]"


def synthesize_speech_with_nova_sonic(text):
    """
    Convert text to speech using Nova Sonic
    Returns base64 encoded audio data
    """
    try:
        # Prepare request for Nova Sonic (text-to-speech)
        request_body = {
            "text": text,
            "task": "synthesize",
            "voice": "en-US-Neural",
            "outputFormat": "pcm",  # or "opus" for better compression
            "sampleRate": 16000
        }

        # Call Nova Sonic for synthesis
        response = bedrock_runtime.invoke_model(
            modelId=NOVA_SONIC_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )

        response_body = json.loads(response['body'].read())
        audio_data = response_body.get('audio', '')  # Base64 encoded audio

        return audio_data

    except Exception as e:
        print(f"Error synthesizing with Nova Sonic: {e}")
        return ""


def process_speech_to_speech(audio_data, customer_id, session_id):
    """
    Complete speech-to-speech flow:
    1. Transcribe audio with Nova Sonic
    2. Route to appropriate agent
    3. Query Knowledge Base
    4. Invoke agent
    5. Synthesize response with Nova Sonic
    6. Return audio response
    """

    # Step 1: Transcribe audio to text
    print("Step 1: Transcribing audio...")
    user_text = transcribe_audio_with_nova_sonic(audio_data)
    print(f"Transcription: {user_text}")

    if not user_text or user_text.startswith('[Audio'):
        # Return error message as audio
        error_text = "I'm sorry, I couldn't understand that. Could you please repeat?"
        error_audio = synthesize_speech_with_nova_sonic(error_text)
        return {
            'transcription': user_text,
            'agent': 'system',
            'response_text': error_text,
            'response_audio': error_audio
        }

    # Step 2: Route to agent
    print("Step 2: Routing to agent...")
    agent_type = route_to_agent(user_text)
    print(f"Routed to: {agent_type}")

    # Step 3: Query Knowledge Base
    print("Step 3: Querying Knowledge Base...")
    kb_id = AGENTS[agent_type]['kb_id']
    kb_context = query_knowledge_base(kb_id, user_text) if kb_id else ""
    print(f"KB context: {kb_context[:100]}...")

    # Step 4: Invoke agent
    print("Step 4: Invoking agent...")
    response_text = invoke_agent_core(agent_type, user_text, customer_id, kb_context)
    print(f"Agent response: {response_text}")

    # Step 5: Synthesize response to audio
    print("Step 5: Synthesizing speech...")
    response_audio = synthesize_speech_with_nova_sonic(response_text)
    print("Speech synthesis complete")

    # Step 6: Store conversation in DynamoDB
    timestamp = int(datetime.now().timestamp())

    # Store user message
    messages_table.put_item(
        Item={
            'sessionId': session_id,
            'messageId': str(uuid.uuid4()),
            'timestamp': timestamp,
            'role': 'user',
            'content': user_text,
            'agent': agent_type,
            'modality': 'speech'
        }
    )

    # Store assistant response
    messages_table.put_item(
        Item={
            'sessionId': session_id,
            'messageId': str(uuid.uuid4()),
            'timestamp': timestamp + 1,
            'role': 'assistant',
            'content': response_text,
            'agent': agent_type,
            'modality': 'speech'
        }
    )

    return {
        'transcription': user_text,
        'agent': agent_type,
        'response_text': response_text,
        'response_audio': response_audio,
        'kb_used': bool(kb_context)
    }


def lambda_handler(event, context):
    """
    Main Lambda handler for Nova Sonic speech-to-speech
    """

    try:
        connection_id = event['requestContext']['connectionId']
        route_key = event['requestContext']['routeKey']

        print(f"Route: {route_key}, Connection: {connection_id}")

        # Parse body
        if event.get('body'):
            if event.get('isBase64Encoded'):
                body = base64.b64decode(event['body'])
            else:
                body = event['body']

            # Try to parse as JSON
            try:
                data = json.loads(body) if isinstance(body, (str, bytes)) else body
            except:
                data = {'audioData': body}  # Raw audio data
        else:
            data = {}

        action = data.get('action', 'speech')

        # Handle speech-to-speech
        if action == 'speech' or route_key == 'speech':
            audio_data = data.get('audioData', data.get('audio', ''))
            customer_id = data.get('customerId', 'CUST-010000')
            session_id = data.get('sessionId', connection_id)

            if not audio_data:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No audio data provided'})
                }

            # Process speech-to-speech
            result = process_speech_to_speech(audio_data, customer_id, session_id)

            # Send response back through WebSocket
            apigw_management = boto3.client(
                'apigatewaymanagementapi',
                endpoint_url=f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
            )

            # Send transcription first
            apigw_management.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    'type': 'transcription',
                    'text': result['transcription'],
                    'agent': result['agent']
                }).encode('utf-8')
            )

            # Send audio response
            apigw_management.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    'type': 'audio_response',
                    'audioData': result['response_audio'],
                    'text': result['response_text'],
                    'agent': result['agent']
                }).encode('utf-8')
            )

            return {'statusCode': 200, 'body': 'Speech processed'}

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }

    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# For local testing
if __name__ == '__main__':
    # Test with sample data
    test_event = {
        'requestContext': {
            'connectionId': 'test-connection',
            'domainName': 'test.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod',
            'routeKey': 'speech'
        },
        'body': json.dumps({
            'action': 'speech',
            'audioData': 'base64_audio_data_here',
            'customerId': 'CUST-010000'
        })
    }

    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
