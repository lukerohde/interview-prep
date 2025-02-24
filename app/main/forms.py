from django import forms
from .models import Deck, Document

class DeckForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default values for hidden fields
        self.initial['deck_type'] = Deck.DeckType.STUDY
        self.initial['status'] = 'active'

    class Meta:
        model = Deck
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Enter a name for your deck'
            }),
        }
        labels = {
            'name': 'Deck Name',
        }
        help_texts = {
            'name': 'Enter a descriptive name for your deck',
        } 

class DocumentForm(forms.ModelForm):
    file = forms.FileField(required=False, widget=forms.FileInput(attrs={
        'class': 'form-control',
        'accept': '.pdf,.doc,.docx,.txt'
    }))

    class Meta:
        model = Document
        fields = ['name', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a name for this document'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter or paste the document content here'
            }),
        }
        labels = {
            'name': 'Document Name',
            'content': 'Content',
        }
        help_texts = {
            'name': 'A descriptive name for this document',
            'content': 'The text content that will be used for AI processing'
        }