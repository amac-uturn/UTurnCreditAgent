# UTurn Credit Service - Web UI

A professional web interface for interacting with UTurn Credit Card Customer Service AI agents.

## Quick Deploy to AWS Amplify

### Prerequisites
- AWS Account with Amplify access
- GitHub repository (this repo)
- Deployed agents (✓ Complete)

### Deployment Steps

#### Option 1: Deploy via AWS Amplify Console (Recommended)

1. **Go to AWS Amplify Console**
   ```
   https://console.aws.amazon.com/amplify/home?region=us-east-1
   ```

2. **Create New App**
   - Click "New app" → "Host web app"
   - Choose "GitHub" as source
   - Connect to repository: `amac-uturn/UTurnCreditAgent`
   - Branch: `claude/credit-card-service-agents-011sdDVaKaLKKRjLZjzK7cMC`
   - App root directory: `web-ui`

3. **Build Settings** (auto-detected from `amplify.yml`)
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: build
       files:
         - '**/*'
     cache:
       paths:
         - node_modules/**/*
   ```

4. **Environment Variables** (Add in Amplify Console)
   ```
   REACT_APP_AWS_REGION=us-east-1
   REACT_APP_ACCOUNT_ID=269610887017
   REACT_APP_AUTH_AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_authorization_agent-wAauASEhv8
   REACT_APP_ACCOUNT_AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_account_agent-55xVu6Cv86
   REACT_APP_SALES_AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_sales_agent-GcC04WEVGN
   ```

5. **Deploy**
   - Click "Save and deploy"
   - Wait 3-5 minutes for build
   - Access your app at: `https://[branch-name].[app-id].amplifyapp.com`

#### Option 2: Deploy via Amplify CLI

```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Configure Amplify
amplify configure

# Initialize Amplify in project
cd web-ui
amplify init

# Add hosting
amplify add hosting

# Publish
amplify publish
```

## Local Development

```bash
cd web-ui
npm install
npm start
```

App will open at `http://localhost:3000`

## Features

- 💬 **Text Chat Interface** - Converse with AI agents
- 🎯 **Smart Routing** - Automatically routes to the right agent
- 🔐 **Secure** - AWS Cognito authentication
- 📊 **Agent Status** - Real-time agent availability
- 🎨 **Professional UI** - Clean, modern design
- 📱 **Responsive** - Works on all devices

## Architecture

```
User Browser
     ↓
  React App (Amplify)
     ↓
  AWS API Gateway
     ↓
  Lambda Function
     ↓
  Bedrock Agent Runtime
     ↓
  Agent Core Endpoints
```

## Agent Integration

The app integrates with three deployed agents:

1. **Authorization Agent** - Security & fraud
2. **Account Agent** - Balances & transactions
3. **Sales Agent** - Products & applications

## Next Steps

1. **Enable Authentication** (Optional)
   ```bash
   amplify add auth
   amplify push
   ```

2. **Add API Gateway** (For backend)
   ```bash
   amplify add api
   amplify push
   ```

3. **Enable Voice** (Nova Sonic integration)
   - Add WebRTC for audio capture
   - Integrate with Nova Sonic S2S model
   - Enable real-time transcription

## Support

- Amplify Documentation: https://docs.amplify.aws/
- Bedrock Agent Core Docs: https://docs.aws.amazon.com/bedrock/

## License

Private - UTurn Data
