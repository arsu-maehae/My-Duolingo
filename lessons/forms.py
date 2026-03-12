from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'ชื่อผู้ใช้'})
        self.fields['username'].help_text = ''
        self.fields['password1'].widget.attrs.update({'placeholder': 'รหัสผ่าน'})
        self.fields['password1'].help_text = ''
        self.fields['password2'].widget.attrs.update({'placeholder': 'ยืนยันรหัสผ่าน'})
        self.fields['password2'].help_text = ''


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'ชื่อผู้ใช้'})
        self.fields['password'].widget.attrs.update({'placeholder': 'รหัสผ่าน'})
