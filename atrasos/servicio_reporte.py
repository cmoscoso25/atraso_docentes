from io import BytesIO

from django.template.loader import render_to_string
from xhtml2pdf import pisa


def generar_pdf_desde_template(template_name, contexto):
    html = render_to_string(template_name, contexto)

    resultado = BytesIO()

    pdf = pisa.CreatePDF(
        src=html,
        dest=resultado,
        encoding="utf-8"
    )

    if pdf.err:
        return None

    return resultado.getvalue()


def generar_pdf_reporte(contexto):
    return generar_pdf_desde_template("atrasos/reporte_pdf.html", contexto)


def generar_pdf_reporte_docente(contexto):
    return generar_pdf_desde_template("atrasos/reporte_docente_pdf.html", contexto)