from django.urls import path

from .views import (
    acceso_denegado,
    acceso_token,
    cerrar_sesion,
    generar_reporte_pdf,
    inicio,
    reporte_docente,
)

app_name = "atrasos"

urlpatterns = [
    path("", inicio, name="inicio"),
    path("acceso-token/", acceso_token, name="acceso_token"),
    path("acceso-denegado/", acceso_denegado, name="acceso_denegado"),
    path("cerrar-sesion/", cerrar_sesion, name="cerrar_sesion"),
    path("reporte/", generar_reporte_pdf, name="reporte_pdf"),
    path("reporte-docente/", reporte_docente, name="reporte_docente"),
]