"""
Deploy React build to S3 and CloudFront
"""

import boto3
import json
import os
import mimetypes
from pathlib import Path

s3 = boto3.client('s3', region_name='us-east-1')
cloudfront = boto3.client('cloudfront', region_name='us-east-1')

# Use existing web UI bucket from deployment config
with open('/home/user/UTurnCreditAgent/deployment_config.json', 'r') as f:
    deploy_config = json.load(f)

# Get existing CloudFront distribution
BUCKET_NAME = 'uturn-web-ui-20251120201917'  # From previous deployment
DISTRIBUTION_ID = 'E3DC1B9P5LMAQE'  # From previous deployment

BUILD_DIR = '/home/user/UTurnCreditAgent/voice-chat-ui/build'


def upload_file_to_s3(file_path, bucket, object_name):
    """Upload a file to S3 bucket with correct content type"""
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'

    extra_args = {'ContentType': content_type}

    # Add cache control for static assets
    if '/static/' in object_name:
        extra_args['CacheControl'] = 'public, max-age=31536000'
    else:
        extra_args['CacheControl'] = 'public, max-age=0, must-revalidate'

    try:
        s3.upload_file(file_path, bucket, object_name, ExtraArgs=extra_args)
        return True
    except Exception as e:
        print(f"Error uploading {object_name}: {e}")
        return False


def deploy_to_s3():
    """Deploy build directory to S3"""
    print("=" * 80)
    print("Deploying React App to S3")
    print("=" * 80)

    uploaded = 0
    failed = 0

    # Walk through build directory
    for root, dirs, files in os.walk(BUILD_DIR):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, BUILD_DIR)
            s3_path = relative_path.replace('\\', '/')

            print(f"Uploading: {s3_path}")

            if upload_file_to_s3(local_path, BUCKET_NAME, s3_path):
                uploaded += 1
            else:
                failed += 1

    print(f"\n✓ Uploaded {uploaded} files")
    if failed > 0:
        print(f"✗ Failed {failed} files")

    return uploaded, failed


def invalidate_cloudfront():
    """Invalidate CloudFront cache"""
    print("\n" + "=" * 80)
    print("Invalidating CloudFront Cache")
    print("=" * 80)

    try:
        response = cloudfront.create_invalidation(
            DistributionId=DISTRIBUTION_ID,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': ['/*']
                },
                'CallerReference': str(int(__import__('time').time()))
            }
        )

        invalidation_id = response['Invalidation']['Id']
        print(f"✓ Invalidation created: {invalidation_id}")
        print("  Cache will be cleared in 1-2 minutes")

        return invalidation_id

    except Exception as e:
        print(f"Error creating invalidation: {e}")
        return None


def main():
    print("\n" + "=" * 80)
    print("DEPLOYING VOICE CHAT UI TO CLOUDFRONT")
    print("=" * 80)
    print(f"\nTarget Bucket: {BUCKET_NAME}")
    print(f"Distribution ID: {DISTRIBUTION_ID}")

    # Deploy to S3
    uploaded, failed = deploy_to_s3()

    if uploaded > 0:
        # Invalidate CloudFront
        invalidation_id = invalidate_cloudfront()

        # Update deployment config
        print("\n" + "=" * 80)
        print("Updating Configuration")
        print("=" * 80)

        deploy_config['voice_chat_ui'] = {
            'bucket': BUCKET_NAME,
            'distribution_id': DISTRIBUTION_ID,
            'url': 'https://d19smcc411vk38.cloudfront.net',
            'build_time': __import__('datetime').datetime.now().isoformat(),
            'files_deployed': uploaded
        }

        with open('/home/user/UTurnCreditAgent/deployment_config.json', 'w') as f:
            json.dump(deploy_config, f, indent=2)

        print("✓ Updated deployment_config.json")

        # Summary
        print("\n" + "=" * 80)
        print("✓ DEPLOYMENT COMPLETE!")
        print("=" * 80)
        print(f"\nVoice Chat UI URL: https://d19smcc411vk38.cloudfront.net")
        print(f"\nDeployed {uploaded} files")
        print("\nFeatures:")
        print("  ✓ WebSocket real-time chat")
        print("  ✓ Voice recording capability")
        print("  ✓ Multi-agent routing")
        print("  ✓ Knowledge Base integration")
        print("  ✓ Quick action buttons")
        print("\nWait 1-2 minutes for CloudFront cache to clear, then test the app!")

    else:
        print("\n✗ No files were uploaded. Please check the build directory.")


if __name__ == '__main__':
    main()
