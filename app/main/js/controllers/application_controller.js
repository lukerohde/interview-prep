import { Controller } from "@hotwired/stimulus"
import * as pdfjsLib from "pdfjs-dist/build/pdf"
import mammoth from "mammoth"
import showdown from "showdown"

import('pdfjs-dist/build/pdf.worker.min.mjs')


export default class extends Controller {
  static targets = ["resumeFileInput", "uploadLabel", "output", "resumeMessage", "resumeSpinner"]
  static values = {
    aiResponseUrl: String,
  }
  converter = null
  
  
  connect() {
    this.converter = new showdown.Converter()
    this.listenInputEvents()
  }

  listenInputEvents() {
    this.resumeFileInputTarget.addEventListener("change", () => this.handleUpload())
  }
  
  handleUpload() {
    console.log("Handling upload...")
    this.clearMessages()
    
    const file = this.resumeFileInputTarget.files[0]
    if (!file) {
      return this.showError("Please select a file.")
    }
    
    const fileType = file.name.split('.').pop().toLowerCase()
    this.showSpinner()
    this.showMessage("Uploading the file...")
    
    if (fileType === "pdf") {
      this.extractTextFromPDF(file)
    } else if (fileType === "docx") {
      this.extractTextFromDocx(file)
    } else if (fileType === "txt") {
      this.extractTextFromTxt(file)
    } else {
      this.hideSpinner()
      this.showError("Unsupported file type. Please upload a PDF, DOCX, or TXT file.")
    }
  }
  
  async extractTextFromPDF(file) {
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
        
        this.sendResumeToAI(extractedText)
      }
      
      reader.readAsArrayBuffer(file)
    } catch (error) {
      this.showError("Error processing the PDF file.")
    }
  }
  
  async extractTextFromDocx(file) {
    try {
      const reader = new FileReader()
      reader.onload = async (event) => {
        const extractedText = await mammoth.extractRawText({ arrayBuffer: event.target.result })
        .then(result => result.value)
        .catch(error => { throw new Error("Error extracting text from DOCX") })
        
        this.sendResumeToAI(extractedText)
      }
      
      reader.readAsArrayBuffer(file)
    } catch (error) {
      this.showError("Error processing the DOCX file.")
    }
  }
  
  async extractTextFromTxt(file) {
    try {
      const reader = new FileReader()
      reader.onload = (event) => {
        const extractedText = event.target.result
        this.sendResumeToAI(extractedText)
      }
      
      reader.readAsText(file)
    } catch (error) {
      this.showError("Error processing the TXT file.")
    }
  }

  sendResumeToAI(resumeText) {
    this.showMessage("Processing the resume, this can take a while, please wait...")
    fetch(this.aiResponseUrlValue, {
      method: 'POST',
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
      },
      body: JSON.stringify({
        developer_prompt: "Parse the following resume to a markdown-formatted text representation with relevant sections grouped together. Remove emain and phone number.",
        user_prompt: resumeText
      })
    }).then(response => response.json())
    .then(data => {
      this.displayResumeResponse(data.response)
    })
    .catch(error => {
        throw new Error(error)
    }).finally(() => {
      this.hideSpinner()
      this.clearMessages()
    })
  }
  
  displayResumeResponse(text) {
    this.outputTarget.textContent = text
  }
  
  showMessage(message) {
    this.resumeMessageTarget.textContent = message
    this.resumeMessageTarget.style.display = "block"
  }
  
  clearMessages() {
    this.resumeMessageTarget.textContent = ""
    this.resumeMessageTarget.style.display = "none"
  }

  showSpinner() {
    this.resumeSpinnerTarget.style.display = 'inline-block'
  }

  hideSpinner() {
    this.resumeSpinnerTarget.style.display = 'none'
  }
}
