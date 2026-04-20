from datetime import datetime, time
from io import BytesIO, StringIO

import pandas as pd
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date

from .models import Bloque


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
TOLERANCIA_MINUTOS = 15
TOPE_MAXIMO_MINUTOS = 90


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


def archivo_parece_html(contenido_bytes):
    """
    Detecta si el archivo contiene HTML en vez de un Excel binario real.
    """
    if not contenido_bytes:
        return False

    encabezado = contenido_bytes[:500].strip().lower()

    patrones_html = [
        b"<html",
        b"<!doctype html",
        b"<head",
        b"<body",
        b"<table",
        b"<meta",
    ]

    return any(patron in encabezado for patron in patrones_html)


def normalizar_dataframe_html(df):
    """
    Cuando una tabla HTML viene exportada como .xls, muchas veces pandas
    la lee con columnas 0,1,2,3... y la primera fila trae los encabezados reales.
    Esta función transforma esa primera fila en nombres de columnas.
    """
    if df is None or df.empty:
        return df

    columnas_actuales = list(df.columns)

    if not all(isinstance(col, int) for col in columnas_actuales):
        df.columns = [str(col).strip() for col in df.columns]
        return df

    primera_fila = df.iloc[0].tolist()
    encabezados = [str(valor).strip() for valor in primera_fila]

    palabras_clave = {
        "fecha clase",
        "rut docente",
        "nombre docente",
        "programa de estudio",
        "asignatura",
        "sección",
        "modulo inicio",
        "módulo inicio",
        "fecha retiro",
    }

    encabezados_normalizados = {texto.lower() for texto in encabezados if texto}

    if encabezados_normalizados & palabras_clave:
        df = df.iloc[1:].copy()
        df.columns = encabezados
        df.reset_index(drop=True, inplace=True)
    else:
        df.columns = [str(col).strip() for col in df.columns]

    return df


def leer_tabla_html_desde_bytes(contenido_bytes):
    """
    Lee una tabla HTML exportada con extensión .xls.
    Muchos sistemas generan este formato.
    """
    try:
        texto = contenido_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            texto = contenido_bytes.decode("latin-1")
        except UnicodeDecodeError:
            texto = contenido_bytes.decode("utf-8", errors="ignore")

    tablas = pd.read_html(StringIO(texto))

    if not tablas:
        raise ValueError(
            "El archivo tiene contenido HTML, pero no se encontró una tabla legible."
        )

    df = tablas[0]

    if df.empty:
        raise ValueError(
            "El archivo HTML fue leído, pero no contiene registros en la primera tabla."
        )

    df = normalizar_dataframe_html(df)
    return df


def leer_archivo_excel(archivo):
    """
    Lee un archivo Excel .xls o .xlsx y retorna un DataFrame.

    Soporta:
    - .xlsx reales
    - .xls reales
    - .xls exportados como HTML por sistemas externos
    """
    nombre = (archivo.name or "").lower()

    try:
        archivo.seek(0)
    except Exception:
        pass

    contenido = archivo.read()

    if not contenido:
        raise ValueError("El archivo está vacío o no fue posible leerlo.")

    if nombre.endswith(".xlsx"):
        try:
            df = pd.read_excel(BytesIO(contenido), engine="openpyxl")
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as error:
            raise ValueError(
                f"No fue posible leer el archivo .xlsx. Detalle: {error}"
            )

    if nombre.endswith(".xls"):
        if archivo_parece_html(contenido):
            return leer_tabla_html_desde_bytes(contenido)

        try:
            df = pd.read_excel(BytesIO(contenido), engine="xlrd")
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as error_xls:
            try:
                return leer_tabla_html_desde_bytes(contenido)
            except Exception:
                raise ValueError(
                    "El archivo subido tiene extensión .xls, pero no corresponde a un "
                    "Excel binario válido ni a una tabla HTML legible. "
                    f"Detalle técnico: {error_xls}"
                )

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
        return pd.to_datetime(valor, dayfirst=True).date()
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
            convertido = pd.to_datetime(valor, dayfirst=True)
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
    claves_normalizadas = {
        str(clave).strip(): valor
        for clave, valor in diccionario_fila.items()
    }

    for nombre in nombres_posibles:
        nombre_limpio = str(nombre).strip()
        if nombre_limpio in claves_normalizadas:
            return claves_normalizadas.get(nombre_limpio)

    return None


def aplicar_tolerancia_minutos(minutos_calculados):
    """
    Resta la tolerancia fija definida y nunca devuelve valores negativos.
    """
    if minutos_calculados is None:
        return None

    minutos_ajustados = minutos_calculados - TOLERANCIA_MINUTOS

    if minutos_ajustados < 0:
        return 0

    return minutos_ajustados


def limitar_atraso_real(minutos_reales):
    """
    Si el atraso supera 90 minutos, se asume posible no marcaje del libro
    y se limita a 90.
    """
    if minutos_reales is None:
        return None, False

    if minutos_reales > TOPE_MAXIMO_MINUTOS:
        return TOPE_MAXIMO_MINUTOS, True

    return minutos_reales, False


def clasificar_atraso(minutos_reales):
    """
    Clasificación visible:
    - <= 0: A tiempo
    - 1 a 4: Tolerancia
    - 5 a 9: Impacto leve
    - 10 a 14: Impacto moderado
    - >= 15: Impacto crítico
    """
    if minutos_reales is None:
        return "SIN_RETIRO", "Sin retiro"

    if minutos_reales <= 0:
        return "A_TIEMPO", "A tiempo"

    if 1 <= minutos_reales <= 4:
        return "TOLERANCIA", "Tolerancia"

    if 5 <= minutos_reales <= 9:
        return "LEVE", "Impacto leve"

    if 10 <= minutos_reales <= 14:
        return "MEDIO", "Impacto moderado"

    return "GRAVE", "Impacto crítico"


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
    """
    Clasificación mejorada de impacto docente considerando:
    - Frecuencia (cantidad de atrasos)
    - Severidad (minutos acumulados)

    No rompe el sistema actual, solo mejora la lógica.
    """

    # 🔴 CRÍTICO
    if minutos >= 150 or (cantidad >= 20 and minutos >= 100):
        return "alto", "Impacto crítico"

    # 🟠 MODERADO
    if minutos >= 70 or cantidad >= 15:
        return "medio", "Impacto moderado"

    # 🟡 LEVE
    if minutos >= 20 or cantidad >= 5:
        return "bajo", "Impacto leve"

    # 🟢 SIN IMPACTO
    return "bajo", "Sin impacto relevante"


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
            f"El subconjunto actual reúne {total_registros} registros y {total_atrasos} presentan atraso efectivo."
        )
    })

    insights.append({
        "titulo": "Promedio de atraso",
        "texto": (
            f"El promedio de atraso observado es de {promedio_atraso} minutos."
        )
    })

    if top_docentes:
        primero = top_docentes[0]
        insights.append({
            "titulo": "Caso más visible",
            "texto": (
                f"{primero['docente']} lidera el ranking actual con "
                f"{primero['cantidad']} atrasos y {primero['minutos']} minutos acumulados."
            )
        })

    if total_sin_retiro > 0:
        insights.append({
            "titulo": "Registros sin retiro",
            "texto": (
                f"Se observaron {total_sin_retiro} registros sin retiro. Conviene revisarlos por separado."
            )
        })

    if total_sin_bloque > 0:
        insights.append({
            "titulo": "Registros sin bloque asociado",
            "texto": (
                f"Se observaron {total_sin_bloque} registros sin bloque asociado. Conviene revisar la homologación de horarios."
            )
        })

    return insights


def obtener_hora_desde_texto_bloque(texto_bloque):
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

    programa_estudio = normalizar_texto(buscar_columna(fila_dict, [
        "Programa de Estudio", "Programa de estudio", "Programa Estudio",
        "Plan de Estudio", "Plan de estudio", "Carrera"
    ]))
    asignatura = normalizar_texto(buscar_columna(fila_dict, ["Asignatura"]))
    seccion = normalizar_texto(buscar_columna(fila_dict, ["Sección", "Seccion"]))
    jornada = normalizar_texto(buscar_columna(fila_dict, ["Jornada"]))
    sala = normalizar_texto(buscar_columna(fila_dict, ["Sala"]))

    hora_base = None
    fuente_bloque = None
    bloque_numero = None

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
        "bloque_numero": bloque_numero if bloque_numero is not None else modulo_inicio,
        "hora_inicio_bloque": hora_base.strftime("%H:%M") if hora_base else None,
        "hora_inicio_texto": hora_base.strftime("%H:%M") if hora_base else "-",
        "fuente_bloque": fuente_bloque,
        "fecha_retiro": fecha_retiro.isoformat() if fecha_retiro else None,
        "programa_estudio": programa_estudio,
        "asignatura": asignatura,
        "seccion": seccion,
        "jornada": jornada,
        "sala": sala,
        "minutos_atraso": None,
        "minutos_atraso_original": None,
        "minutos_atraso_tolerancia": None,
        "minutos_tolerancia_aplicada": TOLERANCIA_MINUTOS,
        "fue_capado_90": False,
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

    diferencia_minutos_original = int(
        round((fecha_retiro - fecha_hora_programada).total_seconds() / 60)
    )

    if diferencia_minutos_original < -180 or diferencia_minutos_original > 600:
        resultado["estado"] = "INCONSISTENTE"
        resultado["estado_texto"] = "Dato inconsistente"
        resultado["color_estado"] = "gris"
        resultado["observacion"] = "La diferencia calculada parece inconsistente y requiere revisión."
        return resultado

    minutos_reales_brutos = max(0, diferencia_minutos_original)
    minutos_reales, fue_capado = limitar_atraso_real(minutos_reales_brutos)
    minutos_con_tolerancia = aplicar_tolerancia_minutos(minutos_reales)

    resultado["minutos_atraso"] = minutos_reales
    resultado["minutos_atraso_original"] = minutos_reales
    resultado["minutos_atraso_tolerancia"] = minutos_con_tolerancia
    resultado["fue_capado_90"] = fue_capado

    estado, estado_texto = clasificar_atraso(minutos_reales)
    resultado["estado"] = estado
    resultado["estado_texto"] = estado_texto
    resultado["color_estado"] = obtener_color_estado(estado)

    if fue_capado:
        detalle_tolerancia = (
            f"Posible no marcaje del libro. El atraso real superó {TOPE_MAXIMO_MINUTOS} min y se ajustó a {TOPE_MAXIMO_MINUTOS} min. "
            f"Con tolerancia de {TOLERANCIA_MINUTOS} min, quedaría en {minutos_con_tolerancia} min."
        )
    elif minutos_reales > 0:
        detalle_tolerancia = (
            f"Atraso real {minutos_reales} min. "
            f"Si se aplicara tolerancia de {TOLERANCIA_MINUTOS} min, "
            f"el atraso quedaría en {minutos_con_tolerancia} min."
        )
    else:
        detalle_tolerancia = (
            f"Sin atraso real. Con tolerancia de {TOLERANCIA_MINUTOS} min el resultado también queda en 0 min."
        )

    if fuente_bloque == "excel":
        resultado["observacion"] = f"{estado_texto}. {detalle_tolerancia} (calculado desde horario leído en el Excel)."
    elif fuente_bloque == "memoria":
        resultado["observacion"] = f"{estado_texto}. {detalle_tolerancia} (bloque resuelto desde tabla base en memoria)."
    else:
        resultado["observacion"] = f"{estado_texto}. {detalle_tolerancia}"

    return resultado


def analizar_excel_en_memoria(archivo, criterio_orden="cantidad"):
    """
    Procesa el Excel completamente en memoria y retorna:
    - resumen ejecutivo
    - top docentes
    - detalle visible para el panel
    - detalle completo para filtros/ranking/KPIs
    - insights
    """
    df = leer_archivo_excel(archivo)

    if df.empty:
        raise ValueError("El archivo no contiene registros.")

    columnas = [str(col).strip() for col in df.columns]
    df.columns = columnas

    detalle_completo = []
    for _, fila in df.iterrows():
        fila_dict = fila.to_dict()
        resultado = calcular_atraso_fila(fila_dict)
        detalle_completo.append(resultado)

    total_registros = len(detalle_completo)

    total_atrasos = sum(
        1 for item in detalle_completo
        if item["minutos_atraso"] is not None and item["minutos_atraso"] > 0
    )
    total_a_tiempo = sum(
        1 for item in detalle_completo
        if item["estado"] == "A_TIEMPO"
    )
    total_sin_retiro = sum(
        1 for item in detalle_completo
        if item["estado"] == "SIN_RETIRO"
    )
    total_sin_bloque = sum(
        1 for item in detalle_completo
        if item["estado"] == "SIN_BLOQUE"
    )

    atrasos_positivos = [
        item["minutos_atraso"]
        for item in detalle_completo
        if item["minutos_atraso"] is not None and item["minutos_atraso"] > 0
    ]

    promedio_atraso = round(sum(atrasos_positivos) / len(atrasos_positivos), 1) if atrasos_positivos else 0

    resumen_docentes = {}

    for item in detalle_completo:
        if item["minutos_atraso"] is not None and item["minutos_atraso"] > 0:
            nombre = item["docente"] or "Docente sin nombre"

            if nombre not in resumen_docentes:
                resumen_docentes[nombre] = {
                    "cantidad": 0,
                    "minutos": 0,
                    "horas": 0,
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
            "horas": round(datos["minutos"] / 60, 1),
            "semaforo": semaforo,
            "semaforo_texto": semaforo_texto,
        })

    if criterio_orden == "minutos":
        docentes_ordenados = sorted(
            docentes_ordenados,
            key=lambda x: (x["minutos"], x["cantidad"], x["docente"]),
            reverse=True
        )
    else:
        docentes_ordenados = sorted(
            docentes_ordenados,
            key=lambda x: (x["cantidad"], x["minutos"], x["docente"]),
            reverse=True
        )

    detalle_visible = [
        item for item in detalle_completo
        if item["minutos_atraso"] is not None and item["minutos_atraso"] >= 5
    ]
    detalle_visible = sorted(
        detalle_visible,
        key=lambda x: (
            x.get("minutos_atraso") or 0,
            x.get("fecha_clase") or "",
            x.get("docente") or "",
        ),
        reverse=True
    )

    top_docentes = docentes_ordenados[:10]

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
        "detalle": detalle_visible,
        "detalle_visible": detalle_visible,
        "detalle_completo": detalle_completo,
        "insights": insights,
        "criterio_orden": criterio_orden,
    }