from django.shortcuts import redirect


ROLES_PERMITIDOS_ATRASOS = [
    "Directora Académica",
    "Director de Carrera",
    "Coordinador",
    "Jefa de Coordinación",
]


def usuario_tiene_rol_permitido(usuario):
    if not usuario.is_authenticated:
        return False

    if usuario.is_superuser:
        return True

    nombres_grupos_usuario = set(
        usuario.groups.values_list("name", flat=True)
    )

    return any(
        rol in nombres_grupos_usuario
        for rol in ROLES_PERMITIDOS_ATRASOS
    )


def acceso_restringido_atrasos(vista):
    def vista_envuelta(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")

        if not usuario_tiene_rol_permitido(request.user):
            return redirect("acceso_denegado")

        return vista(request, *args, **kwargs)

    return vista_envuelta