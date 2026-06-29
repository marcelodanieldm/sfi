from django.shortcuts import render


def soft_skills(request):
    return render(request, 'core/soft_skills.html')
