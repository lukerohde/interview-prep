import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["container"]

  connect() {
    // Listen for transcript events from voice chat controller
    document.addEventListener('voice-chat:user-transcript', this.handleUserTranscript.bind(this))
    document.addEventListener('voice-chat:ai-transcript-delta', this.handleAITranscriptDelta.bind(this))
    document.addEventListener('voice-chat:ai-transcript-done', this.handleAITranscriptDone.bind(this))
    
    // Initialize streaming transcript element
    this.streamingTranscript = document.createElement('div')
    this.streamingTranscript.classList.add('streaming-transcript')
  }

  disconnect() {
    document.removeEventListener('voice-chat:user-transcript', this.handleUserTranscript.bind(this))
    document.removeEventListener('voice-chat:ai-transcript-delta', this.handleAITranscriptDelta.bind(this))
    document.removeEventListener('voice-chat:ai-transcript-done', this.handleAITranscriptDone.bind(this))
  }

  handleUserTranscript(event) {
    const message = this.createMessageElement('user', event.detail.transcript)
    this.containerTarget.appendChild(message)

    // If there's an in-progress AI message, move it after this user message
    if (this.streamingTranscript.parentElement) {
      const aiMessage = this.streamingTranscript.parentElement.closest('.message')
      if (aiMessage) {
        this.containerTarget.appendChild(aiMessage)
      }
    }

    this.scrollToBottom()
  }

  handleAITranscriptDelta(event) {
    if (!this.streamingTranscript.parentElement) {
      const message = this.createMessageElement('ai', '')
      const contentEl = message.querySelector('.message-content')
      contentEl.appendChild(this.streamingTranscript)
      this.containerTarget.appendChild(message)
    }
    this.streamingTranscript.textContent += event.detail.delta
    this.scrollToBottom()
  }

  handleAITranscriptDone(event) {
    if (this.streamingTranscript.parentElement) {
      // Update the content of the existing message instead of creating a new one
      const contentEl = this.streamingTranscript.parentElement
      contentEl.textContent = event.detail.transcript
      this.streamingTranscript = document.createElement('div')
      this.streamingTranscript.classList.add('streaming-transcript')
    } else {
      // Fallback: create a new message if no streaming transcript exists
      const message = this.createMessageElement('ai', event.detail.transcript)
      this.containerTarget.appendChild(message)
    }
    this.scrollToBottom()
  }

  createMessageElement(role, content) {
    const template = document.getElementById('message-template')
    const messageEl = template.content.cloneNode(true).querySelector('.message')
    messageEl.classList.add(`message-${role}`)
    
    const contentEl = messageEl.querySelector('.message-content')
    contentEl.textContent = content
    
    return messageEl
  }

  scrollToBottom() {
    this.containerTarget.scrollTop = this.containerTarget.scrollHeight
  }
}
