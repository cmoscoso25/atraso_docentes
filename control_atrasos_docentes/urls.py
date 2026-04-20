from django.contrib import admin
from django.contrib.auth import views as vistas_autenticacion
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "login/",
        vistas_autenticacion.LoginView.as_view(
            template_name="registration/login.html"
        ),
        name="login",
    ),

    path(
        "logout/",
        vistas_autenticacion.LogoutView.as_view(),
        name="logout",
    ),

    path(
        "password-change/",
        vistas_autenticacion.PasswordChangeView.as_view(
            template_name="registration/password_change.html"
        ),
        name="password_change",
    ),

    path(
        "password-change/done/",
        vistas_autenticacion.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),

    path(
        "password-reset/",
        TemplateView.as_view(
            template_name="registration/password_reset_help.html"
        ),
        name="password_reset",
    ),

    path("", include("atrasos.urls")),
]