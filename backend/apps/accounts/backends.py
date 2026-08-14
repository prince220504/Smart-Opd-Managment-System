from django.contrib.auth.backends import ModelBackend
from .models import CustomUser

class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        user = (
            CustomUser.objects.filter(username=username).first()
            or CustomUser.objects.filter(email__iexact=username).first()
        )

        if user is None:
            CustomUser().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None