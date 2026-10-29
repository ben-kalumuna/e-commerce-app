from django import forms

from apps.pages.models import ContactMessage, NewsletterSubscriber


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ('name', 'email', 'telephone', 'subject', 'message')
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Your full name',
                'class': 'alesi-control',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'you@example.com',
                'class': 'alesi-control',
            }),
            'telephone': forms.TextInput(attrs={
                'placeholder': 'Phone (optional)',
                'class': 'alesi-control',
            }),
            'subject': forms.TextInput(attrs={
                'placeholder': 'What is this about?',
                'class': 'alesi-control',
            }),
            'message': forms.Textarea(attrs={
                'placeholder': 'Write your message here...',
                'rows': 6,
                'class': 'alesi-control',
            }),
        }


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ('email',)
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
        }
