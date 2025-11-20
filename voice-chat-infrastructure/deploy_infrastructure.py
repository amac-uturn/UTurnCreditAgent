"""
Deploy complete infrastructure for Nova Sonic voice chat system
- DynamoDB tables for sessions and messages
- AppSync EventAPI for WebSocket
- Lambda function for Nova Sonic streaming
"""

import boto3
import json
import time
import zipfile
import io

# Initialize AWS clients
dynamodb = boto3.client('dynamodb', region_name='us-east-1')
appsync = boto3.client('appsync', region_name='us-east-1')
iam = boto3.client('iam', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')
logs = boto3.client('logs', region_name='us-east-1')

# Configuration
REGION = 'us-east-1'
ACCOUNT_ID = '269610887017'

# Load deployment config
with open('/home/user/UTurnCreditAgent/deployment_config.json', 'r') as f:
    deploy_config = json.load(f)


def create_dynamodb_tables():
    """
    Create DynamoDB tables for sessions and messages
    """
    print("\n" + "="*80)
    print("Creating DynamoDB Tables")
    print("="*80)

    tables = []

    # Sessions table
    print("\n1. Creating Sessions table...")
    try:
        response = dynamodb.create_table(
            TableName='UTurnVoiceSessions',
            KeySchema=[
                {'AttributeName': 'sessionId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'sessionId', 'AttributeType': 'S'},
                {'AttributeName': 'customerId', 'AttributeType': 'S'},
                {'AttributeName': 'createdAt', 'AttributeType': 'N'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'CustomerIndex',
                    'KeySchema': [
                        {'AttributeName': 'customerId', 'KeyType': 'HASH'},
                        {'AttributeName': 'createdAt', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"  ✓ Created Sessions table")
        tables.append('UTurnVoiceSessions')

    except dynamodb.exceptions.ResourceInUseException:
        print(f"  ℹ Sessions table already exists")
        tables.append('UTurnVoiceSessions')

    # Messages table
    print("\n2. Creating Messages table...")
    try:
        response = dynamodb.create_table(
            TableName='UTurnVoiceMessages',
            KeySchema=[
                {'AttributeName': 'sessionId', 'KeyType': 'HASH'},
                {'AttributeName': 'messageId', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'sessionId', 'AttributeType': 'S'},
                {'AttributeName': 'messageId', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ],
            LocalSecondaryIndexes=[
                {
                    'IndexName': 'TimestampIndex',
                    'KeySchema': [
                        {'AttributeName': 'sessionId', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"  ✓ Created Messages table")
        tables.append('UTurnVoiceMessages')

    except dynamodb.exceptions.ResourceInUseException:
        print(f"  ℹ Messages table already exists")
        tables.append('UTurnVoiceMessages')

    # Wait for tables to be active
    if tables:
        print("\n3. Waiting for tables to be active...")
        for table_name in tables:
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            print(f"  ✓ {table_name} is active")

    return tables


def create_appsync_role():
    """
    Create IAM role for AppSync
    """
    print("\n" + "="*80)
    print("Creating AppSync IAM Role")
    print("="*80)

    role_name = 'UTurnAppSyncServiceRole'

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "appsync.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Service role for UTurn AppSync EventAPI'
        )
        role_arn = role['Role']['Arn']
        print(f"  ✓ Created role: {role_arn}")

    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"  ℹ Using existing role: {role_arn}")

    # Attach CloudWatch Logs policy
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            }
        ]
    }

    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='CloudWatchLogsPolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        print("  ✓ Attached CloudWatch Logs policy")
    except Exception as e:
        print(f"  Note: {e}")

    return role_arn


def create_appsync_api(role_arn):
    """
    Create AppSync EventAPI
    """
    print("\n" + "="*80)
    print("Creating AppSync EventAPI")
    print("="*80)

    api_name = 'UTurnVoiceChatAPI'

    # Check if API already exists
    try:
        apis = appsync.list_graph_ql_apis(apiType='EVENT')
        for api in apis.get('graphqlApis', []):
            if api['name'] == api_name:
                print(f"  ℹ Using existing API: {api['apiId']}")
                return api['apiId'], api['uris']['REALTIME']
    except Exception as e:
        print(f"  Note: {e}")

    # Create new EventAPI
    try:
        response = appsync.create_graph_ql_api(
            name=api_name,
            authenticationType='API_KEY',
            apiType='EVENT',
            eventConfig={
                'authProviders': [
                    {'authType': 'API_KEY'}
                ],
                'connectionAuthModes': [
                    {'authType': 'API_KEY'}
                ],
                'defaultPublishAuthModes': [
                    {'authType': 'API_KEY'}
                ],
                'defaultSubscribeAuthModes': [
                    {'authType': 'API_KEY'}
                ]
            },
            logConfig={
                'fieldLogLevel': 'ALL',
                'cloudWatchLogsRoleArn': role_arn
            }
        )

        api_id = response['graphqlApi']['apiId']
        websocket_url = response['graphqlApi']['uris']['REALTIME']

        print(f"  ✓ Created EventAPI: {api_id}")
        print(f"  ✓ WebSocket URL: {websocket_url}")

        # Create API key
        key_response = appsync.create_api_key(
            apiId=api_id,
            description='Default API key for UTurn Voice Chat',
            expires=int(time.time()) + (365 * 24 * 60 * 60)  # 1 year
        )

        api_key = key_response['apiKey']['id']
        print(f"  ✓ Created API key: {api_key[:10]}...")

        return api_id, websocket_url, api_key

    except Exception as e:
        print(f"  Error creating AppSync API: {e}")
        raise


def create_lambda_role():
    """
    Create IAM role for Lambda functions
    """
    print("\n" + "="*80)
    print("Creating Lambda IAM Role")
    print("="*80)

    role_name = 'UTurnVoiceHandlerRole'

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
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Execution role for UTurn Voice Handler Lambda'
        )
        role_arn = role['Role']['Arn']
        print(f"  ✓ Created role: {role_arn}")

    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)
        role_arn = role['Role']['Arn']
        print(f"  ℹ Using existing role: {role_arn}")

    # Attach policies
    policies = [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws:iam::aws:policy/AmazonBedrockFullAccess'
    ]

    for policy_arn in policies:
        try:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
            print(f"  ✓ Attached policy: {policy_arn.split('/')[-1]}")
        except Exception as e:
            if 'already attached' not in str(e).lower():
                print(f"  Note: {e}")

    # Add inline policy for DynamoDB and AppSync
    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": [
                    f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/UTurnVoiceSessions",
                    f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/UTurnVoiceSessions/index/*",
                    f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/UTurnVoiceMessages",
                    f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/UTurnVoiceMessages/index/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "appsync:GraphQL"
                ],
                "Resource": "*"
            }
        ]
    }

    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='DynamoDBAppSyncPolicy',
            PolicyDocument=json.dumps(inline_policy)
        )
        print("  ✓ Added DynamoDB and AppSync permissions")
    except Exception as e:
        print(f"  Note: {e}")

    return role_arn


def main():
    """
    Main deployment function
    """
    print("\n" + "="*80)
    print("DEPLOYING NOVA SONIC VOICE CHAT INFRASTRUCTURE")
    print("="*80)

    results = {}

    # Step 1: Create DynamoDB tables
    tables = create_dynamodb_tables()
    results['dynamodb_tables'] = tables

    # Step 2: Create AppSync role
    appsync_role_arn = create_appsync_role()
    results['appsync_role_arn'] = appsync_role_arn

    print("\nWaiting 10 seconds for IAM propagation...")
    time.sleep(10)

    # Step 3: Create AppSync EventAPI
    try:
        api_result = create_appsync_api(appsync_role_arn)
        if len(api_result) == 3:
            api_id, websocket_url, api_key = api_result
            results['appsync'] = {
                'api_id': api_id,
                'websocket_url': websocket_url,
                'api_key': api_key
            }
        else:
            api_id, websocket_url = api_result
            results['appsync'] = {
                'api_id': api_id,
                'websocket_url': websocket_url
            }
    except Exception as e:
        print(f"Error creating AppSync API: {e}")
        results['appsync'] = {'error': str(e)}

    # Step 4: Create Lambda role
    lambda_role_arn = create_lambda_role()
    results['lambda_role_arn'] = lambda_role_arn

    # Step 5: Update deployment config
    print("\n" + "="*80)
    print("Updating Deployment Configuration")
    print("="*80)

    deploy_config['voice_chat_infrastructure'] = results

    with open('/home/user/UTurnCreditAgent/deployment_config.json', 'w') as f:
        json.dump(deploy_config, f, indent=2)

    print("  ✓ Updated deployment_config.json")

    # Summary
    print("\n" + "="*80)
    print("✓ INFRASTRUCTURE DEPLOYMENT COMPLETE!")
    print("="*80)

    print("\nCreated Resources:")
    print(f"  • DynamoDB Tables: {', '.join(tables)}")
    if 'appsync' in results and 'api_id' in results['appsync']:
        print(f"  • AppSync API ID: {results['appsync']['api_id']}")
        print(f"  • WebSocket URL: {results['appsync']['websocket_url']}")
    print(f"  • Lambda Role: {lambda_role_arn}")

    print("\nNext Steps:")
    print("  1. Deploy Lambda function for voice streaming")
    print("  2. Build and deploy Next.js frontend")
    print("  3. Test end-to-end voice chat")

    return results


if __name__ == '__main__':
    results = main()
