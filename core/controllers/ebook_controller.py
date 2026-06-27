from django.shortcuts import render


def ebook(request):
    return render(request, 'core/ebook_landing.html')
