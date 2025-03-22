import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ['submit', 'cancel', 'error', 'payment', 'paymentSpinner', 'submitSpinner', 'submitText', 'submitProcessing', 'cancelSpinner', 'cancelText', 'cancelProcessing']
    
    static classes = ['loading', 'error']
    static values = {
        publishableKey: String,
        clientSecret: String,
        email: String,
        csrfToken: String,
        updateUrl: String,
        returnUrl: String,
    }

    connect() {
        console.log('Connecting Payment Controller')
        this.stripe = Stripe(this.publishableKeyValue)
        this.elements = null
        this.paymentElement = null
        this.initialize_stripe()
    }

    async initialize_stripe() {
        console.log('Initializing Setup Payment Controller')
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

    async handleSubmit(event) {
        event.preventDefault()
        
        this.setLoading(true, 'submit')
        this.hideError()
        
        try {
            // First save our form data
            const form = event.target.closest('form')
            const formData = new FormData(form)

            const response = await fetch(this.updateUrlValue, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.csrfTokenValue
                }
            })

            const data = await response.json()
            
            if (!response.ok) {
                throw new Error(data.message || 'Failed to save settings')
            }

            // Then setup the card with Stripe (this will redirect)
            const { setupIntent, error } = await this.stripe.confirmSetup({
                elements: this.elements,
                confirmParams: {
                    return_url: window.location.origin + this.returnUrlValue
                }
            })

            if (error) {
                this.showError(error.message)
                this.setLoading(false, 'submit')
            }
            // No need to handle success - Stripe will redirect
            
        } catch (error) {
            this.showError('An unexpected error occurred. Please try again.')
            this.setLoading(false, 'submit')
        }
    }

    async handleCancel(event) {
        event.preventDefault()
        
        this.setLoading(true, 'cancel')
        
        try {
            //await this.updateTransactionStatus('cancel')
            window.location.href = this.returnUrlValue
        } catch (error) {
            console.error('Cancellation error:', error)
            this.setLoading(false, 'cancel')
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
        }
        if (button === 'cancel') {
            this.cancelSpinnerTarget.classList.toggle('d-none', !isLoading)
            this.cancelTextTarget.classList.toggle('d-none', isLoading)
            this.cancelProcessingTarget.classList.toggle('d-none', !isLoading)
        }
    }

    showError(message) {
        const errorDiv = this.errorTarget
        errorDiv.textContent = message
        errorDiv.classList.remove('d-none')
        errorDiv.classList.add(this.errorClass)
    }

    hideError() {
        const errorDiv = this.errorTarget
        errorDiv.textContent = ''
        errorDiv.classList.add('d-none')
        errorDiv.classList.remove(this.errorClass)
    }
}
