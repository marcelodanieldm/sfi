from django.shortcuts import render


def terminos_condiciones(request):
    return render(request, 'core/legal_terminos.html')


def politica_privacidad(request):
    return render(request, 'core/legal_privacidad.html')
