from datetime import datetime, time

import pandas as pd
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date

from .models import Bloque


# =========================================================
# BLOQUES OFICIALES BASE
# Estos horarios se usan como respaldo si no existe
# el bloque en la base de datos.
# =========================================================
BLOQUES_POR_DEFECTO = {
    1: time(8, 15),
    2: time(9, 0),
    3: time(9, 50),
    4: time(10, 35),
    5: time(11, 25),
    6: time(12, 10),
    7: time(12, 55),
    8: time(13, 50),
    9: time(14, 35),
    10: time(15, 25),
    11: time(16, 10),
    12: time(17, 0),
    13: time(18, 30),
    14: time(19, 10),
    15: time(19, 50),
    16: time(20, 30),
    17: time(21, 10),
    18: time(21, 50),
}

# También dejamos una tabla por texto horario, por si el Excel
# trae directamente algo como "08:15-09:00" en vez de módulo.
HORARIOS_BLOQUE_POR_TEXTO = {
    "08:15-09:00": time(8, 15),
    "09:00-09:45": time(9, 0),
    "09:50-10:35": time(9, 50),
    "10:35-11:20": time(10, 35),
    "11:25-12:10": time(11, 25),
    "12:10-12:55": time(12, 10),
    "12:55-13:40": time(12, 55),
    "13:50-14:35": time(13, 50),
    "14:35-15:20": time(14, 35),
    "15:25-16:10": time(15, 25),
    "16:10-16:55": time(16, 10),
    "17:00-17:45": time(17, 0),
    "18:30-19:10": time(18, 30),
    "19:10-19:50": time(19, 10),
    "19:50-20:30": time(19, 50),
    "20:30-21:10": time(20, 30),
    "21:10-21:50": time(21, 10),
    "21:50-22:30": time(21, 50),
}


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
    """
    Busca una columna dentro de la fila usando distintos nombres posibles.
    """
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
    total_sin_bloque,
    promedio_atraso,
    top_docentes
):
    insights = []

    porcentaje_atraso = round((total_atrasos / total_registros) * 100, 1) if total_registros else 0
    porcentaje_a_tiempo = round((total_a_tiempo / total_registros) * 100, 1) if total_registros else 0
    porcentaje_sin_retiro = round((total_sin_retiro / total_registros) * 100, 1) if total_registros else 0
    porcentaje_sin_bloque = round((total_sin_bloque / total_registros) * 100, 1) if total_registros else 0

    insights.append({
        "titulo": "Panorama general",
        "texto": (
            f"Con los filtros actuales se observan {total_registros} registros. "
            f"El {porcentaje_atraso}% presenta atraso, "
            f"el {porcentaje_a_tiempo}% está a tiempo, "
            f"el {porcentaje_sin_retiro}% aparece sin retiro "
            f"y el {porcentaje_sin_bloque}% quedó sin bloque asociado."
        )
    })

    insights.append({
        "titulo": "Promedio de atraso",
        "texto": (
            f"El promedio de atraso en el subconjunto analizado es de {promedio_atraso} minutos. "
            f"Este indicador ayuda a distinguir si el problema es leve, moderado o crítico."
        )
    })

    if top_docentes:
        primero = top_docentes[0]
        insights.append({
            "titulo": "Docente con mayor impacto",
            "texto": (
                f"{primero['docente']} lidera el análisis con "
                f"{primero['cantidad']} atrasos y {primero['minutos']} minutos acumulados. "
                f"Su nivel de impacto se clasifica como {primero['semaforo_texto'].lower()}."
            )
        })

    if total_sin_retiro > 0:
        insights.append({
            "titulo": "Registros sin retiro",
            "texto": (
                f"Se detectaron {total_sin_retiro} registros sin retiro. "
                f"Conviene revisar estos casos por separado para mejorar la trazabilidad."
            )
        })

    if total_sin_bloque > 0:
        insights.append({
            "titulo": "Registros sin bloque asociado",
            "texto": (
                f"Se detectaron {total_sin_bloque} registros que no pudieron asociarse a un bloque. "
                f"Esto puede ocurrir si el Excel trae otro formato o si falta homologar horarios."
            )
        })

    return insights


def obtener_hora_desde_texto_bloque(texto_bloque):
    """
    Intenta resolver la hora de inicio a partir de un texto como:
    '08:15-09:00'
    """
    if not texto_bloque:
        return None

    texto_bloque = str(texto_bloque).strip()

    if texto_bloque in HORARIOS_BLOQUE_POR_TEXTO:
        return HORARIOS_BLOQUE_POR_TEXTO[texto_bloque]

    if "-" in texto_bloque:
        try:
            primera_parte = texto_bloque.split("-")[0].strip()
            hora, minuto = map(int, primera_parte.split(":"))
            return time(hora, minuto)
        except Exception:
            return None

    return None


def obtener_bloque_desde_bd_o_memoria(modulo_inicio):
    """
    Busca primero en la tabla Bloque.
    Si no existe, usa la tabla base en memoria.
    """
    if modulo_inicio <= 0:
        return None

    bloque_bd = Bloque.objects.filter(numero=modulo_inicio, activo=True).first()

    if bloque_bd:
        return {
            "numero": bloque_bd.numero,
            "hora_inicio": bloque_bd.hora_inicio,
            "fuente": "bd",
        }

    hora_base = BLOQUES_POR_DEFECTO.get(modulo_inicio)
    if hora_base:
        return {
            "numero": modulo_inicio,
            "hora_inicio": hora_base,
            "fuente": "memoria",
        }

    return None


def calcular_atraso_fila(fila_dict):
    rut_docente = normalizar_texto(buscar_columna(fila_dict, [
        "Rut Docente", "RUT Docente", "Rut docente", "RUT docente"
    ]))

    nombre_docente = normalizar_texto(buscar_columna(fila_dict, [
        "Nombre Docente", "Nombre docente", "Docente"
    ])) or "Docente sin nombre"

    fecha_clase = normalizar_fecha(buscar_columna(fila_dict, [
        "Fecha Clase", "Fecha clase", "Fecha"
    ]))

    modulo_inicio = normalizar_entero(buscar_columna(fila_dict, [
        "Módulo inicio", "Modulo inicio", "Módulo Inicio", "Modulo Inicio"
    ]), por_defecto=0)

    texto_bloque = normalizar_texto(buscar_columna(fila_dict, [
        "Bloque", "Horario", "Hora", "Hora bloque", "Tramo", "Franja"
    ]))

    bloque = obtener_bloque_desde_bd_o_memoria(modulo_inicio)
    hora_inicio_desde_texto = obtener_hora_desde_texto_bloque(texto_bloque)

    fecha_retiro = normalizar_fecha_hora(buscar_columna(fila_dict, [
        "Fecha retiro", "Fecha Retiro", "Hora retiro", "Retiro"
    ]))

    asignatura = normalizar_texto(buscar_columna(fila_dict, ["Asignatura"]))
    seccion = normalizar_texto(buscar_columna(fila_dict, ["Sección", "Seccion"]))
    jornada = normalizar_texto(buscar_columna(fila_dict, ["Jornada"]))
    sala = normalizar_texto(buscar_columna(fila_dict, ["Sala"]))

    hora_base = None
    fuente_bloque = None
    bloque_numero = None

    # Prioridad:
    # 1) hora desde texto del Excel
    # 2) bloque desde BD
    # 3) bloque base en memoria
    if hora_inicio_desde_texto:
        hora_base = hora_inicio_desde_texto
        fuente_bloque = "excel"
    elif bloque:
        hora_base = bloque["hora_inicio"]
        fuente_bloque = bloque["fuente"]
        bloque_numero = bloque["numero"]

    resultado = {
        "rut_docente": rut_docente,
        "docente": nombre_docente,
        "fecha_clase": fecha_clase.isoformat() if fecha_clase else None,
        "fecha_clase_texto": fecha_clase.strftime("%d-%m-%Y") if fecha_clase else "-",
        "modulo_inicio": modulo_inicio,
        "bloque_texto": texto_bloque,
        "bloque_numero": bloque_numero,
        "hora_inicio_bloque": hora_base.strftime("%H:%M") if hora_base else None,
        "fuente_bloque": fuente_bloque,
        "fecha_retiro": fecha_retiro.isoformat() if fecha_retiro else None,
        "asignatura": asignatura,
        "seccion": seccion,
        "jornada": jornada,
        "sala": sala,
        "minutos_atraso": None,
        "estado": "SIN_BLOQUE",
        "estado_texto": "Bloque no configurado",
        "color_estado": "gris",
        "observacion": "No fue posible determinar la hora base del bloque.",
    }

    if not fecha_clase:
        resultado["estado"] = "INCONSISTENTE"
        resultado["estado_texto"] = "Dato inconsistente"
        resultado["color_estado"] = "gris"
        resultado["observacion"] = "La fila no tiene fecha válida."
        return resultado

    if not hora_base:
        return resultado

    if not fecha_retiro:
        resultado["estado"] = "SIN_RETIRO"
        resultado["estado_texto"] = "Sin retiro"
        resultado["color_estado"] = "gris"
        resultado["observacion"] = "El registro no tiene fecha de retiro."
        return resultado

    fecha_hora_programada = datetime.combine(fecha_clase, hora_base)
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

    if fuente_bloque == "excel":
        resultado["observacion"] = f"{estado_texto} (calculado desde horario leído en el Excel)."
    elif fuente_bloque == "memoria":
        resultado["observacion"] = f"{estado_texto} (bloque resuelto desde tabla base en memoria)."
    else:
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
    total_sin_bloque = sum(1 for item in detalle if item["estado"] == "SIN_BLOQUE")

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
        total_sin_bloque=total_sin_bloque,
        promedio_atraso=promedio_atraso,
        top_docentes=top_docentes,
    )

    return {
        "columnas": columnas,
        "total_registros": total_registros,
        "total_atrasos": total_atrasos,
        "total_a_tiempo": total_a_tiempo,
        "total_sin_retiro": total_sin_retiro,
        "total_sin_bloque": total_sin_bloque,
        "promedio_atraso": promedio_atraso,
        "top_docentes": top_docentes,
        "detalle": detalle,
        "insights": insights,
        "criterio_orden": criterio_orden,
    }