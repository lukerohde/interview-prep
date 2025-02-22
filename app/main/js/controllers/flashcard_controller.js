import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["previewContainer", "reviewContainer"]
  static values = { 
    apiUrl: String,
    nextReviewUrl: String,
    reviewUrlTemplate: String,
    deleteUrlTemplate: String,
    reviewSide: String,
    csrfToken: String
  }

  editModal = null
  currentEditCard = null

  connect() {
    this.prompts = {}
    this.editModal = new bootstrap.Modal(document.getElementById('editFlashcardModal'))
  }

  handlePromptsAvailable(event) {
    this.prompts = event.detail
  }

  interpolatePrompt(template, variables) {
    return template.replace(/\${(\w+)}/g, (match, key) => variables[key] || match)
  }

  async handleFunctionCall(event) {
    const { name, arguments: args } = event.detail

    switch (name) {
      case 'create_flashcard':
        await this.createFlashcard(args)
        break
      case 'start_review':
        this.fetchNextCard()
        break
      case 'assess_answer':
        await this.judgeCard(args)
        break
      case 'update_flashcard':
        await this.aiUpdateCard(args)
        break
      default:
        console.warn(`Unknown function call: ${name}`)
    }
  }

  async createFlashcard(args) {
    try {
      const response = await this.postWithToken(this.apiUrlValue, {
        front: args.front,
        back: args.back,
        tags: args.tags || []
      })
      const flashcard = await response.json()
      this.appendFlashcard(flashcard)
    } catch (error) {
      console.error('Error creating flashcard:', error)
    }
  }

  async judgeCard(args) {
    const card = this.reviewContainerTarget.querySelector('.flashcard')
    if (card) {
      await this.handleAIJudgement(args, card)
    } else {
      console.error('No card found to judge')
    }
  }

  async aiUpdateCard(args) {
    console.log('AI updating card:', args)
    const reviewCard = this.reviewContainerTarget.querySelector('.flashcard')
    if (!reviewCard) {
      console.error('No card found to update')
      return
    }

    try {
      // Find any existing preview card for this flashcard
      const previewCard = this.previewContainerTarget.querySelector(
        `.flashcard-preview[data-flashcard-id="${reviewCard.dataset.flashcardId}"]`
      )

      // Include review side in the request
      const params = new URLSearchParams({
        reviewSide: reviewCard.dataset.flashcardSide,
        show_both: 'false'
      })

      const response = await this.postWithToken(
        `${this.apiUrlValue}${reviewCard.dataset.flashcardId}/?${params}`,
        {
          front: args.front,
          back: args.back,
          tags: args.tags || []
        },
        'PUT'
      )

      if (!response.ok) throw new Error('Failed to update flashcard')

      const data = await response.json()
      
      // Update the preview card if it exists
      if (data.preview_html && previewCard) {
        this.updateCardContent(previewCard, data.preview_html)
      }
      
      // Update the review card
      if (data.review_html) {
        this.updateCardContent(reviewCard, data.review_html)
      }
    } catch (error) {
      console.error('Error updating flashcard:', error)
    }
  }

  async userUpdateCard(args) {
    if (!this.currentEditCard) {
      console.error('No card selected for update')
      return
    }

    try {
      const response = await this.postWithToken(
        this.apiUrlValue + this.currentEditCard.dataset.flashcardId + '/',
        {
          front: args.front,
          back: args.back,
          front_notes: args.front_notes,
          back_notes: args.back_notes,
          tags: args.tags || []
        },
        'PUT'
      )

      const data = await response.json()

      if (!response.ok) {
        // Format validation errors from DRF
        let errorMessage = 'Failed to update flashcard'
        if (data.error) {
          errorMessage = data.error
        } else if (data.detail) {
          errorMessage = data.detail
        } else if (typeof data === 'object') {
          // Handle DRF validation error format
          const errors = []
          for (const [field, fieldErrors] of Object.entries(data)) {
            if (Array.isArray(fieldErrors)) {
              errors.push(`${field}: ${fieldErrors.join(', ')}`)
            }
          }
          if (errors.length > 0) {
            errorMessage = errors.join('\n')
          }
        }

        const errorDiv = document.getElementById('editFlashcardError')
        if (errorDiv) {
          errorDiv.innerHTML = errorMessage.replace(/\n/g, '<br>')
          errorDiv.classList.remove('d-none')
        }
        throw new Error(errorMessage)
      }

      if (data.preview_html) {
        this.updateCardContent(this.currentEditCard, data.preview_html)
        this.editModal.hide()
      }
    } catch (error) {
      console.error('Error updating flashcard:', error)
      // Show error in modal if we haven't already
      if (!document.getElementById('editFlashcardError').textContent) {
        const errorDiv = document.getElementById('editFlashcardError')
        if (errorDiv) {
          errorDiv.textContent = error.message
          errorDiv.classList.remove('d-none')
        }
      }
    }
  }
  
  editCard(event) {
    const button = event.target.closest('button')
    if (!button) return

    const card = button.closest('.flashcard, .flashcard-preview')
    if (!card) return

    this.currentEditCard = card
    const frontTextarea = document.getElementById('editFlashcardFront')
    const backTextarea = document.getElementById('editFlashcardBack')
    const frontNotesTextarea = document.getElementById('editFlashcardFrontNotes')
    const backNotesTextarea = document.getElementById('editFlashcardBackNotes')
    const tagsInput = document.getElementById('editFlashcardTags')

    frontTextarea.value = card.dataset.flashcardFrontValue
    backTextarea.value = card.dataset.flashcardBackValue
    frontNotesTextarea.value = card.dataset.flashcardFrontNotesValue || ''
    backNotesTextarea.value = card.dataset.flashcardBackNotesValue || ''
    tagsInput.value = card.dataset.flashcardTagsValue || ''

    this.editModal.show()
  }

  saveEdit() {
    const frontTextarea = document.getElementById('editFlashcardFront')
    const backTextarea = document.getElementById('editFlashcardBack')
    const frontNotesTextarea = document.getElementById('editFlashcardFrontNotes')
    const backNotesTextarea = document.getElementById('editFlashcardBackNotes')
    const tagsInput = document.getElementById('editFlashcardTags')
    
    // Split tags by comma and trim whitespace
    const tags = tagsInput.value
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0)

    this.userUpdateCard({
      front: frontTextarea.value,
      back: backTextarea.value,
      front_notes: frontNotesTextarea.value,
      back_notes: backNotesTextarea.value,
      tags: tags
    })
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
    
    // Use prompt template
    const instruction = this.interpolatePrompt(this.prompts.play_full_card, { front, back })
    this.dispatch('add-context', { detail: instruction })
    this.dispatch('please-respond')
  }

  async fetchNextCard() {
    if (!this.hasReviewContainerTarget) {
      return
    }
    // Fetch the side we want to show, if its set
    const side = this.reviewSideValue || 'either'
    
    // Show the review area if it's hidden
    this.reviewContainerTarget.classList.remove('d-none')

    try {
      const response = await fetch(`${this.nextReviewUrlValue}?reviewSide=${side}`)
      if (!response.ok) throw new Error('Failed to fetch next review')
      
      const data = await response.json()
      this.reviewContainerTarget.innerHTML = data.html
      
      // If we got a card, automatically start the review
      if (data.html.includes('flashcard')) {
        this.reviewCard()
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
    const notes = side === 'front' ? card.dataset.flashcardFrontNotesValue : card.dataset.flashcardBackNotesValue
    
    // Use prompt template with interpolation
    const instruction = this.interpolatePrompt(this.prompts.review_card, {
      side,
      shownContent,
      front,
      back,
      notes
    })
    this.dispatch('add-context', { detail: instruction })
    this.dispatch('please-respond')
  }

  // Handle self-assessment from user clicking buttons
  async handleSelfAssessment(event) {
    const card = event.target.closest('.flashcard')
    const status = event.target.dataset.status
    
    if (!card || !status) return
    
    await this.postJudgement(card, status)
  }

  // Handle AI judgment of user's response
  async handleAIJudgement(args, card) {
    const status = args.status
    const notes = args.critique
    if (!card || !status) return

    // Convert AI judgment to backend status values
    const statusMap = {
      'correct': 'easy',
      'incorrect': 'forgot',
      'hard': 'hard',
      'excellent': 'easy',
      'needs_improvement': 'hard'
    }
    const backendStatus = statusMap[status] || status
    
    // Call the postJudgement method with the updated status and notes
    await this.postJudgement(card, backendStatus, notes)
  }

  // Helper to update a card's HTML content with new content from the server
  updateCardContent(existingCard, updatedPreview, moveToTop = true) {
    if (!existingCard || !updatedPreview) return

    // Create a temporary container to hold the new HTML
    const temp = document.createElement('div')
    temp.innerHTML = updatedPreview
    const updatedCard = temp.firstElementChild

    // Determine if this is a preview or review card
    const isPreviewCard = existingCard.classList.contains('flashcard-preview')

    if (isPreviewCard && this.hasPreviewContainerTarget) {
      // Handle preview card update
      if (moveToTop) {
        this.previewContainerTarget.insertBefore(
          updatedCard,
          this.previewContainerTarget.firstChild
        )
      } else {
        existingCard.parentNode.insertBefore(updatedCard, existingCard)
      }
    } else {
      // Handle review card update - always replace in place
      existingCard.parentNode.insertBefore(updatedCard, existingCard)
    }
    existingCard.remove()
  }

  // Common method to post judgment to backend
  async postJudgement(card, status, notes = null) {
    console.log('Posting judgment:', { status, notes, cardData: card?.dataset })
    console.log(this.reviewUrlTemplateValue)
    try {
      const response = await this.postWithToken(
        this.reviewUrlTemplateValue.replace(':id', card.dataset.flashcardId),
        {
          status: status,
          side: card.dataset.flashcardSide,
          notes: notes
        }
      )
      
      if (!response.ok) throw new Error('Failed to update review')
      
      const data = await response.json()

      // Update the preview of the judged card and move it to the top
      if (data.updated_preview) {
        const existingCard = this.previewContainerTarget.querySelector(
          `.flashcard-preview[data-flashcard-id="${data.updated_card_id}"]`
        )
        this.updateCardContent(existingCard, data.updated_preview)
      }

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
        this.deleteUrlTemplateValue.replace(':id', cardId),
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
    if (!this.csrfTokenValue) {
      throw new Error('CSRF token not found')
    }

    return fetch(url, {
      method: method,
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.csrfTokenValue,
      },
      body: JSON.stringify(data)
    })
  }
}
