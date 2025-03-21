# Interview Prep

A voice-chat web application to assist with interview preparation.

Features:
- Upload you resume and the position description
- Voice chat with an AI interviewer to draft STAR format answers for likely questions
- Get hired and profit!

## Target state tech architecture
- Uses OpenAI RealTime API for voice communication
- Server-side rendering with Django templates
- StimulusJS for interactive components
    - Voice Chat Controller
    - Flash Card Controller
    - Transcription Controller
- Asset bundling with NPM and Parcel
- Bootstrap 5 for responsive layou

## Setup

Run the setup script to configure your project name and `.env` plus `docker-compose.override.yml` for local development.

```
./setup
```
```

Start developing

```
make run
```

For hot asset reloading, in another terminal run

```
make dev
```

Sign in 
1. http://localhost:3000
2. your username and password are in .env

To see how to run other stuff

```
make help
```

## For headed Playwright testing on macOS:

1. Install XQuartz:

   ```
   brew install --cask xquartz
   ```
   
2. follow [x11 on docker](https://gist.github.com/cschiewek/246a244ba23da8b9f0e7b11a68bf3285)


3. Run headed Playwright tests:
   ```
   make test-headed
   ```



## Deployment Instructions

For more detailed instructions, please refer to the following README files:

- [Deploy to Render](deploy-render/README.md)

# Stripe Payment Integration

Sign into stripe and setup your account

Set your Stripe keys in the .env file

STRIPE_PUBLISHABLE_KEY=xxx
STRIPE_API_KEY=xxx
STRIPE_WEBHOOK_SECRET=xxx

You get the webhook secret from https://dashboard.stripe.com/test/workbench/webhooks

Setup a webhook with the following events:
* payment_intent.succeeded
* payment_intent.payment_failed

On https://your-domain/billing/api/stripe-webhook/

Use `ngrok http 3000` for local development
