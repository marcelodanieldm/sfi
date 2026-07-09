from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def soft_skills(request, subpath=''):
    # El parámetro subpath se ignora, Django renderiza soft_skills.html
    # y la aplicación Vue maneja el routing en el cliente
    return render(request, 'core/soft_skills.html')
