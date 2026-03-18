from django.contrib import admin
from .models import Bloque, Docente, CargaArchivo, RegistroClase, AtrasoDocente


@admin.register(Bloque)
class BloqueAdmin(admin.ModelAdmin):
    list_display = ("numero", "hora_inicio", "hora_termino", "jornada", "activo")
    list_filter = ("jornada", "activo")
    search_fields = ("numero",)
    ordering = ("numero",)


@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ("rut", "nombre")
    search_fields = ("rut", "nombre")
    ordering = ("nombre",)


@admin.register(CargaArchivo)
class CargaArchivoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre_original", "fecha_carga", "total_registros")
    readonly_fields = ("fecha_carga",)
    search_fields = ("nombre_original",)


@admin.register(RegistroClase)
class RegistroClaseAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_clase",
        "docente",
        "asignatura",
        "seccion",
        "modulo_inicio",
        "modulo_termino",
        "fecha_retiro",
    )
    list_filter = ("fecha_clase", "jornada_texto", "seccion", "modulo_inicio")
    search_fields = (
        "docente__nombre",
        "docente__rut",
        "asignatura",
        "seccion",
        "programa_estudio",
    )


@admin.register(AtrasoDocente)
class AtrasoDocenteAdmin(admin.ModelAdmin):
    list_display = (
        "registro_clase",
        "bloque",
        "fecha_hora_programada",
        "minutos_atraso",
        "estado",
    )
    list_filter = ("estado", "bloque")
    search_fields = (
        "registro_clase__docente__nombre",
        "registro_clase__docente__rut",
        "registro_clase__asignatura",
        "registro_clase__seccion",
    )