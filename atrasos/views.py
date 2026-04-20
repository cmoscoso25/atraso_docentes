from collections import Counter
from datetime import datetime
from statistics import median

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.core import signing
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from .permisos import acceso_restringido_atrasos, usuario_tiene_rol_permitido
from .servicio_reporte import generar_pdf_reporte, generar_pdf_reporte_docente
from .servicios_excel import analizar_excel_en_memoria


@login_required
def acceso_denegado(request):
    contexto = {
        "titulo": "Acceso restringido",
        "mensaje": (
            "Tu usuario inició sesión correctamente, pero no cuenta con permisos "
            "para acceder al sistema de control de atrasos docentes."
        ),
    }
    return render(request, "atrasos/acceso_denegado.html", contexto)


def acceso_token(request):
    token = request.GET.get("token")

    if not token:
        return redirect("/login/?next=/")

    try:
        datos = signing.loads(
            token,
            key=settings.SSO_CLAVE_COMPARTIDA,
            salt="sso-atrasos-docentes",
            max_age=60,
        )
    except Exception:
        return redirect("/login/?next=/")

    username = (datos.get("username") or "").strip()
    nombre = (datos.get("nombre") or "").strip()
    rol = (datos.get("rol") or "").strip()

    if not username:
        return redirect("/login/?next=/")

    usuario, creado = User.objects.get_or_create(username=username)

    if creado:
        usuario.set_unusable_password()

    if nombre:
        usuario.first_name = nombre

    usuario.is_staff = True
    usuario.save()

    if rol:
        grupo, _ = Group.objects.get_or_create(name=rol)
        usuario.groups.add(grupo)

    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")

    if not usuario_tiene_rol_permitido(usuario):
        return redirect("acceso_denegado")

    return redirect("/")


def cerrar_sesion(request):
    logout(request)
    request.session.flush()
    return redirect("http://127.0.0.1:8000/logout/")


def numero_seguro(valor):
    try:
        if valor is None or valor == "":
            return 0
        return float(valor)
    except (TypeError, ValueError):
        return 0


def texto_seguro(valor, por_defecto="-"):
    texto = str(valor or "").strip()
    return texto if texto else por_defecto


def impacto_docente(cantidad, minutos):
    if minutos >= 15:
        return "Critico"
    if minutos >= 10:
        return "Moderado"
    if minutos >= 5:
        return "Leve"
    return "Bajo"


def obtener_estado_global(total_registros, total_atrasos, promedio_atraso, top_docentes):
    if total_registros <= 0:
        return "Controlado"

    porcentaje_atrasos = (total_atrasos / total_registros) * 100 if total_registros else 0
    hay_impacto_critico = any(item.get("semaforo") == "alto" for item in top_docentes)
    hay_impacto_moderado = any(item.get("semaforo") == "medio" for item in top_docentes)

    if hay_impacto_critico or porcentaje_atrasos >= 35 or promedio_atraso >= 15:
        return "Crítico"

    if hay_impacto_moderado or porcentaje_atrasos >= 15 or promedio_atraso >= 10:
        return "Atención"

    return "Controlado"


def construir_ranking_para_pdf(detalle, criterio_orden="cantidad"):
    resumen = {}
    programas_por_docente = {}

    for item in detalle:
        docente = texto_seguro(item.get("docente"), "")
        programa = texto_seguro(item.get("programa_estudio"), "")
        minutos = numero_seguro(item.get("minutos_atraso"))

        if not docente or minutos <= 0:
            continue

        if docente not in resumen:
            resumen[docente] = {
                "docente": docente,
                "cantidad": 0,
                "minutos": 0,
            }

        resumen[docente]["cantidad"] += 1
        resumen[docente]["minutos"] += int(round(minutos))

        if docente not in programas_por_docente:
            programas_por_docente[docente] = []

        if programa:
            programas_por_docente[docente].append(programa)

    lista = []

    for docente, datos in resumen.items():
        impacto = impacto_docente(datos["cantidad"], datos["minutos"])

        if impacto == "Bajo":
            continue

        semaforo = "bajo"
        semaforo_texto = "Impacto leve"

        if impacto == "Moderado":
            semaforo = "medio"
            semaforo_texto = "Impacto moderado"
        elif impacto == "Critico":
            semaforo = "alto"
            semaforo_texto = "Impacto crítico"

        programa_predominante = "-"
        programas = programas_por_docente.get(docente, [])
        if programas:
            programa_predominante = Counter(programas).most_common(1)[0][0]

        lista.append({
            "docente": docente,
            "programa": programa_predominante,
            "cantidad": datos["cantidad"],
            "minutos": datos["minutos"],
            "horas": round(datos["minutos"] / 60, 1),
            "impacto": impacto,
            "semaforo": semaforo,
            "semaforo_texto": semaforo_texto,
        })

    if criterio_orden == "minutos":
        lista.sort(key=lambda x: (-x["minutos"], -x["cantidad"], x["docente"]))
    else:
        lista.sort(key=lambda x: (-x["cantidad"], -x["minutos"], x["docente"]))

    return lista[:5]


def normalizar_insights_para_pdf(insights):
    salida = []

    for item in insights:
        if isinstance(item, dict):
            titulo = str(item.get("titulo", "")).strip()
            texto = str(item.get("texto", "")).strip()

            if titulo and texto:
                salida.append(f"{titulo}: {texto}")
            elif texto:
                salida.append(texto)
            elif titulo:
                salida.append(titulo)

        elif isinstance(item, str):
            texto = item.strip()
            if texto:
                salida.append(texto)

    return salida


def resumir_dimension(registros, campo, limite=5):
    resumen = {}

    for item in registros:
        nombre = texto_seguro(item.get(campo), "Sin dato")
        minutos = int(round(numero_seguro(item.get("minutos_atraso"))))

        if nombre not in resumen:
            resumen[nombre] = {
                "nombre": nombre,
                "casos": 0,
                "minutos": 0,
            }

        resumen[nombre]["casos"] += 1
        resumen[nombre]["minutos"] += minutos

    lista = list(resumen.values())
    lista.sort(key=lambda x: (-x["minutos"], -x["casos"], x["nombre"]))
    return lista[:limite]


def construir_conclusiones_docente(
    docente,
    total_registros,
    total_atrasos,
    minutos_totales,
    promedio,
    mediana,
    max_atraso,
    porcentaje_critico,
    top_bloques,
    top_asignaturas,
    top_secciones,
):
    conclusiones = []

    if total_registros <= 0:
        return [f"No se encontraron registros analizables para {docente}."]

    conclusiones.append(
        f"{docente} presenta {total_atrasos} atrasos efectivos dentro de {total_registros} registros analizados, acumulando {minutos_totales} minutos de atraso."
    )

    conclusiones.append(
        f"El promedio de atraso es de {promedio} minutos, con mediana de {mediana} minutos y un máximo de {max_atraso} minutos."
    )

    if porcentaje_critico >= 30:
        conclusiones.append(
            f"Existe una concentración alta de eventos críticos: el {porcentaje_critico}% de los atrasos se ubica en nivel crítico."
        )
    elif porcentaje_critico > 0:
        conclusiones.append(
            f"Se observan eventos críticos, equivalentes al {porcentaje_critico}% del total de atrasos del docente."
        )
    else:
        conclusiones.append(
            "No se observan atrasos en nivel crítico dentro del período analizado."
        )

    if top_bloques:
        bloque = top_bloques[0]
        conclusiones.append(
            f"El mayor impacto se concentra en bloque {bloque['nombre']}, con {bloque['casos']} eventos y {bloque['minutos']} minutos acumulados."
        )

    if top_asignaturas:
        asignatura = top_asignaturas[0]
        conclusiones.append(
            f"La asignatura con mayor exposición es {asignatura['nombre']}, con {asignatura['casos']} eventos y {asignatura['minutos']} minutos acumulados."
        )

    if top_secciones:
        seccion = top_secciones[0]
        conclusiones.append(
            f"La sección más afectada es {seccion['nombre']}, con {seccion['casos']} eventos y {seccion['minutos']} minutos acumulados."
        )

    return conclusiones


def obtener_nivel_ejecutivo(promedio, porcentaje_critico, max_atraso, total_atrasos):
    if total_atrasos <= 0:
        return "Controlado", "Comportamiento sin atrasos relevantes en el período analizado."

    if promedio >= 15 or porcentaje_critico >= 30 or max_atraso >= 45:
        return "Crítico", "El caso requiere seguimiento prioritario por recurrencia y severidad de los atrasos."

    if promedio >= 10 or porcentaje_critico >= 10 or max_atraso >= 20:
        return "Atención", "El caso presenta señales que justifican monitoreo y seguimiento focalizado."

    return "Controlado", "El comportamiento del docente se mantiene dentro de rangos relativamente contenidos."


@acceso_restringido_atrasos
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

            total_registros = resultado.get("total_registros", 0)
            total_atrasos = resultado.get("total_atrasos", 0)
            promedio_atraso = resultado.get("promedio_atraso", 0)
            top_docentes = resultado.get("top_docentes", [])
            detalle_visible = resultado.get("detalle_visible", [])
            detalle_completo = resultado.get("detalle_completo", [])
            insights = resultado.get("insights", [])

            porcentaje_atrasos = round((total_atrasos / total_registros) * 100, 1) if total_registros else 0
            estado_global = obtener_estado_global(
                total_registros=total_registros,
                total_atrasos=total_atrasos,
                promedio_atraso=promedio_atraso,
                top_docentes=top_docentes
            )

            top_docentes_pdf = construir_ranking_para_pdf(
                detalle=detalle_completo,
                criterio_orden=criterio_orden
            )
            insights_pdf = normalizar_insights_para_pdf(insights)

            contexto["mensaje"] = (
                f"Archivo procesado correctamente. "
                f"Se analizaron {total_registros} registros sin guardar en la base de datos."
            )

            contexto["total_registros"] = total_registros
            contexto["total_atrasos"] = total_atrasos
            contexto["total_a_tiempo"] = resultado.get("total_a_tiempo", 0)
            contexto["total_sin_retiro"] = resultado.get("total_sin_retiro", 0)
            contexto["total_sin_bloque"] = resultado.get("total_sin_bloque", 0)
            contexto["promedio_atraso"] = promedio_atraso
            contexto["top_docentes"] = top_docentes
            contexto["detalle"] = detalle_visible
            contexto["detalle_visible"] = detalle_visible
            contexto["detalle_completo"] = detalle_completo
            contexto["insights"] = insights
            contexto["criterio_orden"] = resultado.get("criterio_orden", criterio_orden)

            contexto["detalle_visible_json"] = detalle_visible
            contexto["detalle_completo_json"] = detalle_completo
            contexto["top_docentes_json"] = top_docentes

            request.session["analisis_atrasos"] = {
                "archivo": archivo.name,
                "estado_global": estado_global,
                "total_registros": total_registros,
                "total_atrasos": total_atrasos,
                "porcentaje_atrasos": porcentaje_atrasos,
                "promedio_atraso": promedio_atraso,
                "criterio_orden": criterio_orden,
                "top_docentes_pdf": top_docentes_pdf,
                "insights_pdf": insights_pdf,
                "detalle_visible": detalle_visible,
                "detalle_completo": detalle_completo,
                "top_docentes": top_docentes,
            }

        except Exception as error:
            contexto["error"] = f"Ocurrió un error al procesar el archivo: {error}"
            contexto["criterio_orden"] = criterio_orden

    else:
        contexto["criterio_orden"] = criterio_orden

    return render(request, "atrasos/inicio.html", contexto)


def generar_reporte_pdf(request):
    datos = request.session.get("analisis_atrasos")

    if not datos:
        return HttpResponse("No hay datos para generar el reporte.", status=400)

    estado_global = datos.get("estado_global", "Controlado")

    clase_estado = "estado-controlado"
    if estado_global == "Crítico":
        clase_estado = "estado-critico"
    elif estado_global == "Atención":
        clase_estado = "estado-atencion"

    contexto = {
        "fecha": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "archivo": datos.get("archivo", "Sin nombre"),
        "estado_global": estado_global,
        "clase_estado": clase_estado,
        "total_registros": datos.get("total_registros", 0),
        "total_atrasos": datos.get("total_atrasos", 0),
        "porcentaje_atrasos": datos.get("porcentaje_atrasos", 0),
        "promedio_atraso": datos.get("promedio_atraso", 0),
        "top_docentes": datos.get("top_docentes_pdf", []),
        "insights": datos.get("insights_pdf", []),
        "acciones_sugeridas": [
            "Priorizar seguimiento sobre docentes con mayor recurrencia y minutos acumulados.",
            "Revisar patrones de atraso en los casos con impacto moderado o crítico.",
            "Dar trazabilidad específica a registros sin retiro o con observaciones relevantes.",
        ],
    }

    pdf = generar_pdf_reporte(contexto)

    if not pdf:
        return HttpResponse("No fue posible generar el PDF.", status=500)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reporte_atrasos.pdf"'
    return response


@login_required
def reporte_docente(request):
    datos = request.session.get("analisis_atrasos")

    if not datos:
        return redirect("atrasos:inicio")

    docente = texto_seguro(request.GET.get("docente"), "")
    if not docente:
        return redirect("atrasos:inicio")

    detalle = datos.get("detalle_completo", [])

    registros = [
        r for r in detalle
        if texto_seguro(r.get("docente"), "") == docente
    ]

    if not registros:
        raise Http404("Docente sin registros")

    total_registros = len(registros)
    minutos_lista = [
        numero_seguro(r.get("minutos_atraso"))
        for r in registros
        if numero_seguro(r.get("minutos_atraso")) > 0
    ]

    total_atrasos = len(minutos_lista)
    minutos_totales = int(round(sum(minutos_lista)))
    horas_totales = round(minutos_totales / 60, 1)
    promedio = round((sum(minutos_lista) / len(minutos_lista)), 1) if minutos_lista else 0
    mediana = round(median(minutos_lista), 1) if minutos_lista else 0
    max_atraso = int(round(max(minutos_lista))) if minutos_lista else 0
    min_atraso = int(round(min(minutos_lista))) if minutos_lista else 0

    leves = len([m for m in minutos_lista if 5 <= m <= 9])
    moderados = len([m for m in minutos_lista if 10 <= m <= 14])
    criticos = len([m for m in minutos_lista if m >= 15])

    porcentaje_leve = round((leves / total_atrasos) * 100, 1) if total_atrasos else 0
    porcentaje_moderado = round((moderados / total_atrasos) * 100, 1) if total_atrasos else 0
    porcentaje_critico = round((criticos / total_atrasos) * 100, 1) if total_atrasos else 0

    registros_con_minutos = [r for r in registros if numero_seguro(r.get("minutos_atraso")) > 0]

    top_bloques = resumir_dimension(registros_con_minutos, "bloque_numero", limite=5)
    top_asignaturas = resumir_dimension(registros_con_minutos, "asignatura", limite=5)
    top_secciones = resumir_dimension(registros_con_minutos, "seccion", limite=5)
    top_programas = resumir_dimension(registros_con_minutos, "programa_estudio", limite=5)

    nivel_ejecutivo, lectura_ejecutiva = obtener_nivel_ejecutivo(
        promedio=promedio,
        porcentaje_critico=porcentaje_critico,
        max_atraso=max_atraso,
        total_atrasos=total_atrasos,
    )

    conclusiones = construir_conclusiones_docente(
        docente=docente,
        total_registros=total_registros,
        total_atrasos=total_atrasos,
        minutos_totales=minutos_totales,
        promedio=promedio,
        mediana=mediana,
        max_atraso=max_atraso,
        porcentaje_critico=porcentaje_critico,
        top_bloques=top_bloques,
        top_asignaturas=top_asignaturas,
        top_secciones=top_secciones,
    )

    contexto = {
        "fecha_generacion": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "docente": docente,
        "nivel_ejecutivo": nivel_ejecutivo,
        "lectura_ejecutiva": lectura_ejecutiva,
        "total_registros": total_registros,
        "total_atrasos": total_atrasos,
        "minutos_totales": minutos_totales,
        "horas_totales": horas_totales,
        "promedio": promedio,
        "mediana": mediana,
        "max_atraso": max_atraso,
        "min_atraso": min_atraso,
        "leves": leves,
        "moderados": moderados,
        "criticos": criticos,
        "porcentaje_leve": porcentaje_leve,
        "porcentaje_moderado": porcentaje_moderado,
        "porcentaje_critico": porcentaje_critico,
        "top_bloques": top_bloques,
        "top_asignaturas": top_asignaturas,
        "top_secciones": top_secciones,
        "top_programas": top_programas,
        "conclusiones": conclusiones,
        "docente_urlencoded": docente,
    }

    if request.GET.get("formato") == "pdf":
        pdf = generar_pdf_reporte_docente(contexto)

        if not pdf:
            return HttpResponse("No fue posible generar el PDF del docente.", status=500)

        nombre_archivo = f"reporte_docente_{docente.replace(' ', '_')}.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
        return response

    return render(request, "atrasos/reporte_docente.html", contexto)