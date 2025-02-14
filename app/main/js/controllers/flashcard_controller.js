import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["previewContainer", "reviewContainer"]

  connect() {
    this.registerTools()
  }

  registerTools() {
    // Flashcard creation tool
    const flashcardTool = {
      type: 'function',
      name: 'create_flashcard',
      description: 'Create a new flashcard with the specified front and back content.',
      parameters: {
        type: 'object',
        properties: {
          front: {
            type: 'string',
            description: 'The english content for the front of the flashcard'
          },
          back: {
            type: 'string',
            description: 'The foreign language content for the back of the flashcard'
          },
          tags: {
            type: 'array',
            items: {
              type: 'string'
            },
            description: 'Optional tags to categorize the flashcard'
          }
        },
        required: ['front', 'back', 'tags']
      }
    }

    // Review start tool
    const startReviewTool = {
      type: 'function',
      name: 'start_review',
      description: 'When the user asks you to start, run this tool.',
      parameters: {
        type: 'object',
        properties: {}
      }
    }

    // AI judgment tool
    const judgeCardTool = {
      type: 'function',
      name: 'judge_card',
      description: 'Judge the current flashcard based on correctness.  If the user says next card please, that is an invitation to judge their understanding and move on.',
      parameters: {
        type: 'object',
        properties: {
          status: {
            type: 'string',
            description: 'The judgment status: correct, incorrect, or hard',
            enum: ['correct', 'incorrect', 'hard']
          }
        },
        required: ['status']
      }
    }

    this.dispatch('register-tool', { detail: flashcardTool })
    this.dispatch('register-tool', { detail: startReviewTool })
    this.dispatch('register-tool', { detail: judgeCardTool })
  }

  async handleFunctionCall(event) {
    const { name, arguments: args } = event.detail

    if (name === 'create_flashcard') {
      try {
        const response = await this.postWithToken('/api/flashcards/', {
          front: args.front,
          back: args.back,
          tags: args.tags || []
        })

        const flashcard = await response.json()
        this.appendFlashcard(flashcard)
      } catch (error) {
        console.error('Error creating flashcard:', error)
      }
    } else if (name === 'start_review') {
      this.fetchNextCard()
    } else if (name === 'judge_card') {
      const card = this.reviewContainerTarget.querySelector('.flashcard')
      if (card) {
        await this.handleAIJudgement(args.status, card)
      } else {
        console.error('No card found to judge')
      }
    }
  }

  appendFlashcard(flashcard) {
    if (flashcard && this.hasPreviewContainerTarget) {
      // Prepend the new flashcards to the preview container
      this.previewContainerTarget.insertAdjacentHTML('afterbegin', flashcard.html);
    }
  }

  async playFullCard(event) {
    const card = event.target.closest('.flashcard')
    if (!card) return

    const front = card.dataset.flashcardFrontValue
    const back = card.dataset.flashcardBackValue
    
    // Instruction to read both sides
    const instruction = `Please read both sides of this flashcard. Front: "${front}". Back: "${back}".`
    this.dispatch('add-context', { detail: instruction })
    this.dispatch('please-respond')
  }

  async fetchNextCard() {
    if (!this.hasReviewContainerTarget) {
      return
    }

    // Show the review area if it's hidden
    this.reviewContainerTarget.classList.remove('d-none')

    try {
      const response = await fetch('/api/flashcards/next_review/')
      if (!response.ok) throw new Error('Failed to fetch next review')
      
      const data = await response.json()
      this.reviewContainerTarget.innerHTML = data.html
      
      // If we got a card, automatically start the review
      if (data.html.includes('flashcard')) {
        this.reviewCard()
      } else {
      }
    } catch (error) {
      console.error('Error loading next review:', error)
    }
  }

  async reviewCard() {
    // Get current card data from the review container
    const card = this.reviewContainerTarget.querySelector('.flashcard')
    if (!card) {
      alert('No card to review')
      return
    }
    
    const side = card.dataset.flashcardSide
    const front = card.dataset.flashcardFrontValue
    const back = card.dataset.flashcardBackValue
    const shownContent = side === 'front' ? front : back
    
    // Instruction to read the card and assess response
    const instruction = `We are reviewing flashcards.
    Currently showing the ${side}: "${shownContent}"
    The complete card content is:
    Front: "${front}"
    Back: "${back}"
    Please just read the ${side} to the user in either english or japanese as shown, nothing more or less. After they respond, assess their answer against the of the hidden side of the card, then use judge_card to formalise feedback.:
    - 'correct': if they demonstrate clear understanding
    - 'incorrect': if they show significant misunderstanding
    - 'hard': if they got it mostly right but struggled or took time
    Do not reveal the correct answer unless they ask for it. Provide hints and corrections as needed.
    
    Here's an example dialog demonstrating your helpful behaviour:
    
    Assistant: パスポートを見せてください
    User: Please show me your passport
    <assistant uses judge_card(correct)>
    
    Assistant: I have a reservation
    User: よよくがあります
    Assistant: Not quiet, reservation is よやく
    User: よやくがあります
    <assistant uses judge_card(hard)>

    Assistant: Room
    User: I forgot
    Assistant: The word for room is へや
    <assistant uses judge_card(forgot)>

    Assistant: 足
    User: Blue
    Assistant: あし means foot or leg depending on context
    User:  Okay あし means foot of leg
    <assistant uses judge_card(incorrect)>

    Assistant: 新しい
    User: Sorry I didn't catch that
    Assistant: 新しい
    User:  New
    <assistant uses judge_card(correct)>
    
    Assistant: Elbow
    User: モンキー
    <assistant uses judge_card(correct)>
    `
    
    this.dispatch('add-context', { detail: instruction })
    this.dispatch('please-respond')
  }

  // Handle self-assessment from user clicking buttons
  async handleSelfAssessment(event) {
    const status = event.target.dataset.status
    const card = event.target.closest('.flashcard')
    if (!card || !status) return
    
    await this.postJudgement(card, status)
  }

  // Handle AI judgment of user's response
  async handleAIJudgement(status, card) {
    if (!card || !status) return

    // Convert AI judgment to backend status values
    const statusMap = {
      'correct': 'easy',
      'incorrect': 'forgot',
      'hard': 'hard'
    }
    const backendStatus = statusMap[status] || status
    
    await this.postJudgement(card, backendStatus)
  }

  // Common method to post judgment to backend
  async postJudgement(card, status) {
    console.log('Posting judgment:', { status, cardData: card?.dataset })
    
    // Play appropriate sound based on status
    const soundMap = {
      'easy': new Audio('/static/sounds/correct.mp3'),  // nice ting
      'forgot': new Audio('/static/sounds/incorrect.mp3'),  // bingbong
      'hard': new Audio('/static/sounds/hard.mp3')  // boop
    }
    
    const sound = soundMap[status]
    if (sound) {
      sound.play().catch(error => console.error('Error playing sound:', error))
    }

    try {
      const response = await this.postWithToken(
        `/api/flashcards/${card.dataset.flashcardId}/review/`,
        {
          status: status,
          side: card.dataset.flashcardSide
        }
      )
      
      if (!response.ok) throw new Error('Failed to update review')
      
      const data = await response.json()

      // Update the preview of the judged card and move it to the top
      if (this.hasPreviewContainerTarget && data.updated_preview) {
        const existingCard = this.previewContainerTarget.querySelector(
          `.flashcard-preview[data-flashcard-id="${data.updated_card_id}"]`
        )
        if (existingCard) {
          // Create a temporary container to hold the new HTML
          const temp = document.createElement('div')
          temp.innerHTML = data.updated_preview
          const updatedCard = temp.firstElementChild

          // Replace the existing card with the updated one and move it to the top
          this.previewContainerTarget.insertBefore(
            updatedCard,
            this.previewContainerTarget.firstChild
          )
          existingCard.remove()
        }
      }

      // Fetch the next card for review
      await this.fetchNextCard()
    } catch (error) {
      console.error('Error updating review:', error)
    }
  }

  async deleteCard(event) {
    const card = event.currentTarget.closest('.flashcard-preview')
    const cardId = card.dataset.flashcardId

    try {
      const response = await this.postWithToken(
        `/api/flashcards/${cardId}/`,
        {},
        'DELETE'
      )

      if (!response.ok) throw new Error('Failed to delete flashcard')

      // Animate the card sliding up and then remove it
      card.style.transition = 'all 0.3s ease-out'
      card.style.maxHeight = card.offsetHeight + 'px'
      
      // Start animation in the next frame
      requestAnimationFrame(() => {
        card.style.maxHeight = '0'
        card.style.opacity = '0'
        card.style.marginBottom = '0'

        // Remove the element after animation completes
        setTimeout(() => {
          card.remove()
        }, 300)
      })
    } catch (error) {
      console.error('Error deleting flashcard:', error)
    }
  }

  async postWithToken(url, data, method = 'POST') {
    const csrfToken = document.cookie.split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];

    if (!csrfToken) {
      throw new Error('CSRF token not found')
    }

    return fetch(url, {
      method: method,
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(data)
    })
  }
}
