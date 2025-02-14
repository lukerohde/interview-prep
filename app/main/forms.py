from django import forms
from .models import Application

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['name', 'status', 'resume', 'job_description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Enter the position or company name'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'resume': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Paste your resume or CV content here'
            }),
            'job_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Paste the full job description here'
            }),
        }
        labels = {
            'name': 'Position/Company',
            'status': 'Application Status',
            'resume': 'Resume/CV',
            'job_description': 'Job Description'
        }
        help_texts = {
            'name': 'Enter the name of the position or company you are applying to',
            'status': 'Current status of your application',
            'resume': 'Your resume or CV content that will be used for this application',
            'job_description': 'The full job description from the posting'
        } 