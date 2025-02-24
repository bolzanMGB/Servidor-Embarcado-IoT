import numpy as np
import socket
import websocket
import json
import RPi.GPIO as GPIO
import threading
import time

# Configuração dos LEDs
LED_VERMELHO = 17  # Pino GPIO para LED vermelho
LED_AMARELO = 18  # Pino GPIO para LED amarelo
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_VERMELHO, GPIO.OUT)
GPIO.setup(LED_AMARELO, GPIO.OUT)

# Definir o tamanho do bloco de dados
TAMANHO_BLOCO = 5
valores_acumulados = []  # Lista para armazenar os valores recebidos

# Variáveis globais para os alertas e o WebSocket
alerta_vermelho = False
alerta_amarelo = False
ws_global = None  # Para armazenar a conexão WebSocket

# Função para processar os dados
def processar_dados(valores):
    media = np.mean(valores)
    desvio_padrao = np.std(valores)
    return {'media': float(media), 'desvio_padrao': float(desvio_padrao), 'dados_originais': valores}

# Funções de callback do WebSocket
def on_message(ws, message):
    global alerta_vermelho, alerta_amarelo
    try:
        data = json.loads(message)
        print(f"📩 Resposta recebida do servidor: {data}")
        
        # Atualizar os alertas
        alerta_vermelho = data.get("alerta_vermelho", False)
        alerta_amarelo = data.get("alerta_amarelo", False)
        
        # Controlar os LEDs
        GPIO.output(LED_VERMELHO, GPIO.HIGH if alerta_vermelho else GPIO.LOW)
        GPIO.output(LED_AMARELO, GPIO.HIGH if alerta_amarelo else GPIO.LOW)
        print(f"🚨 LEDs atualizados: Vermelho={alerta_vermelho}, Amarelo={alerta_amarelo}")
    except Exception as e:
        print(f"Erro ao processar mensagem do servidor: {e}")

def on_error(ws, error):
    print(f"❌ Erro no WebSocket: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 WebSocket fechado: {close_msg}")
    GPIO.cleanup()

def on_open(ws):
    global ws_global
    ws_global = ws  # Armazenar a conexão para uso posterior
    print("🔗 WebSocket conectado ao servidor!")

# Função para gerenciar o WebSocket em uma thread separada
def iniciar_websocket():
    ws_url = "ws://192.168.0.6:8000/ws/dados/"
    ws = websocket.WebSocketApp(ws_url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

# Função para enviar dados via WebSocket
def enviar_dados_websocket(dados):
    global ws_global
    try:
        if ws_global and ws_global.sock and ws_global.sock.connected:
            ws_global.send(json.dumps(dados))
            print(f"📤 Dados enviados: {dados}")
        else:
            print("⚠ WebSocket não está conectado!")
    except Exception as e:
        print(f"Erro ao enviar dados via WebSocket: {e}")

# Função para receber dados do Arduino
def receber_dados_arduino():
    host = "192.168.0.15"  # IP da Raspberry Pi
    port = 5000  # Porta do Arduino

    # Iniciar o WebSocket em uma thread separada
    ws_thread = threading.Thread(target=iniciar_websocket)
    ws_thread.daemon = True
    ws_thread.start()
    time.sleep(2)  # Dar tempo para o WebSocket conectar

    # Criar o socket TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Esperando por conexão na porta {port}...")

    client_socket, client_address = server_socket.accept()
    print(f"Conexão recebida de {client_address}")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            dados_recebidos = data.decode().strip()
            print(f"Valor analógico recebido do Arduino: {dados_recebidos}")

            try:
                valor = int(dados_recebidos)
                valores_acumulados.append(valor)
            except ValueError:
                print(f"Valor recebido inválido: {dados_recebidos}")

            if len(valores_acumulados) >= TAMANHO_BLOCO:
                dados_processados = processar_dados(valores_acumulados)
                enviar_dados_websocket(dados_processados)
                valores_acumulados.clear()

    finally:
        client_socket.close()
        server_socket.close()
        GPIO.cleanup()

# Iniciar a recepção dos dados
if _name_ == "_main_":
    receber_dados_arduino()