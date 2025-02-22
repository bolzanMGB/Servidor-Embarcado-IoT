from django.shortcuts import render
from django.core.cache import cache
import matplotlib
matplotlib.use('Agg')  # Backend não interativo
import matplotlib.pyplot as plt
import io
import base64
import numpy as np  # Para cálculos estatísticos

def grafico_view(request):
    # Pegar os dados do cache
    dados_grafico = cache.get("dados_grafico", [])
    if not dados_grafico:
        dados_grafico = []  # Lista vazia se nada estiver no cache

    # Extrair timestamps e médias
    timestamps = [dado["timestamp"] for dado in dados_grafico]
    medias = [dado["media"] for dado in dados_grafico]

    if not medias:  # Se não houver dados, retornar gráfico vazio
        plt.figure(figsize=(10, 5))
        plt.title("Gráfico em Tempo Real (Sem Dados)")
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        imagem_png = buffer.getvalue()
        buffer.close()
        plt.close()
        imagem_base64 = base64.b64encode(imagem_png).decode("utf-8")
        return render(request, "grafico.html", {"imagem_grafico": imagem_base64})

    # Cálculos para CEP
    media_geral = np.mean(medias)  # Média geral (X̄)
    desvio_padrao = np.std(medias)  # Desvio padrão (σ)
    lcs = media_geral + 3 * desvio_padrao  # Limite de Controle Superior (X̄ + 3σ)
    lci = media_geral - 3 * desvio_padrao  # Limite de Controle Inferior (X̄ - 3σ)

    # Criar o gráfico
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, medias, marker='o', color='blue', label='Valores do Sensor')

    # Adicionar linhas de controle
    plt.axhline(y=media_geral, color='green', linestyle='--', label=f'Média Geral ({media_geral:.2f})')
    plt.axhline(y=lcs, color='red', linestyle='--', label=f'LCS ({lcs:.2f})')
    plt.axhline(y=lci, color='red', linestyle='--', label=f'LCI ({lci:.2f})')

    # Destacar pontos fora dos limites (opcional)
    for i, media in enumerate(medias):
        if media > lcs or media < lci:
            plt.plot(timestamps[i], media, 'ro', markersize=10, label='Fora de Controle' if i == 0 else "")

    # Configurações do gráfico
    plt.xlabel("Tempo")
    plt.ylabel("Média")
    plt.title("Gráfico de Controle Estatístico de Processo (CEP)")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)

    # Salvar como imagem
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    imagem_png = buffer.getvalue()
    buffer.close()
    plt.close()

    # Codificar em base64
    imagem_base64 = base64.b64encode(imagem_png).decode("utf-8")

    return render(request, "grafico.html", {
        "imagem_grafico": imagem_base64,
        "dados_grafico": dados_grafico
    })