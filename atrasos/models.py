from django.db import models


class Bloque(models.Model):
    JORNADAS = (
        ("DIURNA", "Diurna"),
        ("VESPERTINA", "Vespertina"),
    )

    numero = models.PositiveIntegerField(unique=True)
    hora_inicio = models.TimeField()
    hora_termino = models.TimeField()
    jornada = models.CharField(max_length=20, choices=JORNADAS)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Bloque"
        verbose_name_plural = "Bloques"
        ordering = ["numero"]

    def __str__(self):
        return f"Bloque {self.numero} ({self.hora_inicio} - {self.hora_termino})"


class Docente(models.Model):
    rut = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.rut})"


class CargaArchivo(models.Model):
    archivo = models.FileField(upload_to="cargas_excel/")
    nombre_original = models.CharField(max_length=255)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    total_registros = models.PositiveIntegerField(default=0)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Carga de archivo"
        verbose_name_plural = "Cargas de archivos"
        ordering = ["-fecha_carga"]

    def __str__(self):
        return f"Carga {self.id} - {self.nombre_original}"


class RegistroClase(models.Model):
    carga = models.ForeignKey(
        CargaArchivo,
        on_delete=models.CASCADE,
        related_name="registros"
    )
    docente = models.ForeignKey(
        Docente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_clase"
    )

    fecha_clase = models.DateField()
    jornada_texto = models.CharField(max_length=100, blank=True, null=True)
    sede = models.CharField(max_length=150, blank=True, null=True)
    sala = models.CharField(max_length=150, blank=True, null=True)

    programa_estudio = models.CharField(max_length=255, blank=True, null=True)
    codigo_asignatura = models.CharField(max_length=100, blank=True, null=True)
    asignatura = models.CharField(max_length=255, blank=True, null=True)
    seccion = models.CharField(max_length=100, blank=True, null=True)
    sub_seccion = models.CharField(max_length=100, blank=True, null=True)
    modalidad = models.CharField(max_length=100, blank=True, null=True)
    dia = models.CharField(max_length=50, blank=True, null=True)

    modulo_inicio = models.PositiveIntegerField()
    modulo_termino = models.PositiveIntegerField(blank=True, null=True)

    asistentes = models.PositiveIntegerField(default=0)
    alumnos_totales = models.PositiveIntegerField(default=0)
    materias_revisadas = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    fecha_retiro = models.DateTimeField(blank=True, null=True)
    fecha_devolucion = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Registro de clase"
        verbose_name_plural = "Registros de clases"
        ordering = ["-fecha_clase", "modulo_inicio", "docente__nombre"]

    def __str__(self):
        nombre_docente = self.docente.nombre if self.docente else "Sin docente"
        return f"{self.fecha_clase} - {nombre_docente} - Bloque {self.modulo_inicio}"


class AtrasoDocente(models.Model):
    ESTADOS = (
        ("A_TIEMPO", "A tiempo"),
        ("TOLERANCIA", "Tolerancia"),
        ("LEVE", "Atraso leve"),
        ("MEDIO", "Atraso medio"),
        ("GRAVE", "Atraso grave"),
        ("SIN_RETIRO", "Sin retiro"),
        ("SIN_BLOQUE", "Bloque no configurado"),
        ("INCONSISTENTE", "Dato inconsistente"),
    )

    registro_clase = models.OneToOneField(
        RegistroClase,
        on_delete=models.CASCADE,
        related_name="atraso"
    )
    bloque = models.ForeignKey(
        Bloque,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atrasos"
    )
    fecha_hora_programada = models.DateTimeField(blank=True, null=True)
    minutos_atraso = models.IntegerField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="SIN_BLOQUE")
    observacion_calculo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Atraso docente"
        verbose_name_plural = "Atrasos docentes"
        ordering = ["-fecha_hora_programada"]

    def __str__(self):
        return f"Atraso {self.id} - {self.estado}"