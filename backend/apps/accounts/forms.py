from django import forms
from .models import CustomUser

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ['username','email','phone']

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        confirm = self.cleaned_data.get('password_confirm')
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords don't match")
        return confirm
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'PATIENT'
        if commit:
            user.save()
        return user    
    