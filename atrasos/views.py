from django.shortcuts import render

from .servicios_excel import analizar_excel_en_memoria


def inicio(request):
    contexto = {}
    criterio_orden = "cantidad"

    if request.method == "POST":
        archivo = request.FILES.get("archivo")
        criterio_orden = request.POST.get("criterio_orden", "cantidad")

        if not archivo:
            contexto["error"] = "Debe seleccionar un archivo Excel."
            contexto["criterio_orden"] = criterio_orden
            return render(request, "atrasos/inicio.html", contexto)

        try:
            resultado = analizar_excel_en_memoria(
                archivo=archivo,
                criterio_orden=criterio_orden
            )

            contexto["mensaje"] = (
                f"Archivo procesado correctamente. "
                f"Se analizaron {resultado['total_registros']} registros sin guardar en la base de datos."
            )

            contexto["total_registros"] = resultado["total_registros"]
            contexto["total_atrasos"] = resultado["total_atrasos"]
            contexto["total_a_tiempo"] = resultado["total_a_tiempo"]
            contexto["total_sin_retiro"] = resultado["total_sin_retiro"]
            contexto["promedio_atraso"] = resultado["promedio_atraso"]
            contexto["top_docentes"] = resultado["top_docentes"]
            contexto["detalle"] = resultado["detalle"]
            contexto["insights"] = resultado["insights"]
            contexto["criterio_orden"] = resultado["criterio_orden"]
            contexto["detalle_json"] = resultado["detalle"]

        except Exception as e:
            contexto["error"] = f"Ocurrió un error al procesar el archivo: {e}"
            contexto["criterio_orden"] = criterio_orden

    else:
        contexto["criterio_orden"] = criterio_orden

    return render(request, "atrasos/inicio.html", contexto)