import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from datetime import datetime

class DadosConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("🔗 WebSocket conectado!")

    async def disconnect(self, close_code):
        print("❌ WebSocket desconectado")

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(f"📩 Dados recebidos no WebSocket: {data}")

        # Pegar a lista existente do cache
        dados_existentes = cache.get("dados_grafico", [])
        if not isinstance(dados_existentes, list):
            dados_existentes = []

        # Adicionar o novo dado
        novo_dado = {
            "media": data["media"],
            "dados_originais": data["dados_originais"],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        dados_existentes.append(novo_dado)

        # Limitar a 20 entradas
        if len(dados_existentes) > 20:
            dados_existentes.pop(0)

        # Atualizar o cache
        cache.set("dados_grafico", dados_existentes, timeout=300)
        print(f"📤 Dados salvos no cache: {dados_existentes}")

        # Notificar o frontend sobre a atualização
        await self.send(text_data=json.dumps({"atualizado": True}))