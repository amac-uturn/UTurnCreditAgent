#!/usr/bin/env python3
"""
Deployment script for Authorization Agent
"""

import sys
import time

try:
    from bedrock_agentcore_starter_toolkit import Runtime
    import boto3
except ImportError:
    print("Error: Required packages not installed. Please run:")
    print("  pip install boto3 bedrock-agentcore-starter-toolkit")
    sys.exit(1)

# Configuration
REGION = "us-east-1"
AGENT_NAME = "uturn_authorization_agent"
ENTRYPOINT = "./authorization_agent.py"

def main():
    print("=" * 70)
    print("  UTurn Authorization Agent Deployment")
    print("=" * 70)
    print(f"\nAgent Name: {AGENT_NAME}")
    print(f"Region: {REGION}")
    print(f"Entrypoint: {ENTRYPOINT}\n")

    # Initialize AgentCore Runtime
    print("Initializing AgentCore Runtime...")
    agentcore_runtime = Runtime()

    # Step 1: Configure the runtime
    print("\n[1/3] Configuring runtime...")
    try:
        response = agentcore_runtime.configure(
            entrypoint=ENTRYPOINT,
            auto_create_execution_role=True,
            auto_create_ecr=True,
            requirements_file="requirements.txt",
            region=REGION,
            agent_name=AGENT_NAME
        )
        print("✓ Runtime configured successfully")
    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        sys.exit(1)

    # Step 2: Launch to AWS
    print("\n[2/3] Launching agent to AWS...")
    print("This may take 5-10 minutes...")
    try:
        launch_result = agentcore_runtime.launch()
        print("✓ Launch initiated successfully")
    except Exception as e:
        print(f"✗ Launch failed: {e}")
        sys.exit(1)

    # Step 3: Poll for completion
    print("\n[3/3] Waiting for deployment to complete...")
    max_wait_time = 600  # 10 minutes
    start_time = time.time()

    while True:
        try:
            status_response = agentcore_runtime.status()
            status = status_response.endpoint['status']

            elapsed = int(time.time() - start_time)
            print(f"  Status: {status} (elapsed: {elapsed}s)")

            if status == 'READY':
                print("\n✓ Deployment completed successfully!")
                break
            elif status == 'CREATE_FAILED':
                print("\n✗ Deployment failed!")
                print(f"Error details: {status_response}")
                sys.exit(1)
            elif elapsed > max_wait_time:
                print(f"\n✗ Deployment timeout after {max_wait_time}s")
                sys.exit(1)

            time.sleep(10)

        except Exception as e:
            print(f"✗ Error checking status: {e}")
            sys.exit(1)

    # Get final status and ARN
    print("\n" + "=" * 70)
    print("  Deployment Complete")
    print("=" * 70)

    try:
        final_status = agentcore_runtime.status()
        endpoint_arn = final_status.endpoint.get('endpointArn', 'N/A')
        print(f"\nAgent ARN: {endpoint_arn}")
        print(f"Agent Name: {AGENT_NAME}")
        print(f"Region: {REGION}")
        print(f"Status: READY")

        print("\nThe Authorization Agent is now deployed and ready to handle:")
        print("  • Customer identity verification")
        print("  • Fraud detection and status checks")
        print("  • Card lock/unlock operations")
        print("  • Security settings management")
        print("  • Suspicious transaction reporting")

    except Exception as e:
        print(f"Warning: Could not retrieve final status: {e}")

if __name__ == "__main__":
    main()
