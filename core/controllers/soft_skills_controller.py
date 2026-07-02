from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def soft_skills(request):
    return render(request, 'core/soft_skills.html')
