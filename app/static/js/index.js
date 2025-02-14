import { Application } from '@hotwired/stimulus'
import ThingController from '../../main/js/controllers/thing_controller'

console.log('Loading Stimulus application...')

let application = null

if (module.hot) {
    module.hot.accept()

    if (module.hot.data) {
        application = module.hot.data.application
    }

    module.hot.dispose(data => {
        data.application = application
    })
}

if (!application) {
    console.log('Initializing application...')
    try {
        application = Application.start()
        console.log('Application initialized successfully')

        // Register all controllers
     } catch (error) {
        console.error('Failed to initialize application:', error)
    }
}

console.log('Registering controllers...')
application.register('thing', ThingController)
console.log('Controllers registered successfully')


// Export the application instance for other modules to use
export { application }
