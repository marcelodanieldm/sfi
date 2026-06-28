from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.shortcuts import redirect, render

from core.models import User


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


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:mentor_ia')

    next_url = request.GET.get('next', 'core:mentor_ia')

    if request.method == 'POST':
        action = request.POST.get('action', 'login')

        if action == 'register':
            form_register = RegisterForm(request.POST)
            form_login    = AuthenticationForm()
            if form_register.is_valid():
                user = form_register.save()
                login(request, user)
                return redirect(next_url)
            # Muestra tab registro con errores
            return render(request, 'core/auth/login.html', {
                'form_login':    form_login,
                'form_register': form_register,
                'active_tab':    'register',
                'next':          next_url,
            })

        else:  # login
            form_login    = AuthenticationForm(request, data=request.POST)
            form_register = RegisterForm()
            if form_login.is_valid():
                login(request, form_login.get_user())
                return redirect(next_url)
            messages.error(request, 'Email o contraseña incorrectos.')
            return render(request, 'core/auth/login.html', {
                'form_login':    form_login,
                'form_register': form_register,
                'active_tab':    'login',
                'next':          next_url,
            })

    return render(request, 'core/auth/login.html', {
        'form_login':    AuthenticationForm(),
        'form_register': RegisterForm(),
        'active_tab':    'login',
        'next':          next_url,
    })


def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('core:inicio')
