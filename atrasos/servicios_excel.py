from datetime import datetime

import pandas as pd
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date

from .models import Bloque


def leer_archivo_excel(archivo):
    """
    Lee un archivo Excel .xls o .xlsx y retorna un DataFrame.
    """
    nombre = archivo.name.lower()

    if nombre.endswith(".xls"):
        return pd.read_excel(archivo, engine="xlrd")

    if nombre.endswith(".xlsx"):
        return pd.read_excel(archivo, engine="openpyxl")

    raise ValueError("Formato no soportado. Solo se permiten archivos .xls o .xlsx.")


def normalizar_texto(valor):
    if pd.isna(valor):
        return None

    texto = str(valor).strip()
    return texto if texto else None


def normalizar_entero(valor, por_defecto=0):
    if pd.isna(valor):
        return por_defecto

    try:
        texto = str(valor).strip()
        if texto == "":
            return por_defecto
        return int(float(texto))
    except Exception:
        return por_defecto


def normalizar_fecha(valor):
    if pd.isna(valor):
        return None

    if hasattr(valor, "date"):
        try:
            return valor.date()
        except Exception:
            pass

    texto = str(valor).strip()
    fecha = parse_date(texto)
    if fecha:
        return fecha

    try:
        return pd.to_datetime(valor).date()
    except Exception:
        return None


def normalizar_fecha_hora(valor):
    if pd.isna(valor):
        return None

    fecha_hora = None

    if hasattr(valor, "to_pydatetime"):
        try:
            fecha_hora = valor.to_pydatetime()
        except Exception:
            fecha_hora = None
    elif isinstance(valor, datetime):
        fecha_hora = valor

    if fecha_hora is None:
        texto = str(valor).strip()
        fecha_hora = parse_datetime(texto)

    if fecha_hora is None:
        try:
            convertido = pd.to_datetime(valor)
            if pd.isna(convertido):
                return None
            fecha_hora = convertido.to_pydatetime()
        except Exception:
            return None

    if timezone.is_naive(fecha_hora):
        fecha_hora = timezone.make_aware(fecha_hora, timezone.get_current_timezone())

    return fecha_hora


def buscar_columna(diccionario_fila, nombres_posibles):
    for nombre in nombres_posibles:
        if nombre in diccionario_fila:
            return diccionario_fila.get(nombre)
    return None


def clasificar_atraso(minutos_atraso):
    if minutos_atraso is None:
        return "SIN_RETIRO", "Sin retiro"

    if minutos_atraso <= 0:
        return "A_TIEMPO", "A tiempo"

    if 1 <= minutos_atraso <= 5:
        return "TOLERANCIA", "Tolerancia"

    if 6 <= minutos_atraso <= 10:
        return "LEVE", "Atraso leve"

    if 11 <= minutos_atraso <= 20:
        return "MEDIO", "Atraso medio"

    return "GRAVE", "Atraso grave"


def obtener_color_estado(estado):
    colores = {
        "A_TIEMPO": "verde",
        "TOLERANCIA": "amarillo",
        "LEVE": "naranjo",
        "MEDIO": "rojo",
        "GRAVE": "rojo",
        "SIN_RETIRO": "gris",
        "SIN_BLOQUE": "gris",
        "INCONSISTENTE": "gris",
    }
    return colores.get(estado, "gris")


def calcular_semaforo_docente(cantidad, minutos):
    if minutos >= 150 or cantidad >= 20:
        return "alto", "Alto impacto"
    if minutos >= 60 or cantidad >= 10:
        return "medio", "Impacto medio"
    return "bajo", "Impacto bajo"


def construir_insights(
    total_registros,
    total_atrasos,
    total_a_tiempo,
    total_sin_retiro,
    promedio_atraso,
    top_docentes
):
    insights = []

    porcentaje_atraso = round((total_atrasos / total_registros) * 100, 1) if total_registros else 0
    porcentaje_a_tiempo = round((total_a_tiempo / total_registros) * 100, 1) if total_registros else 0
    porcentaje_sin_retiro = round((total_sin_retiro / total_registros) * 100, 1) if total_registros else 0

    insights.append({
        "titulo": "Panorama general",
        "texto": (
            f"Se analizaron {total_registros} registros. "
            f"El {porcentaje_atraso}% presenta atraso, "
            f"el {porcentaje_a_tiempo}% está a tiempo "
            f"y el {porcentaje_sin_retiro}% aparece sin retiro."
        )
    })

    insights.append({
        "titulo": "Promedio de atraso",
        "texto": (
            f"El promedio de atraso entre los registros con retraso es de "
            f"{promedio_atraso} minutos. Esto permite distinguir si el problema es leve, "
            f"moderado o si ya requiere intervención."
        )
    })

    if top_docentes:
        primero = top_docentes[0]
        insights.append({
            "titulo": "Docente con mayor impacto",
            "texto": (
                f"{primero['docente']} lidera el análisis con "
                f"{primero['cantidad']} atrasos y {primero['minutos']} minutos acumulados, "
                f"clasificado como {primero['semaforo_texto'].lower()}."
            )
        })

    if total_sin_retiro > 0:
        insights.append({
            "titulo": "Registros incompletos",
            "texto": (
                f"Se detectaron {total_sin_retiro} registros sin retiro. "
                f"Estos casos pueden afectar la trazabilidad y conviene revisarlos por separado."
            )
        })

    return insights


def calcular_atraso_fila(fila_dict):
    rut_docente = normalizar_texto(buscar_columna(fila_dict, [
        "Rut Docente", "RUT Docente", "Rut docente", "RUT docente"
    ]))

    nombre_docente = normalizar_texto(buscar_columna(fila_dict, [
        "Nombre Docente", "Nombre docente", "Docente"
    ])) or "Docente sin nombre"

    fecha_clase = normalizar_fecha(buscar_columna(fila_dict, [
        "Fecha Clase", "Fecha clase"
    ]))

    modulo_inicio = normalizar_entero(buscar_columna(fila_dict, [
        "Módulo inicio", "Modulo inicio"
    ]), por_defecto=0)

    bloque = Bloque.objects.filter(numero=modulo_inicio, activo=True).first()

    fecha_retiro = normalizar_fecha_hora(buscar_columna(fila_dict, [
        "Fecha retiro", "Fecha Retiro"
    ]))

    asignatura = normalizar_texto(buscar_columna(fila_dict, ["Asignatura"]))
    seccion = normalizar_texto(buscar_columna(fila_dict, ["Sección", "Seccion"]))
    jornada = normalizar_texto(buscar_columna(fila_dict, ["Jornada"]))
    sala = normalizar_texto(buscar_columna(fila_dict, ["Sala"]))

    resultado = {
        "rut_docente": rut_docente,
        "docente": nombre_docente,
        "fecha_clase": fecha_clase.isoformat() if fecha_clase else None,
        "fecha_clase_texto": fecha_clase.strftime("%d-%m-%Y") if fecha_clase else "-",
        "modulo_inicio": modulo_inicio,
        "bloque_numero": bloque.numero if bloque else None,
        "hora_inicio_bloque": bloque.hora_inicio.strftime("%H:%M") if bloque else None,
        "fecha_retiro": fecha_retiro.isoformat() if fecha_retiro else None,
        "asignatura": asignatura,
        "seccion": seccion,
        "jornada": jornada,
        "sala": sala,
        "minutos_atraso": None,
        "estado": "SIN_BLOQUE",
        "estado_texto": "Bloque no configurado",
        "color_estado": "gris",
        "observacion": "No existe bloque configurado para el módulo de inicio.",
    }

    if not fecha_clase:
        resultado["estado"] = "INCONSISTENTE"
        resultado["estado_texto"] = "Dato inconsistente"
        resultado["color_estado"] = "gris"
        resultado["observacion"] = "La fila no tiene fecha de clase válida."
        return resultado

    if not bloque:
        return resultado

    if not fecha_retiro:
        resultado["estado"] = "SIN_RETIRO"
        resultado["estado_texto"] = "Sin retiro"
        resultado["color_estado"] = "gris"
        resultado["observacion"] = "El registro no tiene fecha de retiro."
        return resultado

    fecha_hora_programada = datetime.combine(fecha_clase, bloque.hora_inicio)
    fecha_hora_programada = timezone.make_aware(
        fecha_hora_programada,
        timezone.get_current_timezone()
    )

    diferencia_minutos = int(
        round((fecha_retiro - fecha_hora_programada).total_seconds() / 60)
    )

    resultado["minutos_atraso"] = diferencia_minutos

    if diferencia_minutos < -180 or diferencia_minutos > 600:
        resultado["estado"] = "INCONSISTENTE"
        resultado["estado_texto"] = "Dato inconsistente"
        resultado["color_estado"] = "gris"
        resultado["observacion"] = "La diferencia calculada parece inconsistente y requiere revisión."
        return resultado

    estado, estado_texto = clasificar_atraso(diferencia_minutos)
    resultado["estado"] = estado
    resultado["estado_texto"] = estado_texto
    resultado["color_estado"] = obtener_color_estado(estado)
    resultado["observacion"] = estado_texto

    return resultado


def analizar_excel_en_memoria(archivo, criterio_orden="cantidad"):
    """
    Procesa el Excel completamente en memoria y retorna:
    - resumen ejecutivo
    - top docentes
    - detalle completo
    - insights
    """
    df = leer_archivo_excel(archivo)

    if df.empty:
        raise ValueError("El archivo no contiene registros.")

    columnas = [str(col).strip() for col in df.columns]
    df.columns = columnas

    detalle = []
    for _, fila in df.iterrows():
        fila_dict = fila.to_dict()
        resultado = calcular_atraso_fila(fila_dict)
        detalle.append(resultado)

    total_registros = len(detalle)
    total_atrasos = sum(
        1 for item in detalle
        if item["minutos_atraso"] is not None and item["minutos_atraso"] > 0
    )
    total_a_tiempo = sum(1 for item in detalle if item["estado"] == "A_TIEMPO")
    total_sin_retiro = sum(1 for item in detalle if item["estado"] == "SIN_RETIRO")

    atrasos_positivos = [
        item["minutos_atraso"]
        for item in detalle
        if item["minutos_atraso"] is not None and item["minutos_atraso"] > 0
    ]

    promedio_atraso = round(sum(atrasos_positivos) / len(atrasos_positivos), 1) if atrasos_positivos else 0

    resumen_docentes = {}

    for item in detalle:
        if item["minutos_atraso"] is not None and item["minutos_atraso"] > 0:
            nombre = item["docente"] or "Docente sin nombre"

            if nombre not in resumen_docentes:
                resumen_docentes[nombre] = {
                    "cantidad": 0,
                    "minutos": 0
                }

            resumen_docentes[nombre]["cantidad"] += 1
            resumen_docentes[nombre]["minutos"] += item["minutos_atraso"]

    docentes_ordenados = []
    for nombre, datos in resumen_docentes.items():
        semaforo, semaforo_texto = calcular_semaforo_docente(
            datos["cantidad"],
            datos["minutos"]
        )
        docentes_ordenados.append({
            "docente": nombre,
            "cantidad": datos["cantidad"],
            "minutos": datos["minutos"],
            "semaforo": semaforo,
            "semaforo_texto": semaforo_texto,
        })

    if criterio_orden == "minutos":
        docentes_ordenados = sorted(
            docentes_ordenados,
            key=lambda x: (x["minutos"], x["cantidad"]),
            reverse=True
        )
    else:
        docentes_ordenados = sorted(
            docentes_ordenados,
            key=lambda x: (x["cantidad"], x["minutos"]),
            reverse=True
        )

    top_docentes = docentes_ordenados[:5]

    insights = construir_insights(
        total_registros=total_registros,
        total_atrasos=total_atrasos,
        total_a_tiempo=total_a_tiempo,
        total_sin_retiro=total_sin_retiro,
        promedio_atraso=promedio_atraso,
        top_docentes=top_docentes,
    )

    return {
        "columnas": columnas,
        "total_registros": total_registros,
        "total_atrasos": total_atrasos,
        "total_a_tiempo": total_a_tiempo,
        "total_sin_retiro": total_sin_retiro,
        "promedio_atraso": promedio_atraso,
        "top_docentes": top_docentes,
        "detalle": detalle,
        "insights": insights,
        "criterio_orden": criterio_orden,
    }