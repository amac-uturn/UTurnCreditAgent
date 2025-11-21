"""
Deploy Nova Sonic Speech-to-Speech Lambda function
"""

import boto3
import json
import zipfile
import io
import time

# Initialize clients
lambda_client = boto3.client('lambda', region_name='us-east-1')
apigatewayv2 = boto3.client('apigatewayv2', region_name='us-east-1')

# Load deployment config
with open('/home/user/UTurnCreditAgent/deployment_config.json', 'r') as f:
    deploy_config = json.load(f)

FUNCTION_NAME = 'UTurnNovaSonicHandler'
REGION = 'us-east-1'
ACCOUNT_ID = '269610887017'


def create_deployment_package():
    """Create Lambda deployment package"""
    print("\n" + "="*80)
    print("Creating Deployment Package")
    print("="*80)

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write(
            '/home/user/UTurnCreditAgent/voice-chat-infrastructure/nova_sonic_handler.py',
            'lambda_function.py'
        )

    zip_buffer.seek(0)
    print("  ✓ Created deployment package")

    return zip_buffer.read()


def deploy_lambda():
    """Deploy or update Lambda function"""
    print("\n" + "="*80)
    print("Deploying Nova Sonic Lambda Function")
    print("="*80)

    # Get Lambda role
    lambda_role_arn = deploy_config['voice_chat_infrastructure']['lambda_role_arn']

    # Environment variables
    env_vars = {
        'AUTH_AGENT_ARN': deploy_config['agents']['authorization']['arn'],
        'ACCOUNT_AGENT_ARN': deploy_config['agents']['account']['arn'],
        'SALES_AGENT_ARN': deploy_config['agents']['sales']['arn'],
        'CUSTOMER_KB_ID': deploy_config['knowledge_bases']['customer_account']['id'],
        'SALES_KB_ID': deploy_config['knowledge_bases']['sales_product']['id']
    }

    # Create deployment package
    deployment_package = create_deployment_package()

    try:
        response = lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime='python3.11',
            Role=lambda_role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': deployment_package},
            Timeout=300,  # 5 minutes for streaming
            MemorySize=1024,  # More memory for audio processing
            Environment={'Variables': env_vars},
            Description='Nova Sonic speech-to-speech handler for UTurn agents'
        )

        function_arn = response['FunctionArn']
        print(f"  ✓ Created Lambda function: {FUNCTION_NAME}")

    except lambda_client.exceptions.ResourceConflictException:
        # Update existing function
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=deployment_package
        )

        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Runtime='python3.11',
            Role=lambda_role_arn,
            Handler='lambda_function.lambda_handler',
            Timeout=300,
            MemorySize=1024,
            Environment={'Variables': env_vars}
        )

        function_arn = response['FunctionArn']
        print(f"  ✓ Updated Lambda function: {FUNCTION_NAME}")

    # Wait for function to be active
    print("  Waiting for function to be active...")
    waiter = lambda_client.get_waiter('function_active_v2')
    waiter.wait(FunctionName=FUNCTION_NAME)
    print("  ✓ Function is active")

    return function_arn


def add_websocket_route(function_arn):
    """Add speech route to WebSocket API"""
    print("\n" + "="*80)
    print("Adding Speech Route to WebSocket API")
    print("="*80)

    api_id = deploy_config['voice_chat_infrastructure']['websocket']['api_id']

    # Create integration for speech route
    try:
        integration_response = apigatewayv2.create_integration(
            ApiId=api_id,
            IntegrationType='AWS_PROXY',
            IntegrationUri=f'arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{function_arn}/invocations',
            IntegrationMethod='POST',
            PayloadFormatVersion='1.0'
        )
        integration_id = integration_response['IntegrationId']
        print(f"  ✓ Created integration: {integration_id}")

    except Exception as e:
        # Integration might already exist
        print(f"  Note: {e}")
        # Get existing integrations
        integrations = apigatewayv2.get_integrations(ApiId=api_id)
        for integration in integrations['Items']:
            if FUNCTION_NAME in integration.get('IntegrationUri', ''):
                integration_id = integration['IntegrationId']
                print(f"  ℹ Using existing integration: {integration_id}")
                break
        else:
            raise

    # Create speech route
    try:
        apigatewayv2.create_route(
            ApiId=api_id,
            RouteKey='speech',
            Target=f'integrations/{integration_id}'
        )
        print("  ✓ Created route: speech")

    except Exception as e:
        print(f"  Note: speech route - {e}")

    # Add Lambda permission
    try:
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId=f'apigateway-websocket-speech-{api_id}',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*'
        )
        print("  ✓ Added Lambda permission for WebSocket API")

    except lambda_client.exceptions.ResourceConflictException:
        print("  ℹ Lambda permission already exists")


def main():
    """Main deployment"""
    print("\n" + "="*80)
    print("DEPLOYING NOVA SONIC SPEECH-TO-SPEECH SYSTEM")
    print("="*80)

    # Deploy Lambda
    function_arn = deploy_lambda()

    # Add to WebSocket API
    add_websocket_route(function_arn)

    # Update deployment config
    print("\n" + "="*80)
    print("Updating Configuration")
    print("="*80)

    deploy_config['voice_chat_infrastructure']['nova_sonic'] = {
        'function_name': FUNCTION_NAME,
        'function_arn': function_arn,
        'deployed_at': __import__('datetime').datetime.now().isoformat()
    }

    with open('/home/user/UTurnCreditAgent/deployment_config.json', 'w') as f:
        json.dump(deploy_config, f, indent=2)

    print("  ✓ Updated deployment_config.json")

    # Summary
    print("\n" + "="*80)
    print("✓ NOVA SONIC DEPLOYMENT COMPLETE!")
    print("="*80)

    websocket_url = deploy_config['voice_chat_infrastructure']['websocket']['websocket_url']

    print(f"\nNova Sonic Function: {FUNCTION_NAME}")
    print(f"Function ARN: {function_arn}")
    print(f"\nWebSocket URL: {websocket_url}")
    print("\nSpeech-to-Speech Flow:")
    print("  1. User speaks → Audio captured")
    print("  2. Audio sent via WebSocket → Nova Sonic")
    print("  3. Nova Sonic transcribes → Text")
    print("  4. Text → Agent Core (with KB context)")
    print("  5. Agent response → Text")
    print("  6. Text → Nova Sonic synthesizes → Audio")
    print("  7. Audio streamed back → User hears response")
    print("\nNext: Update frontend to stream audio via WebSocket!")


if __name__ == '__main__':
    main()
