from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Address, CustomerProfile


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username',
            'required': True,
            'class': 'alesi-control',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'required': True,
            'class': 'alesi-control',
            'autocomplete': 'current-password',
        })
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'you@example.com',
            'required': True,
            'class': 'alesi-control',
            'autocomplete': 'email',
        }),
    )
    phone = forms.CharField(
        required=False,
        max_length=32,
        widget=forms.TextInput(attrs={
            'placeholder': 'Optional phone number',
            'class': 'alesi-control',
            'autocomplete': 'tel',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Choose a username',
            'class': 'alesi-control',
            'autocomplete': 'username',
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Create a password',
            'class': 'alesi-control',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm your password',
            'class': 'alesi-control',
            'autocomplete': 'new-password',
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.save()
        return user


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            'full_name',
            'phone',
            'landmark',
            'city',
            'address_line',
            'address_type',
            'is_default',
        )
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'billing-address-name form-control',
                'placeholder': 'Full name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mobile number',
            }),
            'landmark': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Landmark',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Town/City',
            }),
            'address_line': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address',
            }),
            'address_type': forms.Select(attrs={'class': 'form-control option-w3ls'}),
        }
