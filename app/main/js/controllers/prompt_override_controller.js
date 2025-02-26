import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ["textarea", "saveIndicator"]
    static values = {
        saveUrl: String
    }

    connect() {
        this.saveTimeout = null
        this.saveInProgress = false
    }

    // Show default value when focusing empty textarea
    focusTextarea(event) {
        const textarea = event.target
        if (!textarea.value) {
            textarea.value = textarea.placeholder
        }
    }

    // Auto-save on input after delay
    inputTextarea(event) {
        clearTimeout(this.saveTimeout)
        this.showSaveIndicator(event.target)
        this.saveTimeout = setTimeout(() => this.savePrompt(event.target), 1000)
    }

    // Save immediately on blur if changes pending
    blurTextarea(event) {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout)
            this.savePrompt(event.target)
        }
    }

    async savePrompt(textarea) {
        if (this.saveInProgress) return
        
        this.saveInProgress = true
        const key = textarea.dataset.key
        const value = textarea.value.trim()

        try {
            const response = await fetch(this.saveUrlValue, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: `key=${encodeURIComponent(key)}&value=${encodeURIComponent(value)}`
            })

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }
        } catch (error) {
            console.error('Error saving prompt:', error)
            // Could add error handling UI here
        } finally {
            this.saveInProgress = false
            this.hideSaveIndicator(textarea)
        }
    }

    showSaveIndicator(textarea) {
        const indicator = textarea.closest('.card-body').querySelector('.save-indicator')
        indicator.style.display = 'block'
    }

    hideSaveIndicator(textarea) {
        const indicator = textarea.closest('.card-body').querySelector('.save-indicator')
        indicator.style.display = 'none'
    }

    getCookie(name) {
        let cookieValue = null
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';')
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim()
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
                    break
                }
            }
        }
        return cookieValue
    }
}
