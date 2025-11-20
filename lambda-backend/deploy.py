"""
Deploy Lambda backend for UTurn Credit Card agents
"""

import boto3
import json
import zipfile
import io
import time
import os

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name='us-east-1')
iam = boto3.client('iam', region_name='us-east-1')
apigateway = boto3.client('apigatewayv2', region_name='us-east-1')

# Load deployment config
with open('/home/user/UTurnCreditAgent/deployment_config.json', 'r') as f:
    deploy_config = json.load(f)

LAMBDA_FUNCTION_NAME = 'UTurnAgentHandler'
LAMBDA_ROLE_NAME = 'UTurnAgentHandlerRole'

def create_lambda_role():
    """
    Create IAM role for Lambda function
    """
    print("Creating Lambda execution role...")

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        role = iam.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Execution role for UTurn Agent Handler Lambda'
        )
        role_arn = role['Role']['Arn']
        print(f"  ✓ Created role: {role_arn}")

    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=LAMBDA_ROLE_NAME)
        role_arn = role['Role']['Arn']
        print(f"  ℹ Using existing role: {role_arn}")

    # Attach policies
    policies = [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws:iam::aws:policy/AmazonBedrockFullAccess'  # For agent and KB access
    ]

    for policy_arn in policies:
        try:
            iam.attach_role_policy(RoleName=LAMBDA_ROLE_NAME, PolicyArn=policy_arn)
            print(f"  ✓ Attached policy: {policy_arn}")
        except Exception as e:
            if 'already attached' not in str(e).lower():
                print(f"  Warning: {e}")

    return role_arn


def create_deployment_package():
    """
    Create Lambda deployment package (zip file)
    """
    print("\nCreating deployment package...")

    # Create zip file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add Lambda handler
        zip_file.write(
            '/home/user/UTurnCreditAgent/lambda-backend/agent_handler.py',
            'agent_handler.py'
        )

    zip_buffer.seek(0)
    print("  ✓ Created deployment package")

    return zip_buffer.read()


def deploy_lambda(role_arn, deployment_package):
    """
    Deploy or update Lambda function
    """
    print("\nDeploying Lambda function...")

    # Environment variables
    env_vars = {
        'AUTH_AGENT_ARN': deploy_config['agents']['authorization']['arn'],
        'ACCOUNT_AGENT_ARN': deploy_config['agents']['account']['arn'],
        'SALES_AGENT_ARN': deploy_config['agents']['sales']['arn'],
        'CUSTOMER_KB_ID': deploy_config['knowledge_bases']['customer_account']['id'],
        'SALES_KB_ID': deploy_config['knowledge_bases']['sales_product']['id']
    }

    try:
        # Create function
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime='python3.11',
            Role=role_arn,
            Handler='agent_handler.lambda_handler',
            Code={'ZipFile': deployment_package},
            Timeout=60,
            MemorySize=512,
            Environment={'Variables': env_vars},
            Description='Handler for UTurn Credit Card service agents'
        )

        function_arn = response['FunctionArn']
        print(f"  ✓ Created Lambda function: {function_arn}")

    except lambda_client.exceptions.ResourceConflictException:
        # Update existing function
        response = lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=deployment_package
        )

        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime='python3.11',
            Role=role_arn,
            Handler='agent_handler.lambda_handler',
            Timeout=60,
            MemorySize=512,
            Environment={'Variables': env_vars}
        )

        function_arn = response['FunctionArn']
        print(f"  ✓ Updated Lambda function: {function_arn}")

    # Wait for function to be active
    print("  Waiting for function to be active...")
    waiter = lambda_client.get_waiter('function_active_v2')
    waiter.wait(FunctionName=LAMBDA_FUNCTION_NAME)
    print("  ✓ Function is active")

    return function_arn


def create_api_gateway(function_arn):
    """
    Create HTTP API Gateway
    """
    print("\nCreating API Gateway...")

    # Create HTTP API
    try:
        api_response = apigateway.create_api(
            Name='UTurnAgentAPI',
            ProtocolType='HTTP',
            Description='API for UTurn Credit Card service agents',
            CorsConfiguration={
                'AllowOrigins': ['*'],
                'AllowMethods': ['POST', 'OPTIONS'],
                'AllowHeaders': ['Content-Type', 'Authorization']
            }
        )
        api_id = api_response['ApiId']
        api_endpoint = api_response['ApiEndpoint']
        print(f"  ✓ Created API: {api_id}")

    except Exception as e:
        if 'ConflictException' in str(e):
            # Find existing API
            apis = apigateway.get_apis()
            for api in apis['Items']:
                if api['Name'] == 'UTurnAgentAPI':
                    api_id = api['ApiId']
                    api_endpoint = api['ApiEndpoint']
                    print(f"  ℹ Using existing API: {api_id}")
                    break
        else:
            raise

    # Create Lambda integration
    try:
        integration_response = apigateway.create_integration(
            ApiId=api_id,
            IntegrationType='AWS_PROXY',
            IntegrationUri=function_arn,
            PayloadFormatVersion='2.0'
        )
        integration_id = integration_response['IntegrationId']
        print(f"  ✓ Created integration: {integration_id}")

    except Exception as e:
        print(f"  Note: {e}")
        # Get existing integration
        integrations = apigateway.get_integrations(ApiId=api_id)
        if integrations['Items']:
            integration_id = integrations['Items'][0]['IntegrationId']

    # Create route
    try:
        route_response = apigateway.create_route(
            ApiId=api_id,
            RouteKey='POST /invoke',
            Target=f'integrations/{integration_id}'
        )
        print(f"  ✓ Created route: POST /invoke")

    except Exception as e:
        print(f"  Note: {e}")

    # Create deployment and stage
    try:
        apigateway.create_stage(
            ApiId=api_id,
            StageName='prod',
            AutoDeploy=True
        )
        print(f"  ✓ Created stage: prod")

    except Exception as e:
        print(f"  Note: {e}")

    # Add Lambda permission for API Gateway
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId='apigateway-invoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:us-east-1:269610887017:{api_id}/*/*'
        )
        print("  ✓ Added Lambda permission for API Gateway")

    except lambda_client.exceptions.ResourceConflictException:
        print("  ℹ Lambda permission already exists")

    full_endpoint = f"{api_endpoint}/prod/invoke"
    return api_id, full_endpoint


def main():
    """
    Main deployment function
    """
    print("=" * 80)
    print("Deploying UTurn Agent Handler Lambda Backend")
    print("=" * 80)

    # Step 1: Create Lambda role
    role_arn = create_lambda_role()

    # Wait for IAM propagation
    print("\nWaiting 10 seconds for IAM propagation...")
    time.sleep(10)

    # Step 2: Create deployment package
    deployment_package = create_deployment_package()

    # Step 3: Deploy Lambda
    function_arn = deploy_lambda(role_arn, deployment_package)

    # Step 4: Create API Gateway
    api_id, api_endpoint = create_api_gateway(function_arn)

    # Step 5: Update deployment config
    print("\nUpdating deployment config...")
    deploy_config['lambda_backend'] = {
        'function_name': LAMBDA_FUNCTION_NAME,
        'function_arn': function_arn,
        'role_arn': role_arn,
        'api_id': api_id,
        'api_endpoint': api_endpoint
    }

    with open('/home/user/UTurnCreditAgent/deployment_config.json', 'w') as f:
        json.dump(deploy_config, f, indent=2)

    print("  ✓ Updated deployment config")

    # Summary
    print("\n" + "=" * 80)
    print("✓ DEPLOYMENT COMPLETE!")
    print("=" * 80)
    print(f"\nLambda Function: {LAMBDA_FUNCTION_NAME}")
    print(f"Function ARN: {function_arn}")
    print(f"\nAPI Gateway Endpoint: {api_endpoint}")
    print("\nTest with:")
    print(f"""
curl -X POST {api_endpoint} \\
  -H "Content-Type: application/json" \\
  -d '{{"message": "What is my balance?", "customer_id": "CUST-010000"}}'
""")


if __name__ == '__main__':
    main()
