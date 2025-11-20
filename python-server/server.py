#!/usr/bin/env python3
"""
WebSocket Server for UTurn Credit Card Customer Service
Orchestrates multi-agent system with speech-to-speech capabilities
"""

import asyncio
import json
import websockets
import boto3
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')


class AgentOrchestrator:
    """Orchestrates requests across three specialized agents."""

    def __init__(self):
        self.authorization_agent_arn = None  # Set after deployment
        self.account_agent_arn = None        # Set after deployment
        self.sales_agent_arn = None          # Set after deployment

        self.sessions = {}  # Track active sessions

    def route_request(self, user_input: str) -> str:
        """
        Route user request to appropriate agent based on intent.

        Args:
            user_input: User's question or request

        Returns:
            Name of the agent to handle the request
        """
        user_input_lower = user_input.lower()

        # Authorization Agent keywords
        auth_keywords = [
            'pin', 'security', 'fraud', 'lock', 'unlock', 'verify', 'identity',
            'suspicious', 'stolen', 'lost card', 'password', 'authentication'
        ]

        # Account Agent keywords
        account_keywords = [
            'balance', 'transaction', 'payment', 'statement', 'due date',
            'autopay', 'rewards', 'points', 'miles', 'history', 'charge'
        ]

        # Sales Agent keywords
        sales_keywords = [
            'apply', 'application', 'new card', 'upgrade', 'product',
            'offer', 'eligible', 'eligibility', 'compare', 'benefits',
            'annual fee', 'apr', 'credit limit'
        ]

        # Check which keywords match
        auth_score = sum(1 for keyword in auth_keywords if keyword in user_input_lower)
        account_score = sum(1 for keyword in account_keywords if keyword in user_input_lower)
        sales_score = sum(1 for keyword in sales_keywords if keyword in user_input_lower)

        # Route to highest scoring agent
        if auth_score >= account_score and auth_score >= sales_score and auth_score > 0:
            return 'authorization'
        elif account_score >= sales_score and account_score > 0:
            return 'account'
        elif sales_score > 0:
            return 'sales'
        else:
            # Default to account agent for general inquiries
            return 'account'

    async def invoke_agent(self, agent_type: str, user_input: str, customer_id: str) -> Dict[str, Any]:
        """
        Invoke the specified agent with the user's input.

        Args:
            agent_type: Type of agent ('authorization', 'account', 'sales')
            user_input: User's question or request
            customer_id: Customer ID for context

        Returns:
            Agent response
        """
        # Prepare payload
        payload = {
            'input': user_input,
            'customer_id': customer_id,
            'timestamp': datetime.now().isoformat()
        }

        # Get agent ARN
        agent_arns = {
            'authorization': self.authorization_agent_arn,
            'account': self.account_agent_arn,
            'sales': self.sales_agent_arn
        }

        agent_arn = agent_arns.get(agent_type)

        if not agent_arn:
            return {
                'error': f'Agent {agent_type} not configured',
                'message': 'Please deploy the agents first using the deployment scripts.'
            }

        try:
            # Invoke AgentCore endpoint
            response = bedrock_agent.invoke_agent_runtime(
                agentRuntimeArn=agent_arn,
                payload=json.dumps(payload)
            )

            return {
                'agent': agent_type,
                'response': response.get('output', 'No response from agent'),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'error': str(e),
                'agent': agent_type,
                'message': 'Error invoking agent. Please check agent deployment.'
            }

    async def handle_conversation(self, user_input: str, customer_id: str, session_id: str) -> Dict[str, Any]:
        """
        Handle a conversation turn.

        Args:
            user_input: User's input (text or transcribed speech)
            customer_id: Customer ID
            session_id: Session ID for tracking

        Returns:
            Response from appropriate agent
        """
        # Route to appropriate agent
        agent_type = self.route_request(user_input)

        print(f"[{session_id}] Routing to {agent_type} agent: {user_input[:50]}...")

        # Invoke the agent
        response = await self.invoke_agent(agent_type, user_input, customer_id)

        return response


class WebSocketServer:
    """WebSocket server for handling client connections."""

    def __init__(self, orchestrator: AgentOrchestrator):
        self.orchestrator = orchestrator
        self.active_connections = set()

    async def handle_client(self, websocket, path):
        """Handle a client WebSocket connection."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.active_connections.add(websocket)

        print(f"[{session_id}] Client connected from {websocket.remote_address}")

        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': 'Welcome to UTurn Credit Card Customer Service',
                'session_id': session_id
            }))

            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)

                    message_type = data.get('type')

                    if message_type == 'text_input':
                        # Handle text input
                        user_input = data.get('input')
                        customer_id = data.get('customer_id', 'CUST-010000')  # Default for demo

                        response = await self.orchestrator.handle_conversation(
                            user_input, customer_id, session_id
                        )

                        await websocket.send(json.dumps({
                            'type': 'agent_response',
                            'session_id': session_id,
                            **response
                        }))

                    elif message_type == 'audio_input':
                        # Handle audio input (to be implemented with Nova Sonic)
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': 'Audio input not yet implemented'
                        }))

                    elif message_type == 'ping':
                        # Health check
                        await websocket.send(json.dumps({
                            'type': 'pong',
                            'timestamp': datetime.now().isoformat()
                        }))

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))

                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': str(e)
                    }))

        except websockets.exceptions.ConnectionClosed:
            print(f"[{session_id}] Client disconnected")

        finally:
            self.active_connections.remove(websocket)

    async def start(self, host='0.0.0.0', port=8765):
        """Start the WebSocket server."""
        print("=" * 70)
        print("  UTurn Customer Service WebSocket Server")
        print("=" * 70)
        print(f"\nStarting server on ws://{host}:{port}")
        print("\nReady to handle customer service requests!")
        print("Press Ctrl+C to stop the server\n")

        async with websockets.serve(self.handle_client, host, port):
            await asyncio.Future()  # Run forever


def main():
    """Main entry point."""
    # Initialize orchestrator
    orchestrator = AgentOrchestrator()

    # TODO: Load agent ARNs from configuration file after deployment
    # For now, these will be None and return helpful error messages

    # Create and start server
    server = WebSocketServer(orchestrator)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
