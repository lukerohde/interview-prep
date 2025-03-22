import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ['submit', 'error', 'payment', 'paymentSpinner', 'submitSpinner', 'submitText']
    static classes = ['loading', 'error']
    static values = {
        publishableKey: String,
        clientSecret: String,
        email: String,
        returnUrl: { type: String, default: '/billing/settings/' }
    }

    connect() {
        this.stripe = Stripe(this.publishableKeyValue)
        this.elements = null
        this.paymentElement = null
        this.initialize()
    }

    async initialize() {
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
        
        this.setLoading(true)
        this.hideError()
        
        try {
            const { setupIntent, error } = await this.stripe.confirmSetup({
                elements: this.elements,
                confirmParams: {
                    return_url: window.location.origin + this.returnUrlValue
                }
            })

            if (error) {
                this.showError(error.message)
                this.setLoading(false)
            }
            // No need to update status - webhook will handle it
        } catch (error) {
            this.showError('An unexpected error occurred. Please try again.')
            this.setLoading(false)
        }
    }

    setLoading(isLoading) {
        const submitButton = this.submitTarget
        const submitSpinner = this.submitSpinnerTarget
        const submitText = this.submitTextTarget

        if (isLoading) {
            submitButton.disabled = true
            submitButton.classList.add(this.loadingClass)
            submitSpinner.classList.remove('d-none')
            submitText.textContent = 'Setting up...'
        } else {
            submitButton.disabled = false
            submitButton.classList.remove(this.loadingClass)
            submitSpinner.classList.add('d-none')
            submitText.textContent = 'Save Card'
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
