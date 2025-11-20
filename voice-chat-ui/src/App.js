import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// Configuration from deployment
const CONFIG = {
  WEBSOCKET_URL: 'wss://jjmdrlszmg.execute-api.us-east-1.amazonaws.com/prod',
  REST_API_URL: 'https://sr6egyg843.execute-api.us-east-1.amazonaws.com/prod/invoke'
};

function App() {
  const [customerId, setCustomerId] = useState('CUST-010000');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentAgent, setCurrentAgent] = useState('account');

  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [customerId]);

  const connectWebSocket = () => {
    const ws = new WebSocket(`${CONFIG.WEBSOCKET_URL}?customerId=${customerId}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      addMessage('system', 'Connected to UTurn Credit Card Service');
    };

    ws.onmessage = (event) => {
      console.log('Received:', event.data);
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
          addMessage('assistant', data.content, data.agent);
        }
      } catch (e) {
        console.error('Parse error:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setIsConnected(false);
      addMessage('system', 'Disconnected from service');
    };

    wsRef.current = ws;
  };

  const addMessage = (role, content, agent = null) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      role,
      content,
      agent,
      timestamp: new Date().toLocaleTimeString()
    }]);
  };

  const sendMessage = async (text = null) => {
    const messageText = text || inputMessage;
    if (!messageText.trim()) return;

    // Add user message
    addMessage('user', messageText);
    setInputMessage('');

    // Send via WebSocket if connected, otherwise use REST API
    if (isConnected && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'message',
        message: messageText,
        customerId: customerId
      }));
    } else {
      // Fallback to REST API
      try {
        const response = await fetch(CONFIG.REST_API_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: messageText,
            customer_id: customerId
          })
        });

        const data = await response.json();
        addMessage('assistant', data.message, data.agent);
      } catch (error) {
        addMessage('system', `Error: ${error.message}`);
      }
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        processAudio(audioBlob);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      addMessage('system', 'Recording... Speak now');

    } catch (error) {
      console.error('Error starting recording:', error);
      addMessage('system', `Recording error: ${error.message}`);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudio = async (audioBlob) => {
    addMessage('system', 'Processing audio...');

    // For now, convert to text using a placeholder
    // In production, this would use Amazon Transcribe or Nova Sonic
    addMessage('system', 'Audio captured. Note: Speech-to-text requires Amazon Transcribe integration.');
    addMessage('user', '[Voice message: ' + (audioBlob.size / 1024).toFixed(1) + ' KB]');

    // Simulate a response
    setTimeout(() => {
      addMessage('assistant', 'I received your voice message. For full voice functionality, Amazon Transcribe or Nova Sonic integration is required.', 'account');
    }, 1000);
  };

  const quickActions = [
    { text: 'Check my balance', agent: 'account' },
    { text: 'Recent transactions', agent: 'account' },
    { text: 'Make a payment', agent: 'account' },
    { text: 'Lock my card', agent: 'authorization' },
    { text: 'Report fraud', agent: 'authorization' },
    { text: 'View credit cards', agent: 'sales' },
    { text: 'Apply for new card', agent: 'sales' }
  ];

  const handleQuickAction = (action) => {
    sendMessage(action.text);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎤 UTurn Credit Card Voice Chat</h1>
        <div className="connection-status">
          <span className={isConnected ? 'connected' : 'disconnected'}>
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
      </header>

      <div className="customer-info">
        <label>
          Customer ID:
          <input
            type="text"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Enter Customer ID"
          />
        </label>
        <span className="agent-badge">{currentAgent.toUpperCase()} Agent</span>
      </div>

      <div className="quick-actions">
        <h3>Quick Actions</h3>
        <div className="action-buttons">
          {quickActions.map((action, idx) => (
            <button
              key={idx}
              onClick={() => handleQuickAction(action)}
              className="action-btn"
            >
              {action.text}
            </button>
          ))}
        </div>
      </div>

      <div className="chat-container">
        <div className="messages">
          {messages.map(msg => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div className="message-header">
                <span className="role">{msg.role === 'user' ? 'You' : msg.role === 'system' ? 'System' : 'Assistant'}</span>
                {msg.agent && <span className="agent-tag">{msg.agent}</span>}
                <span className="time">{msg.timestamp}</span>
              </div>
              <div className="message-content">{msg.content}</div>
            </div>
          ))}
        </div>

        <div className="input-area">
          <div className="voice-controls">
            <button
              className={`voice-btn ${isRecording ? 'recording' : ''}`}
              onClick={isRecording ? stopRecording : startRecording}
            >
              {isRecording ? '⏹️ Stop' : '🎤 Voice'}
            </button>
          </div>

          <div className="text-input">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type your message or use voice..."
            />
            <button onClick={() => sendMessage()}>Send</button>
          </div>
        </div>
      </div>

      <footer>
        <p>Powered by Amazon Bedrock Agent Core & Knowledge Bases</p>
        <div className="tech-stack">
          <span>✓ WebSocket API</span>
          <span>✓ Knowledge Base</span>
          <span>✓ Multi-Agent</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
