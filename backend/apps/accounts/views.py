from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import RegisterForm, WalkInPatientForm, ProfileForm
from django.db.models import Q
from django.contrib import messages
from django.http import Http404
from .models import CustomUser

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
                return redirect('appointments:doctor_dashboard')
            if user.role == 'RECEPTION':
                return redirect('appointments:dashboard')
            if user.role == 'LAB':
                return redirect('lab:dashboard')
            if not user.age:
                return redirect('accounts:profile_edit')
            return redirect('appointments:patient_dashboard')
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
            return redirect('accounts:profile_edit')
        return render(request, 'accounts/register.html', {'form': form})
    form = RegisterForm()
    return render(request, 'accounts/register.html',{'form':form})                        
    
@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'accounts/profile_edit.html', {'form':form})

@login_required
def patient_registry(request):
    if request.user.role != 'RECEPTION':
        raise Http404()

    patients = CustomUser.objects.filter(role='PATIENT').order_by('-date_joined')    
    q = request.GET.get('q', '').strip()
    if q:
        patients = patients.filter(
            Q(full_name__icontains=q) | Q(username__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )

    return render(request, 'accounts/patient_registry.html', {'patients':patients, 'q':q})

@login_required
def register_patient(request):
    if request.user.role != 'RECEPTION':
        raise Http404()

    if request.method == 'POST':
        form = WalkInPatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'{patient.display_name} registered')
            return redirect('appointments:reception_book')
    else:
        form = WalkInPatientForm()

    return render(request, 'accounts/register_patient.html', {'form':form})
