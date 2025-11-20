#!/usr/bin/env python3
"""
Create and configure AWS Bedrock Knowledge Bases for UTurn Credit Card Service

This script creates two knowledge bases:
1. Customer/Account KB - For authorization and account agents
2. Sales/Product KB - For sales agent
"""

import boto3
import json
import time
import sys
from datetime import datetime

# Configuration
REGION = "us-east-1"

# Knowledge Base configurations
KB_CONFIGS = [
    {
        "name": "uturn-customer-account-kb",
        "description": "Customer account data, security info, and policies for Authorization and Account agents",
        "documents": [
            "data/customer_data/customers.json",
            "data/customer_data/knowledge_base_faqs.json",
            "data/customer_data/knowledge_base_policies.json"
        ]
    },
    {
        "name": "uturn-sales-product-kb",
        "description": "Credit card product catalog and offers for Sales agent",
        "documents": [
            "data/product_data/credit_card_products.json"
        ]
    }
]


def create_iam_role_for_kb(role_name: str):
    """Create IAM role for Bedrock Knowledge Base."""
    iam = boto3.client('iam', region_name=REGION)

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for Bedrock Knowledge Base access"
        )

        # Attach necessary policies
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        )

        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AmazonOpenSearchServiceFullAccess"
        )

        print(f"✓ Created IAM role: {role_name}")
        return response['Role']['Arn']

    except iam.exceptions.EntityAlreadyExistsException:
        response = iam.get_role(RoleName=role_name)
        print(f"ℹ IAM role already exists: {role_name}")
        return response['Role']['Arn']


def create_s3_bucket_for_documents(bucket_name: str):
    """Create S3 bucket for knowledge base documents."""
    s3 = boto3.client('s3', region_name=REGION)

    try:
        if REGION == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )

        print(f"✓ Created S3 bucket: {bucket_name}")
        return bucket_name

    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"ℹ S3 bucket already exists: {bucket_name}")
        return bucket_name


def upload_documents_to_s3(bucket_name: str, documents: list):
    """Upload knowledge base documents to S3."""
    s3 = boto3.client('s3', region_name=REGION)

    uploaded_files = []

    for doc_path in documents:
        try:
            with open(doc_path, 'r') as f:
                content = json.load(f)

            # Convert JSON to text format for better KB processing
            if isinstance(content, list):
                text_content = "\n\n".join([json.dumps(item, indent=2) for item in content])
            else:
                text_content = json.dumps(content, indent=2)

            # Upload to S3
            key = f"documents/{doc_path.split('/')[-1]}.txt"
            s3.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=text_content.encode('utf-8'),
                ContentType='text/plain'
            )

            uploaded_files.append(f"s3://{bucket_name}/{key}")
            print(f"  ✓ Uploaded: {doc_path} → s3://{bucket_name}/{key}")

        except FileNotFoundError:
            print(f"  ✗ File not found: {doc_path}")
        except Exception as e:
            print(f"  ✗ Error uploading {doc_path}: {e}")

    return uploaded_files


def create_opensearch_serverless_collection(collection_name: str):
    """Create OpenSearch Serverless collection for vector storage."""
    aoss = boto3.client('opensearchserverless', region_name=REGION)

    try:
        response = aoss.create_collection(
            name=collection_name,
            type='VECTORSEARCH',
            description=f'Vector collection for {collection_name}'
        )

        collection_id = response['createCollectionDetail']['id']
        print(f"✓ Created OpenSearch collection: {collection_name} (ID: {collection_id})")

        # Wait for collection to be active
        print("  Waiting for collection to be active...")
        while True:
            status = aoss.batch_get_collection(names=[collection_name])
            if status['collectionDetails'][0]['status'] == 'ACTIVE':
                break
            time.sleep(5)

        print("  ✓ Collection is active")
        return collection_id

    except aoss.exceptions.ConflictException:
        print(f"ℹ OpenSearch collection already exists: {collection_name}")
        # Get existing collection
        response = aoss.batch_get_collection(names=[collection_name])
        return response['collectionDetails'][0]['id']


def create_knowledge_base(kb_config: dict, role_arn: str, bucket_name: str):
    """Create Bedrock Knowledge Base."""
    bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

    kb_name = kb_config['name']
    description = kb_config['description']

    try:
        # Create the knowledge base
        response = bedrock_agent.create_knowledge_base(
            name=kb_name,
            description=description,
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                'type': 'VECTOR',
                'vectorKnowledgeBaseConfiguration': {
                    'embeddingModelArn': f'arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v1'
                }
            },
            storageConfiguration={
                'type': 'OPENSEARCH_SERVERLESS',
                'opensearchServerlessConfiguration': {
                    'collectionArn': f'arn:aws:aoss:{REGION}:*:collection/*',
                    'vectorIndexName': kb_name.replace('-', '_'),
                    'fieldMapping': {
                        'vectorField': 'vector',
                        'textField': 'text',
                        'metadataField': 'metadata'
                    }
                }
            }
        )

        kb_id = response['knowledgeBase']['knowledgeBaseId']
        print(f"✓ Created Knowledge Base: {kb_name} (ID: {kb_id})")

        # Create data source
        print(f"  Creating data source...")
        ds_response = bedrock_agent.create_data_source(
            knowledgeBaseId=kb_id,
            name=f"{kb_name}-datasource",
            dataSourceConfiguration={
                'type': 'S3',
                's3Configuration': {
                    'bucketArn': f'arn:aws:s3:::{bucket_name}',
                    'inclusionPrefixes': ['documents/']
                }
            }
        )

        ds_id = ds_response['dataSource']['dataSourceId']
        print(f"  ✓ Created data source: {ds_id}")

        # Trigger ingestion
        print(f"  Triggering document ingestion...")
        ingestion_response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id
        )

        print(f"  ✓ Ingestion job started: {ingestion_response['ingestionJob']['ingestionJobId']}")

        return {
            'knowledge_base_id': kb_id,
            'data_source_id': ds_id,
            'name': kb_name
        }

    except Exception as e:
        print(f"✗ Error creating knowledge base: {e}")
        return None


def main():
    print("=" * 70)
    print("  UTurn Knowledge Base Setup")
    print("=" * 70)
    print()

    # Get AWS account ID
    try:
        sts = boto3.client('sts', region_name=REGION)
        account_id = sts.get_caller_identity()['Account']
        print(f"AWS Account: {account_id}")
        print(f"Region: {REGION}")
        print()
    except Exception as e:
        print(f"✗ Error verifying AWS credentials: {e}")
        print("\nPlease ensure AWS credentials are configured correctly.")
        sys.exit(1)

    created_resources = []

    # Create IAM role
    print("[1/5] Creating IAM role...")
    role_name = "UTurnKnowledgeBaseRole"
    role_arn = create_iam_role_for_kb(role_name)
    print()

    # Create S3 bucket
    print("[2/5] Creating S3 bucket...")
    bucket_name = f"uturn-kb-documents-{account_id}"
    create_s3_bucket_for_documents(bucket_name)
    print()

    # Upload documents
    print("[3/5] Uploading documents to S3...")
    all_documents = []
    for kb_config in KB_CONFIGS:
        all_documents.extend(kb_config['documents'])
    uploaded_files = upload_documents_to_s3(bucket_name, all_documents)
    print(f"  Uploaded {len(uploaded_files)} files")
    print()

    # Create knowledge bases
    print("[4/5] Creating Knowledge Bases...")
    for i, kb_config in enumerate(KB_CONFIGS, 1):
        print(f"\n  Knowledge Base {i}/{len(KB_CONFIGS)}: {kb_config['name']}")
        kb_info = create_knowledge_base(kb_config, role_arn, bucket_name)
        if kb_info:
            created_resources.append(kb_info)
    print()

    # Summary
    print("[5/5] Setup Complete!")
    print()
    print("=" * 70)
    print("  Knowledge Base Summary")
    print("=" * 70)
    print()

    for resource in created_resources:
        print(f"Name: {resource['name']}")
        print(f"  KB ID: {resource['knowledge_base_id']}")
        print(f"  Data Source ID: {resource['data_source_id']}")
        print()

    print("Next Steps:")
    print("  1. Wait 5-10 minutes for document ingestion to complete")
    print("  2. Verify knowledge bases in AWS Console:")
    print(f"     https://console.aws.amazon.com/bedrock/home?region={REGION}#/knowledge-bases")
    print("  3. Update agent code to use these knowledge base IDs")
    print("  4. Test queries against knowledge bases")
    print()

    # Save configuration
    config_file = "kb_config.json"
    with open(config_file, 'w') as f:
        json.dump({
            'created_at': datetime.now().isoformat(),
            'region': REGION,
            'account_id': account_id,
            'role_arn': role_arn,
            'bucket_name': bucket_name,
            'knowledge_bases': created_resources
        }, f, indent=2)

    print(f"Configuration saved to: {config_file}")
    print()


if __name__ == "__main__":
    main()
