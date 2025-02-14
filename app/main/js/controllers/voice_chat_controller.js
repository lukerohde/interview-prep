import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["walkieButton", "micSelect", "status"]
  static values = {
    sessionUrl: String,
    autoConnect: Boolean,
    baseUrl: { type: String, default: 'https://api.openai.com/v1/realtime' },
    model: { type: String, default: 'gpt-4o-realtime-preview-2024-12-17' }
  }

  registeredTools = []

  connect() {
    // Listen for tool registrations using data-action in the HTML

    if (this.autoConnectValue) {
      this.initializeConnection();
    }
  }

  disconnect() {
    this.closeConnection();
  }

  registerTool(tool) {
    this.registeredTools.push(tool.detail)
    if (this.isConnected && this.dc) {
      this.updateTools()
    }
  }

  updateTools() {
    const toolsUpdate = {
      type: 'session.update',
      session: {
        tools: this.registeredTools,
        tool_choice: 'auto'
      }
    }
    this.sendEvent(toolsUpdate)
  }

  sendEvent(event) {
    if (this.dc) {
      this.dc.send(JSON.stringify(event));
    } else {
      console.warn('Data channel not available');
    }
  }

  initialize() {
    this.holdTimer = null;
    this.pushTalkActive = false;
    this.pc = null;
    this.dc = null;
    this.audioEl = null;
    this.microphoneStream = null;
    this.isConnected = false;
    this.ephemeralKey = null;
    this.isMuted = true;
    this.isHolding = false;
    this.audioTrack = null;
    this.pressStartTime = 0;
    this.holdThreshold = 200; // ms to distinguish between click and hold

    // Set initial mute state on the button
    if (this.hasWalkieButtonTarget) {
      this.walkieButtonTarget.setAttribute('data-muted', 'true');
    }
  }


  async initializeConnection() {
    try {
      // Update state to connecting
      this.walkieButtonTarget.setAttribute('data-state', 'connecting');
      
      // Get session token first
      await this.getSessionToken();
      
      // Setup microphone
      await this.setupMicrophone();
      
      // Setup WebRTC with the session token
      await this.setupWebRTC();
      
      // Update state to connected
      this.walkieButtonTarget.setAttribute('data-state', 'connected');

      // Send registered tools if any exist
      if (this.registeredTools.length > 0) {
        this.updateTools();
      }
    } catch (error) {
      this.walkieButtonTarget.setAttribute('data-state', 'error');
      this.updateStatus(`Error: ${error.message}. Click to retry.`, 'error');
    }
  }

  async getSessionToken() {
    this.updateStatus('Getting session token...', 'info');
    const response = await fetch(this.sessionUrlValue, {
      credentials: 'same-origin'
    });
    const data = await response.json();
    
    if (data.error) {
      throw new Error(data.error);
    }
    
    this.ephemeralKey = data.client_secret;
    this.updateStatus('Session token received', 'success');
  }

  async setupMicrophone() {
    try {
      this.updateStatus('Setting up microphone...', 'info');
      this.microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Start with microphone muted
      this.audioTrack = this.microphoneStream.getAudioTracks()[0];
      this.audioTrack.enabled = false;
      this.isMuted = true;
      
      // Update UI to reflect muted state
      if (this.hasWalkieButtonTarget) {
        this.walkieButtonTarget.setAttribute('data-muted', 'true');
      }
      
      // Set up track error handling
      this.audioTrack.addEventListener('ended', () => this.handleTrackEnded());
      
      // Set up periodic track check
      this.trackCheckInterval = setInterval(() => this.checkTrackStatus(), 1000);
      
      await this.updateAudioDevices();
      this.updateStatus(`Using microphone: ${this.audioTrack.label}`, 'success');
      
      // Set up space bar controls for push-to-talk
    } catch (error) {
      throw new Error('Failed to access microphone: ' + error.message);
    }
  }

  handleTrackEnded() {
    this.handleMicrophoneFailure('Microphone disconnected');
  }

  checkTrackStatus() {
    // Don't check during WebRTC setup
    if (this.isSettingUpWebRTC) {
      return;
    }

    // Only consider a track failed if:
    // 1. We have no track, or
    // 2. The track exists but its readyState is 'ended'
    const track = this.microphoneStream?.getAudioTracks()[0];
    if (!track || track.readyState === 'ended') {
      this.handleMicrophoneFailure('Microphone disconnected');
    }
  }

  handleMicrophoneFailure(reason) {
    // Clear the check interval
    if (this.trackCheckInterval) {
      clearInterval(this.trackCheckInterval);
      this.trackCheckInterval = null;
    }

    // Clean up the track
    if (this.audioTrack) {
      this.audioTrack.stop();
      this.audioTrack = null;
    }

    if (this.microphoneStream) {
      this.microphoneStream.getTracks().forEach(track => track.stop());
      this.microphoneStream = null;
    }

    // Update UI
    this.walkieButtonTarget.setAttribute('data-state', 'error');
    this.walkieButtonTarget.classList.remove('active');
    this.isConnected = false;
    this.updateStatus(`${reason}. Click to reconnect.`, 'error');
  }


  pressStartCommon() {
    // If not connected, initialize the connection now
    if (!this.isConnected) {
      this.initializeConnection();
    }

    // If still no audio track after we try to connect, bail out
    if (!this.audioTrack) return;

    this.pressStartTime = Date.now();

    // Clear any existing hold timer
    if (this.holdTimer) {
      clearTimeout(this.holdTimer);
      this.holdTimer = null;
    }

    // Schedule a timer for push-to-talk if user holds longer than threshold
    this.holdTimer = setTimeout(() => {
      this.pushTalkActive = true;
      this.startTalking();
    }, this.holdThreshold);
  }

  pressEndCommon() {
    if (this.holdTimer) {
      clearTimeout(this.holdTimer);
      this.holdTimer = null;
    }

    const pressDuration = Date.now() - this.pressStartTime;

    if (this.pushTalkActive) {
      // Was in push-to-talk mode
      this.stopTalking();
      this.pushTalkActive = false;
    } else if (pressDuration < this.holdThreshold) {
      // Short press => toggle mute
      this.toggleMute();
    }
  }

  /* =====================
   *  POINTER EVENTS
   * ===================== */

  pressStart(event) {
    // Usually no need for preventDefault if it's a button element
    this.pressStartCommon();
  }

  pressEnd(event) {
    this.pressEndCommon();
  }

  /* =====================
   *  SPACEBAR EVENTS
   * ===================== */

  spaceDown(event) {
    // Only handle space, skip repeats
    if (event.code !== "Space" || event.repeat) return;

    // If user is typing in a text field, let space pass
    if (event.target.matches('input, textarea, [contenteditable="true"]')) {
      return;
    }

    // Prevent scrolling when pressing space
    event.preventDefault();
    this.pressStartCommon();
  }

  spaceUp(event) {
    if (event.code !== "Space") return;

    // Same text field check
    if (event.target.matches('input, textarea, [contenteditable="true"]')) {
      return;
    }

    // Prevent scroll on space release
    event.preventDefault();
    this.pressEndCommon();
  }



  async updateAudioDevices() {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const audioDevices = devices.filter(device => device.kind === 'audioinput');
    
    if (this.hasMicSelectTarget) {
      this.micSelectTarget.innerHTML = audioDevices
        .map(device => `<option value="${device.deviceId}">${device.label || 'Microphone ' + (i + 1)}</option>`)
        .join('');
    }
  }

  async switchMicrophone(event) {
    const deviceId = event.target.value;
    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: { exact: deviceId } }
      });

      if (this.pc && this.microphoneStream) {
        const sender = this.pc.getSenders().find(s => s.track.kind === 'audio');
        if (sender) {
          await sender.replaceTrack(newStream.getAudioTracks()[0]);
        }
      }

      this.microphoneStream.getAudioTracks().forEach(track => track.stop());
      this.microphoneStream = newStream;
      this.updateStatus('Microphone switched successfully', 'success');
    } catch (error) {
      this.updateStatus('Failed to switch microphone: ' + error.message, 'error');
    }
  }

  async setupWebRTC() {
    this.isSettingUpWebRTC = true;
    try {
      if (!this.ephemeralKey) {
        throw new Error('No session token available');
      }

      if (!this.microphoneStream) {
        throw new Error('No microphone stream available');
      }
      
      this.updateStatus('Creating WebRTC connection...', 'info');
      this.pc = new RTCPeerConnection();

      // Set up audio playback
      this.audioEl = document.createElement('audio');
      this.audioEl.autoplay = true;
      this.pc.ontrack = e => {
        console.log('Received audio track', e);
        this.audioEl.srcObject = e.streams[0];
      };

      // Add microphone track
      this.pc.addTrack(this.microphoneStream.getAudioTracks()[0], this.microphoneStream);
      
      // Set up data channel
      this.dc = this.pc.createDataChannel('oai-events');
      this.setupDataChannelHandlers();
      
      const offer = await this.pc.createOffer();
      await this.pc.setLocalDescription(offer);
      
      // Connect to OpenAI's Realtime API
      this.updateStatus('Connecting to OpenAI...', 'info');
      const sdpResponse = await fetch(`${this.baseUrlValue}?model=${this.modelValue}`, {
        method: 'POST',
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${this.ephemeralKey}`,
          'Content-Type': 'application/sdp'
        },
      });

      if (!sdpResponse.ok) {
        const error = await sdpResponse.json();
        throw new Error('Failed to connect to OpenAI: ' + error.error?.message || 'Unknown error');
      } 
      
      const answer = {
        type: 'answer',
        sdp: await sdpResponse.text(),
      };
      await this.pc.setRemoteDescription(answer);

      // Wait for data channel to open
      if (this.dc.readyState !== 'open') {
        await this.waitForDataChannel();
      }

      if (!this.pc) {
        throw new Error('No WebRTC connection available');
      }

      if (!this.dc) {
        throw new Error('No data channel available');
      }

      if (this.dc.readyState !== 'open') {
        throw new Error('Data channel not open');
      }

      if (!this.microphoneStream) {
        throw new Error('No microphone stream available');
      }

      // Only mark as connected if we have everything we need
      if (this.pc && this.dc && this.dc.readyState === 'open' && this.microphoneStream) {
        this.isConnected = true;
        this.walkieButtonTarget.setAttribute('data-state', 'connected');
        this.updateStatus('Connection established!', 'success');
      } else {
        throw new Error('Connection incomplete');
      }
    } catch (error) {
      console.error('Error setting up WebRTC:', error);
      this.isConnected = false;
      this.walkieButtonTarget.setAttribute('data-state', 'error');
      this.updateStatus(`Error: ${error.message}`, 'error');
      this.closeConnection();
      this.isSettingUpWebRTC = false;
      throw error;
    } finally {
      this.isSettingUpWebRTC = false;
    }
  }

  setupDataChannelHandlers() {
    this.dc.onopen = () => {
      console.log('Data channel opened');
      this.updateStatus('Data channel ready', 'success');
    };

    this.dc.onclose = () => {
      console.log('Data channel closed');
      this.updateStatus('Connection closed', 'info');
      this.isConnected = false;
    };

    this.dc.onerror = (error) => {
      console.error('Data channel error:', error);
      this.updateStatus('Connection error', 'error');
      this.closeConnection();
    };

    this.dc.onmessage = this.handleMessage.bind(this);
  }

  async waitForDataChannel() {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout waiting for data channel'));
      }, 5000);

      this.dc.onopen = () => {
        clearTimeout(timeout);
        resolve();
      };
    });
  }

  handleMessage(event) {
    const message = JSON.parse(event.data);

    // Handle different message types
    switch (message.type) {
      case 'conversation.item.input_audio_transcription.completed':
        document.dispatchEvent(new CustomEvent('voice-chat:user-transcript', {
          detail: { transcript: message.transcript }
        }));
        break;

      case 'response.audio_transcript.delta':
        document.dispatchEvent(new CustomEvent('voice-chat:ai-transcript-delta', {
          detail: { delta: message.delta }
        }));
        break;

      case 'response.audio_transcript.done':
        document.dispatchEvent(new CustomEvent('voice-chat:ai-transcript-done', {
          detail: { transcript: message.transcript }
        }));
        break;

      case 'response.done':
      case 'response.function_call_arguments.done':
        // Handle function calls in the response
        console.log(message)
        if (message.response && message.response.output) {
          message.response.output.forEach(item => {
            if (item.type === 'function_call' && item.status === 'completed') {
              this.dispatch('function-call', {
                detail: {
                  name: item.name,
                  arguments: JSON.parse(item.arguments),
                  callId: item.call_id
                }
              });
            }
          });
        }
        break;

      case 'error':
        this.updateStatus(`Error: ${message.error}`, 'error');
        break;

      default:
  }


    // Also dispatch the raw message for other controllers
    const customEvent = new CustomEvent('voice-chat-message', {
      detail: message,
      bubbles: true
    });
    this.element.dispatchEvent(customEvent);
  }

  closeConnection() {
    // Clear any existing hold timer
    if (this.holdTimer) {
      clearTimeout(this.holdTimer);
      this.holdTimer = null;
    }
    this.pushTalkActive = false;

    if (this.dc) {
      this.dc.close();
      this.dc = null;
    }

    if (this.pc) {
      this.pc.close();
      this.pc = null;
    }

    if (this.trackCheckInterval) {
      clearInterval(this.trackCheckInterval);
      this.trackCheckInterval = null;
    }

    if (this.microphoneStream) {
      this.microphoneStream.getTracks().forEach(track => track.stop());
      this.microphoneStream = null;
    }

    if (this.audioEl) {
      this.audioEl.srcObject = null;
      this.audioEl = null;
    }

    // Remove push-to-talk handlers
    if (this.pushToTalkHandlers) {
      document.removeEventListener('keydown', this.pushToTalkHandlers.keydown);
      document.removeEventListener('keyup', this.pushToTalkHandlers.keyup);
      this.pushToTalkHandlers = null;
    }

    this.isConnected = false;
    this.ephemeralKey = null;
    
    // Reset icon to disconnected state
    if (this.hasWalkieButtonTarget) {
      this.walkieButtonTarget.setAttribute('data-state', 'disconnected');
      this.walkieButtonTarget.classList.remove('active');
    }
    
    this.updateStatus('Connection closed', 'info');
  }

  updateStatus(message, type = 'info') {
    if (this.hasStatusTarget) {
      this.statusTarget.textContent = message;
      this.statusTarget.className = `voice-status text-${type}`;
    }
  }

  enableVAD() {
    const sessionUpdate = {
      type: "session.update",
      session: {
        turn_detection: {
          type: "server_vad",
          threshold: 0.5,
          prefix_padding_ms: 300,
          silence_duration_ms: 500,
          create_response: true
        }
      }
    };
    this.sendEvent(sessionUpdate);
  }

  disableVAD() {
    const sessionUpdate = {
      type: "session.update",
      session: {
        turn_detection: null
      }
    };
    this.sendEvent(sessionUpdate);
  }

  commitAudioBuffer() {
    const commit = {
      type: "input_audio_buffer.commit"
    };
    this.sendEvent(commit);
  }

  addContext(event) {
    console.log('Voice chat received context:', event.detail)
    const context = event.detail
    if (!context) return

    const contextEvent = {
      type: "conversation.item.create",
      item: {
        type: "message",
        role: "user",
        content: [
          {
            type: "input_text",
            text: context
          }
        ]
      }
    }

    this.sendEvent(contextEvent)
  }

  pleaseRespond() {
    console.log('Voice chat received please-respond')
    const response = {
      type: "response.create"
    }
    this.sendEvent(response)
  }

  clearAudioBuffer() {
    const clear = {
      type: "input_audio_buffer.clear"
    };
    this.sendEvent(clear);
  }

  startTalking() {
    if (!this.audioTrack || !this.isConnected) return;
    
    this.isHolding = true;
    this.audioTrack.enabled = true;
    this.walkieButtonTarget.classList.add('active');
    this.disableVAD();
    this.updateStatus('Listening...', 'info');
  }

  stopTalking() {
    if (!this.audioTrack || !this.isConnected) return;
    
    this.isHolding = false;
    
    // Commit the audio buffer and create response
    this.commitAudioBuffer();
    this.pleaseRespond();
    
    // If we're unmuted, re-enable VAD and keep the UI in unmuted state
    if (!this.isMuted) {
      this.audioTrack.enabled = true;
      this.enableVAD();
      this.updateStatus('Channel open (tap to mute)', 'info');
    } else {
      // If muted, disable audio and update UI accordingly
      this.audioTrack.enabled = false;
      this.walkieButtonTarget.classList.remove('active');
      this.updateStatus('Hold to talk or tap to toggle', 'info');
    }
  }

  toggleMute() {
    if (!this.audioTrack || !this.isConnected) return;
    
    this.isMuted = !this.isMuted;
    //this.audioTrack.enabled = !this.isMuted;
    
    // Update button state
    if (this.hasWalkieButtonTarget) {
      this.walkieButtonTarget.setAttribute('data-muted', this.isMuted.toString());
      const icon = this.walkieButtonTarget.querySelector('i');
      
      if (this.isMuted) {
        this.audioTrack.enabled = false;
        this.walkieButtonTarget.classList.remove('active');
        icon.className = 'bi bi-mic-mute';
      } else {
        this.audioTrack.enabled = true;
        this.walkieButtonTarget.classList.add('active');
        icon.className = 'bi bi-mic';
        // When unmuting and not in push-to-talk mode
        this.clearAudioBuffer();  
        if (!this.isHolding) {
          this.enableVAD();
        }
      }
    }
    
    if (this.isMuted) {
      this.updateStatus('Hold to talk or tap to toggle', 'info');
    } else {
      this.updateStatus('Channel open (tap to mute)', 'info');
    }
  }
}
