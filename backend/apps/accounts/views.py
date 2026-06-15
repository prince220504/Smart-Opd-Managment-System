from django.http import HttpResponse

def login_view(request):
    return HttpResponse('Login page - coming in Step 12')

def logout_view(request):
    return HttpResponse('Logout - coming in Step 12')

def register_view(request):
    return HttpResponse('Register page - coming in Step 12')