from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from core.models import Habilidad, Categoria


def lista_habilidades(request):
    habilidades = Habilidad.objects.filter(activo=True).select_related('categoria')
    categorias = Categoria.objects.all()
    categoria_id = request.GET.get('categoria')

    if categoria_id:
        habilidades = habilidades.filter(categoria_id=categoria_id)

    context = {
        'habilidades': habilidades,
        'categorias': categorias,
        'categoria_seleccionada': categoria_id,
    }
    return render(request, 'core/habilidades/lista.html', context)


def detalle_habilidad(request, pk):
    habilidad = get_object_or_404(Habilidad, pk=pk, activo=True)
    return render(request, 'core/habilidades/detalle.html', {'habilidad': habilidad})
