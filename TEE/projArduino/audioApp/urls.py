from django.urls import path
from . import views

urlpatterns = [
    path("grafico/", views.grafico_view, name="grafico"),
    path("grafico_r/", views.grafico_r_view, name="grafico_r"),  # Nova rota
]