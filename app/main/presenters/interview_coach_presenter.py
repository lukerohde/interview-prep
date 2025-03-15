class InterviewCoachPresenter:
  def __init__(self, tutor):
    self.tutor = tutor

  @property
  def should_render_document_form(self):
    return True
