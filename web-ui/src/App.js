import React, { useState, useRef, useEffect } from 'react';
import './App.css';

// Agent configuration (loaded from environment variables in production)
const AGENT_CONFIG = {
  region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
  accountId: process.env.REACT_APP_ACCOUNT_ID || '269610887017',
  agents: {
    authorization: process.env.REACT_APP_AUTH_AGENT_ARN || 'arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_authorization_agent-wAauASEhv8',
    account: process.env.REACT_APP_ACCOUNT_AGENT_ARN || 'arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_account_agent-55xVu6Cv86',
    sales: process.env.REACT_APP_SALES_AGENT_ARN || 'arn:aws:bedrock-agentcore:us-east-1:269610887017:runtime/uturn_sales_agent-GcC04WEVGN'
  }
};

function App() {
  const [messages, setMessages] = useState([
    {
      type: 'agent',
      text: 'Welcome to UTurn Credit Card Customer Service! How can I help you today?',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [customerId, setCustomerId] = useState('CUST-010000'); // Default test customer
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const routeToAgent = (userInput) => {
    const input = userInput.toLowerCase();

    // Authorization keywords
    const authKeywords = ['pin', 'security', 'fraud', 'lock', 'unlock', 'stolen', 'lost'];
    // Account keywords
    const accountKeywords = ['balance', 'transaction', 'payment', 'statement', 'due'];
    // Sales keywords
    const salesKeywords = ['apply', 'new card', 'upgrade', 'offer', 'product'];

    const authScore = authKeywords.filter(k => input.includes(k)).length;
    const accountScore = accountKeywords.filter(k => input.includes(k)).length;
    const salesScore = salesKeywords.filter(k => input.includes(k)).length;

    if (authScore >= accountScore && authScore >= salesScore && authScore > 0) {
      return 'authorization';
    } else if (accountScore >= salesScore && accountScore > 0) {
      return 'account';
    } else if (salesScore > 0) {
      return 'sales';
    } else {
      return 'account'; // Default
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMessage = {
      type: 'user',
      text: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Route to appropriate agent
      const agentType = routeToAgent(inputValue);

      // Simulate agent response (in production, this would call the actual agent via API Gateway)
      const agentResponse = await simulateAgentResponse(agentType, inputValue, customerId);

      const agentMessage = {
        type: 'agent',
        text: agentResponse.message,
        agent: agentType,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      const errorMessage = {
        type: 'agent',
        text: 'Sorry, I encountered an error. Please try again.',
        error: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const simulateAgentResponse = async (agentType, userInput, customerId) => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Sample responses based on agent type and input
    const responses = {
      authorization: {
        default: `I'm the Authorization Agent. For security verification, I can help you with PINs, fraud alerts, and card security. Customer ${customerId} is verified.`,
        pin: `I can help you reset your PIN. For security, I'll need to verify your identity first. Can you confirm your date of birth?`,
        fraud: `I've checked your account and found no active fraud alerts. Your card is secure and active.`,
        lock: `I can lock your card immediately for security. Would you like me to proceed with locking card ending in 8811?`
      },
      account: {
        default: `I'm the Account Agent. I can help with balances, transactions, and payments for customer ${customerId}.`,
        balance: `Your current balance is $24,989.54 with $17,184.46 available credit. Your minimum payment of $499.79 is due on December 23rd.`,
        transaction: `Your recent transactions include: Starbucks $271.62, Home Depot $1,241.61, and Walmart $1,296.47. Would you like to see more details?`,
        payment: `I can help you make a payment. Your minimum payment is $499.79. How much would you like to pay?`
      },
      sales: {
        default: `I'm the Sales Agent. I can help you explore our credit card products and check your eligibility.`,
        apply: `I'd be happy to help you apply for a new card! Based on your credit score of 677, you're eligible for our UTurn Cash Back Card with no annual fee and 2% cash back on groceries and gas.`,
        upgrade: `Great! You're eligible for an upgrade to the UTurn Rewards Plus Card with 3x points on dining. This card has a $95 annual fee but offers excellent rewards. Would you like to apply?`,
        offer: `We have a special offer for you! Earn 25,000 bonus points after your first purchase if you upgrade to the UTurn Rewards Plus Card. Offer expires in 30 days.`
      }
    };

    // Determine specific response based on keywords
    const agentResponses = responses[agentType];
    const input = userInput.toLowerCase();

    for (const [key, response] of Object.entries(agentResponses)) {
      if (input.includes(key)) {
        return {
          message: response,
          agent: agentType,
          customerId: customerId
        };
      }
    }

    return {
      message: agentResponses.default,
      agent: agentType,
      customerId: customerId
    };
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    { text: 'Check my balance', icon: '💳' },
    { text: 'Recent transactions', icon: '📊' },
    { text: 'Make a payment', icon: '💰' },
    { text: 'Apply for new card', icon: '✨' }
  ];

  return (
    <div className="App">
      <div className="container">
        {/* Header */}
        <div className="header">
          <h1>🏦 UTurn Credit Service</h1>
          <p>AI-Powered Customer Support</p>
          <div className="agent-status">
            <span className="status-dot"></span>
            <span>All Agents Online</span>
          </div>
        </div>

        {/* Customer Info */}
        <div className="customer-info">
          <label>Customer ID:</label>
          <input
            type="text"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Enter Customer ID"
          />
        </div>

        {/* Quick Actions */}
        <div className="quick-actions">
          {quickActions.map((action, index) => (
            <button
              key={index}
              className="quick-action-btn"
              onClick={() => setInputValue(action.text)}
            >
              <span>{action.icon}</span>
              <span>{action.text}</span>
            </button>
          ))}
        </div>

        {/* Messages */}
        <div className="messages">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.type} ${message.error ? 'error' : ''}`}
            >
              <div className="message-header">
                <span className="message-sender">
                  {message.type === 'user' ? 'You' : message.agent ? `${message.agent} Agent` : 'Agent'}
                </span>
                <span className="message-time">
                  {message.timestamp.toLocaleTimeString()}
                </span>
              </div>
              <div className="message-text">{message.text}</div>
            </div>
          ))}
          {isLoading && (
            <div className="message agent loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="input-container">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            rows={2}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !inputValue.trim()}
            className="send-button"
          >
            {isLoading ? '...' : 'Send →'}
          </button>
        </div>

        {/* Footer */}
        <div className="footer">
          <p>Powered by AWS Bedrock Agent Core & Amazon Nova</p>
          <p className="disclaimer">Demo Mode - Using simulated responses. Deploy to Amplify for live agent integration.</p>
        </div>
      </div>
    </div>
  );
}

export default App;
