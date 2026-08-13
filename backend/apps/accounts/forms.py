from django import forms
from .models import CustomUser

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)
    full_name = forms.CharField(max_length=100)

    class Meta:
        model = CustomUser
        fields = ['full_name','username','email','phone']

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

class WalkInPatientForm(RegisterForm):
    """Reception registering a walk-in. Same rules as self-registeration,
    plus the desk details a patient gives at the counter."""

    class Meta(RegisterForm.Meta):
        fields = ['full_name','username', 'email', 'phone', 'age', 'gender', 'blood_group', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('phone', 'age', 'gender'):
            self.fields[name].required = True

class ProfileForm(forms.ModelForm):
    """Edit your own profile. Also the 'complete your profile' page a new
    patient is sent to on first login."""

    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'phone', 'gender', 
                  'age', 'blood_group', 'address', 'department']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('full_name', 'email', 'phone'):
            self.fields[name].required = True 

        if self.instance.role == 'PATIENT':
            self.fields['age'].required = True
        else:
            for name in ('age', 'blood_group', 'address'):
                del self.fields[name]

        if self.instance.role != 'DOCTOR':
            del self.fields['department']
