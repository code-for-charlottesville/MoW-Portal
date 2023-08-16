from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import ModelForm

from models.models import Volunteer


class DateInput(forms.DateInput):
    input_type = "date"


class SignUpForm(UserCreationForm):

    # gets rid of the password fields on form
    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields["password1"].widget = forms.HiddenInput()
        self.fields["password2"].widget = forms.HiddenInput()
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        self.fields["email"].required = True

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "is_staff",
        )

    def clean(self):
        super().clean()
        data = self.cleaned_data
        # ensure that username is incase sensitive and unique
        cleaned_username = data.get("username")
        if cleaned_username is None or cleaned_username == "":
            raise forms.ValidationError("Username not valid.")

        try:
            get_user_model()._default_manager.get(username__iexact=cleaned_username)
        except get_user_model().DoesNotExist:
            data["username"] = cleaned_username.lower()
            return data
        raise forms.ValidationError("This username already exists.")


class LoginForm(forms.Form):
    username = forms.CharField(max_length=255, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        super().clean()
        username = self.cleaned_data.get("username").lower()
        password = self.cleaned_data.get("password")
        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            raise forms.ValidationError(
                "Sorry, that login was invalid. Please try again.")
        return self.cleaned_data

    def login(self, request):
        username = self.cleaned_data.get("username").lower()
        password = self.cleaned_data.get("password")
        user = authenticate(username=username, password=password)
        return user


class VolunteerForm(ModelForm):
    class Meta:
        model = Volunteer
        fields = [
            "organization",
            "home_phone",
            "cell_phone",
            "work_phone",
            "birth_date",
            "join_date",
            "notes",
        ]
        widgets = {
            "birth_date": DateInput(format=("%Y-%m-%d")),
            "join_date": DateInput(format=("%Y-%m-%d")),
        }
