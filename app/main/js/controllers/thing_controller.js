import { Controller } from "@hotwired/stimulus"
import { showToast } from '../../../static/js/utils/toast'

export default class extends Controller {
  static targets = ["form", "input", "fileInput", "previewContainer", "submit", "loading"]

  connect() {
  }

  disconnect() {
  }
}
