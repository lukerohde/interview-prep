from django import forms
from .models import Deck, Document

class DeckForm(forms.ModelForm):
    class Meta:
        model = Deck
        fields = ['name', 'deck_type', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Enter a name for your deck'
            }),
            'deck_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'name': 'Deck Name',
            'deck_type': 'Type',
            'status': 'Status'
        }
        help_texts = {
            'name': 'Enter a descriptive name for your deck',
            'deck_type': 'Choose the type of content this deck will contain',
            'status': 'Current status of your deck'
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