import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ['submit', 'cancel', 'error', 'payment', 'paymentSpinner', 'submitSpinner', 'submitText', 'submitProcessing', 'cancelSpinner', 'cancelText', 'cancelProcessing']
    static classes = ['loading', 'error']
    static values = {
        publishableKey: String,
        clientSecret: String,
        intentId: String,
        email: String,
        updateUrl: String,
        returnUrl: String,
        csrfToken: String
    }

    connect() {
        console.log('Connecting Recharge Controller')
        this.stripe = Stripe(this.publishableKeyValue)
        this.elements = null
        this.paymentElement = null
        this.initialize_stripe()
    }

    async initialize_stripe() {
        console.log('Initializing Recharge Controller')
        const appearance = {
            theme: 'stripe',
        }

        this.elements = this.stripe.elements({
            clientSecret: this.clientSecretValue,
            appearance,
            loader: 'auto',
        })

        this.paymentElement = this.elements.create('payment', {
            layout: { type: 'tabs' },
            defaultValues: {
                billingDetails: {
                    email: this.emailValue,
                }
            },
            paymentMethodOrder: ['card'],  // Only allow card payments
            wallets: { applePay: 'never', googlePay: 'never' }  // Disable digital wallets
        })
        
        await this.paymentElement.mount(this.paymentTarget)
        this.paymentSpinnerTarget.classList.add('d-none')
        this.paymentTarget.classList.remove('d-none')
    }

    async updateTransactionStatus(action) {
        try {
            const response = await fetch(this.updateUrlValue, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.csrfTokenValue
                },
                body: `intent_id=${this.intentIdValue}&action=${action}`
            })
            
            const data = await response.json()
            
            if (!response.ok) {
                throw new Error(data.message || 'Failed to update transaction status')
            }
            
            return data
        } catch (error) {
            if (error instanceof TypeError && !window.navigator.onLine) {
                throw new Error('Network connection lost. Please check your internet connection and try again.')
            }
            console.error('Error updating transaction status:', error)
            throw error
        }
    }

    async handleSubmit(event) {
        event.preventDefault()
        
        this.setLoading(true)
        this.hideError()
        
        try {
            // Update status to processing
            await this.updateTransactionStatus('process')
            
            const { error } = await this.stripe.confirmPayment({
                elements: this.elements,
                confirmParams: {
                    return_url: window.location.origin + this.returnUrlValue
                }
            })

            if (error) {
                this.showError(error.message)
                this.setLoading(false)
            }
        } catch (error) {
            console.error('Payment error:', error)
            this.showError('An unexpected error occurred')
            this.setLoading(false)
        }
    }

    async handleCancel(event) {
        event.preventDefault()
        
        this.setLoading(true, 'cancel')
        
        try {
            await this.updateTransactionStatus('cancel')
            window.location.href = this.returnUrlValue
        } catch (error) {
            console.error('Cancellation error:', error)
            this.setLoading(false)
            this.showError('Failed to cancel payment')
        }
    }

    setLoading(isLoading, button = 'submit') {
        this.submitTarget.disabled = isLoading
        this.cancelTarget.disabled = isLoading

        if (button === 'submit') {
            this.submitSpinnerTarget.classList.toggle('d-none', !isLoading)
            this.submitTextTarget.classList.toggle('d-none', isLoading)
            this.submitProcessingTarget.classList.toggle('d-none', !isLoading)
        } else {
            this.cancelSpinnerTarget.classList.toggle('d-none', !isLoading)
            this.cancelTextTarget.classList.toggle('d-none', isLoading)
            this.cancelProcessingTarget.classList.toggle('d-none', !isLoading)
        }
    }

    showError(message) {
        this.errorTarget.textContent = message
        this.errorTarget.classList.add(this.errorClass)
    }

    hideError() {
        this.errorTarget.textContent = ''
        this.errorTarget.classList.remove(this.errorClass)
    }


}
