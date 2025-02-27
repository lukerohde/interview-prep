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
        fields = ['name', 'description', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Enter a name for your deck'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter a description for your deck'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Enter or paste the content to generate flashcards from'
            }),
        }
        labels = {
            'name': 'Deck Name',
            'description': 'Description',
            'content': 'Content',
        }
        help_texts = {
            'name': 'Enter a descriptive name for your deck',
            'description': 'Enter a description for your deck',
            'content': 'Enter the text content that will be used to generate flashcards',
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

class InvitationForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address to invite'
        }),
        help_text='Enter the email address of the person you want to invite'
    )