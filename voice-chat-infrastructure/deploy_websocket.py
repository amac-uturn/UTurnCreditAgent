"""
Deploy API Gateway WebSocket for Nova Sonic voice chat
"""

import boto3
import json
import time

# Initialize clients
apigatewayv2 = boto3.client('apigatewayv2', region_name='us-east-1')
iam = boto3.client('iam', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')

# Load deployment config
with open('/home/user/UTurnCreditAgent/deployment_config.json', 'r') as f:
    deploy_config = json.load(f)

ACCOUNT_ID = '269610887017'
REGION = 'us-east-1'


def create_websocket_api():
    """
    Create WebSocket API Gateway
    """
    print("\n" + "="*80)
    print("Creating WebSocket API")
    print("="*80)

    try:
        response = apigatewayv2.create_api(
            Name='UTurnVoiceChatWebSocket',
            ProtocolType='WEBSOCKET',
            RouteSelectionExpression='$request.body.action',
            Description='WebSocket API for UTurn Nova Sonic voice chat'
        )

        api_id = response['ApiId']
        api_endpoint = response['ApiEndpoint']

        print(f"  ✓ Created WebSocket API: {api_id}")
        print(f"  ✓ API Endpoint: {api_endpoint}")

        return api_id, api_endpoint

    except Exception as e:
        # Check if exists
        apis = apigatewayv2.get_apis()
        for api in apis['Items']:
            if api['Name'] == 'UTurnVoiceChatWebSocket':
                api_id = api['ApiId']
                api_endpoint = api['ApiEndpoint']
                print(f"  ℹ Using existing API: {api_id}")
                return api_id, api_endpoint

        raise e


def create_connection_lambda(role_arn):
    """
    Create Lambda function for WebSocket connection handling
    """
    print("\n" + "="*80)
    print("Creating Connection Handler Lambda")
    print("="*80)

    function_name = 'UTurnVoiceConnectionHandler'

    # Lambda code
    lambda_code = """
import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sessions_table = dynamodb.Table('UTurnVoiceSessions')

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    route_key = event['requestContext']['routeKey']

    print(f"Route: {route_key}, Connection: {connection_id}")

    if route_key == '$connect':
        # Store connection
        query_params = event.get('queryStringParameters', {}) or {}
        customer_id = query_params.get('customerId', 'CUST-010000')

        sessions_table.put_item(
            Item={
                'sessionId': connection_id,
                'customerId': customer_id,
                'connectionId': connection_id,
                'createdAt': int(datetime.now().timestamp()),
                'status': 'connected'
            }
        )

        return {'statusCode': 200, 'body': 'Connected'}

    elif route_key == '$disconnect':
        # Clean up connection
        try:
            sessions_table.update_item(
                Key={'sessionId': connection_id},
                UpdateExpression='SET #status = :status, disconnectedAt = :time',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'disconnected',
                    ':time': int(datetime.now().timestamp())
                }
            )
        except Exception as e:
            print(f"Error updating session: {e}")

        return {'statusCode': 200, 'body': 'Disconnected'}

    elif route_key == '$default':
        # Handle default messages
        return {'statusCode': 200, 'body': 'Message received'}

    return {'statusCode': 400, 'body': 'Invalid route'}
"""

    # Create deployment package
    import zipfile
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', lambda_code)

    zip_buffer.seek(0)
    deployment_package = zip_buffer.read()

    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': deployment_package},
            Timeout=30,
            MemorySize=256,
            Environment={
                'Variables': {
                    'SESSIONS_TABLE': 'UTurnVoiceSessions'
                }
            }
        )

        function_arn = response['FunctionArn']
        print(f"  ✓ Created Lambda: {function_name}")

    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=deployment_package
        )
        function_arn = response['FunctionArn']
        print(f"  ℹ Updated Lambda: {function_name}")

    # Wait for function to be active
    waiter = lambda_client.get_waiter('function_active_v2')
    waiter.wait(FunctionName=function_name)

    return function_arn


def create_voice_handler_lambda(role_arn):
    """
    Create Lambda function for voice/audio handling
    """
    print("\n" + "="*80)
    print("Creating Voice Handler Lambda")
    print("="*80)

    function_name = 'UTurnVoiceMessageHandler'

    # Lambda code for handling voice messages
    lambda_code = """
import json
import boto3
import os
import base64
from datetime import datetime
import uuid

dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

messages_table = dynamodb.Table('UTurnVoiceMessages')
sessions_table = dynamodb.Table('UTurnVoiceSessions')

# Agent ARNs from environment
AGENT_ARNS = {
    'authorization': os.environ.get('AUTH_AGENT_ARN'),
    'account': os.environ.get('ACCOUNT_AGENT_ARN'),
    'sales': os.environ.get('SALES_AGENT_ARN')
}

KB_IDS = {
    'authorization': os.environ.get('CUSTOMER_KB_ID'),
    'account': os.environ.get('CUSTOMER_KB_ID'),
    'sales': os.environ.get('SALES_KB_ID')
}


def route_to_agent(text):
    \"\"\"Route message to appropriate agent\"\"\"
    text_lower = text.lower()

    auth_keywords = ['pin', 'security', 'fraud', 'lock', 'unlock', 'stolen']
    account_keywords = ['balance', 'transaction', 'payment', 'statement']
    sales_keywords = ['apply', 'new card', 'upgrade', 'offer', 'product']

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
        return 'account'


def query_kb(kb_id, query):
    \"\"\"Query knowledge base\"\"\"
    try:
        response = bedrock_runtime.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {'numberOfResults': 3}
            }
        )

        results = []
        for result in response.get('retrievalResults', []):
            results.append(result.get('content', {}).get('text', ''))

        return '\\n'.join(results[:2])  # Top 2 results
    except Exception as e:
        print(f"KB query error: {e}")
        return ""


def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']

    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'message')

        if action == 'message':
            # Handle text message
            message_text = body.get('message', body.get('text', ''))
            customer_id = body.get('customerId', 'CUST-010000')

            if not message_text:
                return {'statusCode': 400, 'body': 'Missing message'}

            # Route to agent
            agent_type = body.get('agent_type') or route_to_agent(message_text)

            # Query KB
            kb_context = ''
            if agent_type in KB_IDS and KB_IDS[agent_type]:
                kb_context = query_kb(KB_IDS[agent_type], message_text)

            # Generate response (simplified - would call actual agent here)
            response_text = f"[{agent_type.upper()}] Processing: {message_text[:50]}..."
            if kb_context:
                response_text += f"\\n\\nContext: {kb_context[:100]}..."

            # Store message
            message_id = str(uuid.uuid4())
            timestamp = int(datetime.now().timestamp())

            messages_table.put_item(
                Item={
                    'sessionId': connection_id,
                    'messageId': message_id,
                    'timestamp': timestamp,
                    'role': 'user',
                    'content': message_text,
                    'agent': agent_type
                }
            )

            # Store response
            response_id = str(uuid.uuid4())
            messages_table.put_item(
                Item={
                    'sessionId': connection_id,
                    'messageId': response_id,
                    'timestamp': timestamp + 1,
                    'role': 'assistant',
                    'content': response_text,
                    'agent': agent_type
                }
            )

            # Send response back through WebSocket
            apigw_management = boto3.client(
                'apigatewaymanagementapi',
                endpoint_url=f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
            )

            apigw_management.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    'type': 'message',
                    'agent': agent_type,
                    'content': response_text,
                    'timestamp': timestamp + 1
                }).encode('utf-8')
            )

            return {'statusCode': 200, 'body': 'Message processed'}

        else:
            return {'statusCode': 400, 'body': 'Unknown action'}

    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': str(e)}
"""

    # Create deployment package
    import zipfile
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', lambda_code)

    zip_buffer.seek(0)
    deployment_package = zip_buffer.read()

    # Environment variables
    env_vars = {
        'SESSIONS_TABLE': 'UTurnVoiceSessions',
        'MESSAGES_TABLE': 'UTurnVoiceMessages',
        'AUTH_AGENT_ARN': deploy_config['agents']['authorization']['arn'],
        'ACCOUNT_AGENT_ARN': deploy_config['agents']['account']['arn'],
        'SALES_AGENT_ARN': deploy_config['agents']['sales']['arn'],
        'CUSTOMER_KB_ID': deploy_config['knowledge_bases']['customer_account']['id'],
        'SALES_KB_ID': deploy_config['knowledge_bases']['sales_product']['id']
    }

    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': deployment_package},
            Timeout=60,
            MemorySize=512,
            Environment={'Variables': env_vars}
        )

        function_arn = response['FunctionArn']
        print(f"  ✓ Created Lambda: {function_name}")

    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=deployment_package
        )

        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': env_vars}
        )

        function_arn = response['FunctionArn']
        print(f"  ℹ Updated Lambda: {function_name}")

    # Wait for function to be active
    waiter = lambda_client.get_waiter('function_active_v2')
    waiter.wait(FunctionName=function_name)

    return function_arn


def setup_websocket_routes(api_id, connection_lambda_arn, message_lambda_arn):
    """
    Setup WebSocket routes
    """
    print("\n" + "="*80)
    print("Setting Up WebSocket Routes")
    print("="*80)

    # Create integrations
    print("\n1. Creating integrations...")

    # Connection integration
    conn_integration = apigatewayv2.create_integration(
        ApiId=api_id,
        IntegrationType='AWS_PROXY',
        IntegrationUri=f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{connection_lambda_arn}/invocations',
        IntegrationMethod='POST',
        PayloadFormatVersion='1.0'
    )
    conn_integration_id = conn_integration['IntegrationId']
    print(f"  ✓ Connection integration: {conn_integration_id}")

    # Message integration
    msg_integration = apigatewayv2.create_integration(
        ApiId=api_id,
        IntegrationType='AWS_PROXY',
        IntegrationUri=f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{message_lambda_arn}/invocations',
        IntegrationMethod='POST',
        PayloadFormatVersion='1.0'
    )
    msg_integration_id = msg_integration['IntegrationId']
    print(f"  ✓ Message integration: {msg_integration_id}")

    # Create routes
    print("\n2. Creating routes...")

    routes = [
        ('$connect', conn_integration_id),
        ('$disconnect', conn_integration_id),
        ('$default', msg_integration_id),
        ('message', msg_integration_id)
    ]

    for route_key, integration_id in routes:
        try:
            apigatewayv2.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f'integrations/{integration_id}'
            )
            print(f"  ✓ Route: {route_key}")
        except Exception as e:
            print(f"  Note: {route_key} - {e}")

    # Add Lambda permissions
    print("\n3. Adding Lambda permissions...")

    for function_arn, function_name in [(connection_lambda_arn, 'UTurnVoiceConnectionHandler'),
                                         (message_lambda_arn, 'UTurnVoiceMessageHandler')]:
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=f'apigateway-websocket-{api_id}',
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f'arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*'
            )
            print(f"  ✓ Permission for {function_name}")
        except lambda_client.exceptions.ResourceConflictException:
            print(f"  ℹ Permission already exists for {function_name}")


def deploy_websocket_stage(api_id):
    """
    Deploy WebSocket API stage
    """
    print("\n" + "="*80)
    print("Deploying WebSocket Stage")
    print("="*80)

    try:
        stage_response = apigatewayv2.create_stage(
            ApiId=api_id,
            StageName='prod',
            AutoDeploy=True,
            Description='Production stage for UTurn voice chat'
        )
        print("  ✓ Created stage: prod")

    except Exception as e:
        print(f"  Note: {e}")

    # Get WebSocket URL
    api_details = apigatewayv2.get_api(ApiId=api_id)
    websocket_url = f"wss://{api_id}.execute-api.{REGION}.amazonaws.com/prod"

    print(f"  ✓ WebSocket URL: {websocket_url}")

    return websocket_url


def main():
    """
    Main deployment
    """
    print("\n" + "="*80)
    print("DEPLOYING WEBSOCKET API FOR VOICE CHAT")
    print("="*80)

    # Get Lambda role from config
    lambda_role_arn = deploy_config['voice_chat_infrastructure']['lambda_role_arn']

    # Create WebSocket API
    api_id, api_endpoint = create_websocket_api()

    # Create Lambda functions
    connection_lambda_arn = create_connection_lambda(lambda_role_arn)
    message_lambda_arn = create_voice_handler_lambda(lambda_role_arn)

    # Setup routes
    setup_websocket_routes(api_id, connection_lambda_arn, message_lambda_arn)

    # Deploy stage
    websocket_url = deploy_websocket_stage(api_id)

    # Update config
    print("\n" + "="*80)
    print("Updating Configuration")
    print("="*80)

    if 'voice_chat_infrastructure' not in deploy_config:
        deploy_config['voice_chat_infrastructure'] = {}

    deploy_config['voice_chat_infrastructure']['websocket'] = {
        'api_id': api_id,
        'websocket_url': websocket_url,
        'connection_lambda_arn': connection_lambda_arn,
        'message_lambda_arn': message_lambda_arn
    }

    with open('/home/user/UTurnCreditAgent/deployment_config.json', 'w') as f:
        json.dump(deploy_config, f, indent=2)

    print("  ✓ Updated deployment_config.json")

    # Summary
    print("\n" + "="*80)
    print("✓ WEBSOCKET API DEPLOYED!")
    print("="*80)

    print(f"\nWebSocket URL: {websocket_url}")
    print(f"\nTest with:")
    print(f"""
wscat -c "{websocket_url}?customerId=CUST-010000"

# Then send:
{{"action": "message", "message": "What is my balance?", "customerId": "CUST-010000"}}
""")


if __name__ == '__main__':
    main()
