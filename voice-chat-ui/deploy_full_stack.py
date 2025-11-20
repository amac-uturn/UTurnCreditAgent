"""
Full deployment of voice chat UI to S3 and CloudFront
"""

import boto3
import json
import os
import mimetypes
import time
from datetime import datetime

s3 = boto3.client('s3', region_name='us-east-1')
cloudfront = boto3.client('cloudfront', region_name='us-east-1')

BUCKET_NAME = 'uturn-voice-chat-ui-20251120221511'
BUILD_DIR = '/home/user/UTurnCreditAgent/voice-chat-ui/build'


def upload_to_s3():
    """Upload build files to S3"""
    print("=" * 80)
    print("Uploading to S3")
    print("=" * 80)

    uploaded = 0

    for root, dirs, files in os.walk(BUILD_DIR):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, BUILD_DIR)
            s3_path = relative_path.replace('\\', '/')

            content_type, _ = mimetypes.guess_type(local_path)
            if content_type is None:
                content_type = 'application/octet-stream'

            extra_args = {'ContentType': content_type}

            if '/static/' in s3_path:
                extra_args['CacheControl'] = 'public, max-age=31536000'
            else:
                extra_args['CacheControl'] = 'public, max-age=0, must-revalidate'

            try:
                s3.upload_file(local_path, BUCKET_NAME, s3_path, ExtraArgs=extra_args)
                print(f"  ✓ {s3_path}")
                uploaded += 1
            except Exception as e:
                print(f"  ✗ {s3_path}: {e}")

    print(f"\n✓ Uploaded {uploaded} files")
    return uploaded


def create_cloudfront_distribution():
    """Create CloudFront distribution"""
    print("\n" + "=" * 80)
    print("Creating CloudFront Distribution")
    print("=" * 80)

    oac_response = cloudfront.create_origin_access_control(
        OriginAccessControlConfig={
            'Name': f'{BUCKET_NAME}-oac',
            'Description': 'OAC for UTurn Voice Chat UI',
            'SigningProtocol': 'sigv4',
            'SigningBehavior': 'always',
            'OriginAccessControlOriginType': 's3'
        }
    )
    oac_id = oac_response['OriginAccessControl']['Id']
    print(f"  ✓ Created OAC: {oac_id}")

    distribution_config = {
        'CallerReference': str(int(time.time())),
        'Comment': 'UTurn Voice Chat UI Distribution',
        'Enabled': True,
        'Origins': {
            'Quantity': 1,
            'Items': [
                {
                    'Id': f's3-{BUCKET_NAME}',
                    'DomainName': f'{BUCKET_NAME}.s3.us-east-1.amazonaws.com',
                    'OriginAccessControlId': oac_id,
                    'S3OriginConfig': {
                        'OriginAccessIdentity': ''
                    }
                }
            ]
        },
        'DefaultRootObject': 'index.html',
        'DefaultCacheBehavior': {
            'TargetOriginId': f's3-{BUCKET_NAME}',
            'ViewerProtocolPolicy': 'redirect-to-https',
            'AllowedMethods': {
                'Quantity': 2,
                'Items': ['GET', 'HEAD'],
                'CachedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD']
                }
            },
            'Compress': True,
            'ForwardedValues': {
                'QueryString': False,
                'Cookies': {'Forward': 'none'}
            },
            'MinTTL': 0,
            'DefaultTTL': 86400,
            'MaxTTL': 31536000,
            'TrustedSigners': {
                'Enabled': False,
                'Quantity': 0
            }
        },
        'CustomErrorResponses': {
            'Quantity': 1,
            'Items': [
                {
                    'ErrorCode': 404,
                    'ResponsePagePath': '/index.html',
                    'ResponseCode': '200',
                    'ErrorCachingMinTTL': 300
                }
            ]
        }
    }

    try:
        response = cloudfront.create_distribution(
            DistributionConfig=distribution_config
        )

        distribution_id = response['Distribution']['Id']
        domain_name = response['Distribution']['DomainName']

        print(f"  ✓ Created distribution: {distribution_id}")
        print(f"  ✓ Domain: {domain_name}")

        # Update S3 bucket policy to allow CloudFront
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowCloudFrontServicePrincipal",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "cloudfront.amazonaws.com"
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{BUCKET_NAME}/*",
                    "Condition": {
                        "StringEquals": {
                            "AWS:SourceArn": f"arn:aws:cloudfront::269610887017:distribution/{distribution_id}"
                        }
                    }
                }
            ]
        }

        s3.put_bucket_policy(Bucket=BUCKET_NAME, Policy=json.dumps(bucket_policy))
        print("  ✓ Updated bucket policy for CloudFront")

        return distribution_id, f"https://{domain_name}"

    except Exception as e:
        print(f"  Error: {e}")
        return None, None


def main():
    print("\n" + "=" * 80)
    print("DEPLOYING VOICE CHAT UI")
    print("=" * 80)

    # Upload to S3
    uploaded = upload_to_s3()

    if uploaded > 0:
        # Create CloudFront distribution
        distribution_id, url = create_cloudfront_distribution()

        if distribution_id:
            # Update deployment config
            print("\n" + "=" * 80)
            print("Updating Configuration")
            print("=" * 80)

            with open('/home/user/UTurnCreditAgent/deployment_config.json', 'r') as f:
                deploy_config = json.load(f)

            deploy_config['voice_chat_ui'] = {
                'bucket': BUCKET_NAME,
                'distribution_id': distribution_id,
                'url': url,
                'deployed_at': datetime.now().isoformat(),
                'files': uploaded
            }

            with open('/home/user/UTurnCreditAgent/deployment_config.json', 'w') as f:
                json.dump(deploy_config, f, indent=2)

            print("  ✓ Updated deployment_config.json")

            # Summary
            print("\n" + "=" * 80)
            print("✓ VOICE CHAT UI DEPLOYED!")
            print("=" * 80)
            print(f"\nURL: {url}")
            print("\nFeatures:")
            print("  ✓ WebSocket real-time chat")
            print("  ✓ Voice recording (browser-based)")
            print("  ✓ Multi-agent routing")
            print("  ✓ Knowledge Base integration")
            print("  ✓ REST API fallback")
            print("\nNote: CloudFront distribution may take 10-15 minutes to fully deploy.")
            print("      You can check status in AWS Console: CloudFront Distributions")


if __name__ == '__main__':
    main()
