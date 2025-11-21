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
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentAgent, setCurrentAgent] = useState('account');
  const [transcription, setTranscription] = useState('');

  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioQueueRef = useRef([]);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
    // eslint-disable-next-line
  }, [customerId]);

  const connectWebSocket = () => {
    const ws = new WebSocket(`${CONFIG.WEBSOCKET_URL}?customerId=${customerId}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      addMessage('system', '🎤 Connected to UTurn Voice Assistant - Speak naturally!');
    };

    ws.onmessage = (event) => {
      console.log('Received:', event.data);
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'transcription') {
          // Display what user said
          setTranscription(data.text);
          addMessage('user', data.text, data.agent);
          setCurrentAgent(data.agent);

        } else if (data.type === 'audio_response') {
          // Play audio response and show text
          addMessage('assistant', data.text, data.agent);
          if (data.audioData) {
            playAudioResponse(data.audioData);
          }

        } else if (data.type === 'message') {
          // Handle text-only messages
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
      id: Date.now() + Math.random(),
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
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      // Create audio context for processing
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 16000
        });
      }

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
        processAndSendAudio(audioBlob);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
      setTranscription('🎤 Listening...');
      addMessage('system', '🎤 Listening... Speak now');

    } catch (error) {
      console.error('Error starting recording:', error);
      addMessage('system', `⚠️ Recording error: ${error.message}`);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setTranscription('Processing...');
    }
  };

  const processAndSendAudio = async (audioBlob) => {
    addMessage('system', '🔄 Processing speech with Nova Sonic...');

    try {
      // Convert audio blob to base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);

      reader.onloadend = () => {
        const base64Audio = reader.result.split(',')[1]; // Remove data:audio/webm;base64, prefix

        // Send to Nova Sonic via WebSocket
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            action: 'speech',
            audioData: base64Audio,
            customerId: customerId,
            sessionId: wsRef.current.url
          }));

          console.log('Audio sent to Nova Sonic for processing');
        } else {
          addMessage('system', '⚠️ WebSocket not connected. Please reconnect.');
        }
      };

    } catch (error) {
      console.error('Error processing audio:', error);
      addMessage('system', `⚠️ Audio processing error: ${error.message}`);
    }
  };

  const playAudioResponse = async (base64Audio) => {
    try {
      setIsSpeaking(true);

      // Decode base64 audio
      const audioData = atob(base64Audio);
      const audioArray = new Uint8Array(audioData.length);

      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i);
      }

      // Create audio blob
      const audioBlob = new Blob([audioArray], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);

      // Play audio
      const audio = new Audio(audioUrl);

      audio.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = (error) => {
        console.error('Audio playback error:', error);
        setIsSpeaking(false);
      };

      await audio.play();

    } catch (error) {
      console.error('Error playing audio:', error);
      setIsSpeaking(false);
    }
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
        <h1>🎙️ UTurn Voice Assistant</h1>
        <div className="subtitle">Powered by Amazon Nova Sonic & Bedrock Agent Core</div>
        <div className="connection-status">
          <span className={isConnected ? 'connected' : 'disconnected'}>
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
          {isSpeaking && <span className="speaking">🔊 Speaking...</span>}
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

      {transcription && (
        <div className="transcription-display">
          <strong>Transcription:</strong> {transcription}
        </div>
      )}

      <div className="quick-actions">
        <h3>Quick Actions (Click or Speak)</h3>
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
                <span className="role">
                  {msg.role === 'user' ? '👤 You' : msg.role === 'system' ? '⚙️ System' : '🤖 Assistant'}
                </span>
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
              className={`voice-btn ${isRecording ? 'recording' : ''} ${isSpeaking ? 'speaking' : ''}`}
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isSpeaking}
            >
              {isRecording ? '⏹️ Stop' : isSpeaking ? '🔊' : '🎤 Speak'}
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
        <div className="tech-stack">
          <span>✓ Nova Sonic S2S</span>
          <span>✓ Agent Core</span>
          <span>✓ Knowledge Bases</span>
          <span>✓ Real-time WebSocket</span>
        </div>
        <p className="instructions">
          <strong>How to use:</strong> Click "🎤 Speak" and talk naturally. Nova Sonic will transcribe your speech,
          route to the appropriate agent (Authorization, Account, or Sales), query the knowledge base,
          and respond with synthesized speech!
        </p>
      </footer>
    </div>
  );
}

export default App;
