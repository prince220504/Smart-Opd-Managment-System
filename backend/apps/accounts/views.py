from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import RegisterForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.role == 'DOCTOR':
                if not user.availabilities.exclude(recurrence='DATE').exists():
                    return redirect('appointments:doctor_schedule')
                return redirect('appointments:doctor_today')
            if user.role == 'RECEPTION':
                return redirect('appointments:appointment_list')
            return redirect('accounts:profile')
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid username or password',})
        
    return render(request, 'accounts/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:profile')
        return render(request, 'accounts/register.html', {'form': form})
    form = RegisterForm()
    return render(request, 'accounts/register.html',{'form':form})                        
    
@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')