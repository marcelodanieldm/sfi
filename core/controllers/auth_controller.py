import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.models import User


def _unique_username(email):
    base = email.split('@')[0][:150]
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1
    return username


class EmailBackend(ModelBackend):
    """Permite autenticar con email en lugar de username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class RegisterForm(UserCreationForm):
    class Meta:
        model  = User
        fields = ('email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email como campo principal
        self.fields['email'].required = True
        # Generar username desde email automáticamente
        for field in self.fields.values():
            field.widget.attrs.update({'autocomplete': 'off'})

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        user.email    = email
        user.username = email.split('@')[0][:150]
        # Evitar username duplicado
        base = user.username
        counter = 1
        while User.objects.filter(username=user.username).exists():
            user.username = f'{base}{counter}'
            counter += 1
        if commit:
            user.save()
        return user


def _login_ctx(form=None, tab='login', next_url='/mentoria/'):
    return {
        'form_register':    form or RegisterForm(),
        'active_tab':       tab,
        'next':             next_url,
        'google_client_id': getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', ''),
    }


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/mentoria/')

    next_url = request.GET.get('next', '/mentoria/')

    if request.method == 'POST':
        action = request.POST.get('action', 'login')

        if action == 'register':
            form_register = RegisterForm(request.POST)
            if form_register.is_valid():
                user = form_register.save()
                login(request, user, backend='core.controllers.auth_controller.EmailBackend')
                return redirect(next_url)
            return render(request, 'core/auth/login.html',
                          _login_ctx(form_register, 'register', next_url))

        else:  # login
            email    = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            user     = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect(next_url)
            messages.error(request, 'Email o contraseña incorrectos.')
            return render(request, 'core/auth/login.html',
                          _login_ctx(tab='login', next_url=next_url))

    return render(request, 'core/auth/login.html',
                  _login_ctx(tab='login', next_url=next_url))


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('core:mentor_ia')


@require_POST
def google_oauth_login(request):
    try:
        data       = json.loads(request.body)
        credential = data.get('credential', '')
        next_url   = data.get('next', '/mentoria/')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Solicitud inválida.'}, status=400)

    client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
    if not client_id or not credential:
        return JsonResponse({'error': 'Google OAuth no configurado.'}, status=503)

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        idinfo = id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id
        )
    except ValueError:
        return JsonResponse({'error': 'Token de Google inválido.'}, status=400)

    email = idinfo.get('email', '').lower()
    if not email:
        return JsonResponse({'error': 'No se pudo obtener el email de Google.'}, status=400)

    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            'username':   _unique_username(email),
            'first_name': idinfo.get('given_name', ''),
            'last_name':  idinfo.get('family_name', ''),
        },
    )

    login(request, user, backend='core.controllers.auth_controller.EmailBackend')
    return JsonResponse({'ok': True, 'next': next_url})
