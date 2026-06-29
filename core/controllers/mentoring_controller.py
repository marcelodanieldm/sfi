from django.shortcuts import render


def mentoring(request):
    return render(request, 'core/mentoring.html')
