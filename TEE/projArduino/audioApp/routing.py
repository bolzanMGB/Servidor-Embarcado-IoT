from django.urls import re_path
from .consumers import DadosConsumer

websocket_urlpatterns = [
    re_path(r'ws/dados/$', DadosConsumer.as_asgi()),
]
