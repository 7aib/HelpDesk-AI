"""
Forms for HelpDesk-AI accounts app.
"""

from typing import Any

from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

User = get_user_model()


class CustomSignupForm(SignupForm):
    """
    Custom signup form for HelpDesk-AI.
    
    Extends allauth's SignupForm with additional fields.
    """

    first_name = forms.CharField(
        max_length=30,
        required=False,
        help_text="Optional.",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First Name"}
        ),
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        help_text="Optional.",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Last Name"}
        ),
    )
    company = forms.CharField(
        max_length=100,
        required=False,
        help_text="Optional.",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Company"}
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "company"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the form with custom widgets."""
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Username"}
        )
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Email"}
        )
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Confirm Password"}
        )

    def save(self, request: Any) -> User:
        """
        Save the new user with additional fields.
        
        Args:
            request: The HTTP request.
            
        Returns:
            The created user instance.
        """
        user = super().save(request)
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.company = self.cleaned_data.get("company", "")
        user.save()
        return user


class UserForm(UserChangeForm):
    """
    Form for editing user profile.
    """

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "bio",
            "company",
            "job_title",
            "phone",
            "timezone",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "company": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "timezone": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the form."""
        super().__init__(*args, **kwargs)
        self.fields["password"].help_text = (
            "Raw passwords are not stored, so there is no way to see "
            "this user's password, but you can change the password "
            "using <a href='../password/'>this form</a>."
        )


class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile without password field.
    """

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "avatar",
            "bio",
            "company",
            "job_title",
            "phone",
            "timezone",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "company": forms.TextInput(attrs={"class": "form-control"}),
            "job_title": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "timezone": forms.Select(attrs={"class": "form-select"}),
        }
