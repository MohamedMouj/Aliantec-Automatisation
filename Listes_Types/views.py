from django.shortcuts import render


def index(request):
    return render(request, 'Listes_Types/index.html')