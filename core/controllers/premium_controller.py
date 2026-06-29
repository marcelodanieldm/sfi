from django.shortcuts import render


def premium(request):
    return render(request, 'core/premium.html')
