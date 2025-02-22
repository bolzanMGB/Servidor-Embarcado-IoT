import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from datetime import datetime

class DadosConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("🔗 WebSocket conectado!")

    async def disconnect(self, close_code):
        print("❌ WebSocket desconectado. Código:", close_code)

    async def receive(self, text_data):
        print("📥 Iniciando recebimento de dados...")
        try:
            data = json.loads(text_data)
            print(f"📩 Dados recebidos no WebSocket: {data}")
        except json.JSONDecodeError as e:
            print(f"⚠️ Erro ao decodificar JSON: {e}")
            return

        # Pegar a lista existente do cache ou iniciar uma nova
        print("🔍 Acessando cache para 'dados_grafico'...")
        dados_existentes = cache.get("dados_grafico", [])
        if not isinstance(dados_existentes, list):
            dados_existentes = []
            print("ℹ️ Cache estava vazio ou inválido, iniciando nova lista.")

        # Adicionar o novo dado à lista
        novo_dado = {
            "media": data["media"],
            "dados_originais": data["dados_originais"],
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        dados_existentes.append(novo_dado)
        print(f"➕ Novo dado adicionado: {novo_dado}")

        # Limitar a lista a 20 entradas
        if len(dados_existentes) > 20:
            dados_existentes.pop(0)
            print("✂️ Removido o dado mais antigo. Tamanho atual:", len(dados_existentes))

        # Salvar a lista atualizada no cache
        cache.set("dados_grafico", dados_existentes, timeout=300)
        print(f"📤 Dados salvos no cache: {dados_existentes}")

        # Verificar alertas no cache
        print("🔍 Verificando alertas no cache...")
        alerta_vermelho = cache.get("alerta_vermelho", False)
        alerta_amarelo = cache.get("alerta_amarelo", False)
        print(f"ℹ️ Alertas lidos: vermelho={alerta_vermelho}, amarelo={alerta_amarelo}")

        # Enviar os alertas de volta ao dispositivo conectado
        resposta = {
            "media": data["media"],
            "dados_originais": data["dados_originais"],
            "alerta_vermelho": alerta_vermelho,
            "alerta_amarelo": alerta_amarelo
        }
        print(f"📦 Preparando resposta: {resposta}")
        
        try:
            await self.send(text_data=json.dumps(resposta))
            print(f"🚨 Alertas enviados: vermelho={alerta_vermelho}, amarelo={alerta_amarelo}")
        except Exception as e:
            print(f"❌ Erro ao enviar resposta via WebSocket: {e}")
