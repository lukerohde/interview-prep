import { Controller } from "@hotwired/stimulus"
import * as pdfjsLib from "pdfjs-dist/build/pdf"
import mammoth from "mammoth"
import showdown from "showdown"

import('pdfjs-dist/build/pdf.worker.min.mjs')

export default class extends Controller {
  static targets = ["documentFileInput", "uploadLabel", "output", "documentMessage", "documentSpinner", "documentList"]
  static values = {
    aiResponseUrl: String,
    deckId: String,
  }
  converter = null

  connect() {
    this.converter = new showdown.Converter()
    console.log("Connected to the document controller.")
    this.listenInputEvents()
  }

  listenInputEvents() {
    this.documentFileInputTarget.addEventListener("change", () => this.handleUpload())
  }

  handleUpload() {
    console.log("Handling upload...")
    this.clearMessages()

    const files = this.documentFileInputTarget.files
    if (files.length === 0) {
      return this.showError("Please select files.")
    }

    this.showSpinner()
    this.showMessage("Uploading the files...")

    Array.from(files).forEach((file, index) => {
      const fileType = file.name.split('.').pop().toLowerCase()
      const fileName = file.name
      const uniqueId = `document_${index}`

      const listItem = document.createElement("div")
      listItem.classList.add("mb-4")
      listItem.innerHTML = `
        <label class="form-label fw-bold">Document: ${fileName}</label>
        <textarea name="${uniqueId}_content" class="form-control" rows="10" placeholder="Processing ${fileName}..."></textarea>
        <input type="hidden" name="${uniqueId}_name" value="${fileName}">
      `
      this.documentListTarget.appendChild(listItem)

      if (fileType === "pdf") {
        this.extractTextFromPDF(file, listItem.querySelector("textarea"))
      } else if (fileType === "docx") {
        this.extractTextFromDocx(file, listItem.querySelector("textarea"))
      } else if (fileType === "txt") {
        this.extractTextFromTxt(file, listItem.querySelector("textarea"))
      } else {
        this.hideSpinner()
        this.showError("Unsupported file type. Please upload a PDF, DOCX, or TXT file.")
      }
    })
  }

  async extractTextFromPDF(file, textarea) {
    try {
      const reader = new FileReader()
      reader.onload = async (event) => {
        const typedArray = new Uint8Array(event.target.result)
        const pdf = await pdfjsLib.getDocument({ data: typedArray }).promise

        let extractedText = ""
        for (let i = 1; i <= pdf.numPages; i++) {
          const page = await pdf.getPage(i)
          const textContent = await page.getTextContent()
          extractedText += textContent.items.map(item => item.str).join(" ") + "\n"
        }

        this.sendDocumentToAI(extractedText, file.name, textarea)
      }

      reader.readAsArrayBuffer(file)
    } catch (error) {
      this.showError("Error processing the PDF file.")
    }
  }

  async extractTextFromDocx(file, textarea) {
    try {
      const reader = new FileReader()
      reader.onload = async (event) => {
        const extractedText = await mammoth.extractRawText({ arrayBuffer: event.target.result })
        .then(result => result.value)
        .catch(error => { throw new Error("Error extracting text from DOCX") })

        this.sendDocumentToAI(extractedText, file.name, textarea)
      }

      reader.readAsArrayBuffer(file)
    } catch (error) {
      this.showError("Error processing the DOCX file.")
    }
  }

  async extractTextFromTxt(file, textarea) {
    try {
      const reader = new FileReader()
      reader.onload = (event) => {
        const extractedText = event.target.result
        this.sendDocumentToAI(extractedText, file.name, textarea)
      }

      reader.readAsText(file)
    } catch (error) {
      this.showError("Error processing the TXT file.")
    }
  }

  sendDocumentToAI(documentText, fileName, textarea) {
    this.showMessage("Processing the document, this can take a while, please wait...")
    fetch(this.aiResponseUrlValue, {
      method: 'POST',
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
      },
      body: JSON.stringify({
        developer_prompt: "Parse the following document to a markdown-formatted text representation with relevant sections grouped together. Remove email and phone number.",
        user_prompt: documentText
      })
    }).then(response => response.json())
    .then(data => {
      this.displayDocumentResponse(data.response, fileName, textarea)
    })
    .catch(error => {
        throw new Error(error)
    }).finally(() => {
      this.hideSpinner()
      this.clearMessages()
    })
  }

  displayDocumentResponse(text, fileName, textarea) {
    textarea.value = text
  }

  showMessage(message) {
    this.documentMessageTarget.textContent = message
    this.documentMessageTarget.style.display = "block"
  }

  clearMessages() {
    this.documentMessageTarget.textContent = ""
    this.documentMessageTarget.style.display = "none"
  }

  showSpinner() {
    this.documentSpinnerTarget.style.display = 'inline-block'
  }

  hideSpinner() {
    this.documentSpinnerTarget.style.display = 'none'
  }

  showError(message) {
    this.showMessage(message)
    this.hideSpinner()
  }

  deleteDocument(event) {
    console.log('Delete document triggered', event);
    const documentId = event.target.getAttribute('data-document-id')
    if (confirm('Are you sure you want to delete this document?')) {
      const url = `/documents/${this.deckIdValue}/documents/${documentId}/delete/`
      fetch(url, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': this.getCookie('csrftoken'),
          'Content-Type': 'application/json'
        }
      })
      .then(response => {
        if (response.ok) {
          document.getElementById(`document-${documentId}`).remove()
        } else {
          alert('Failed to delete the document.')
        }
      })
      .catch(error => {
        console.error('Error:', error)
        alert('Failed to delete the document.')
      })
    }
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
