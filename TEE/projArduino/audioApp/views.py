from django.shortcuts import render
from django.core.cache import cache
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

def grafico_view(request):
    # Pegar os dados do cache
    dados_grafico = cache.get("dados_grafico", [])
    if not dados_grafico:
        dados_grafico = []  # Lista vazia se nada estiver no cache

    # Extrair timestamps e médias
    timestamps = [dado["timestamp"] for dado in dados_grafico]
    medias = [dado["media"] for dado in dados_grafico]

    if not medias:  # Se não houver dados, retornar gráfico vazio
        plt.figure(figsize=(12, 6))
        plt.title("Gráfico em Tempo Real (Sem Dados)", fontsize=14, weight='bold')
        plt.xlabel("Tempo", fontsize=12)
        plt.ylabel("Média", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        imagem_png = buffer.getvalue()
        buffer.close()
        plt.close()
        imagem_base64 = base64.b64encode(imagem_png).decode("utf-8")
        return render(request, "grafico.html", {"imagem_grafico": imagem_base64})

    # Cálculos para CEP com n = 5
    A2 = 0.577  # Fator A2 para amostras de tamanho 5
    media_geral = np.mean(medias)
    desvio_padrao = np.std(medias)
    lcs = media_geral + A2 * desvio_padrao
    lci = media_geral - A2 * desvio_padrao
    sigma_1_pos = media_geral + desvio_padrao
    sigma_1_neg = media_geral - desvio_padrao
    sigma_2_pos = media_geral + 2 * desvio_padrao
    sigma_2_neg = media_geral - 2 * desvio_padrao

    # Verificar as regras do Western Electric
    alerta_vermelho = False  # Regra 1
    alerta_amarelo = False  # Regras 2, 3, 4
    alertas_vermelhos = []  # Para o gráfico
    alertas_amarelos = []  # Para o gráfico

    for i, media in enumerate(medias):
        # Regra 1: Ponto fora de LCS ou LCI
        if media > lcs or media < lci:
            alerta_vermelho = True
            alertas_vermelhos.append((timestamps[i], media))
            continue

        # Regra 2: 2 de 3 pontos consecutivos fora de 2σ
        if i >= 2:
            pontos_ultimos_3 = medias[i-2:i+1]
            fora_2sigma_pos = sum(1 for m in pontos_ultimos_3 if m > sigma_2_pos)
            fora_2sigma_neg = sum(1 for m in pontos_ultimos_3 if m < sigma_2_neg)
            if fora_2sigma_pos >= 2 or fora_2sigma_neg >= 2:
                alerta_amarelo = True
                alertas_amarelos.append((timestamps[i], media))

        # Regra 3: 4 de 5 pontos consecutivos fora de 1σ
        if i >= 4:
            pontos_ultimos_5 = medias[i-4:i+1]
            fora_1sigma_pos = sum(1 for m in pontos_ultimos_5 if m > sigma_1_pos)
            fora_1sigma_neg = sum(1 for m in pontos_ultimos_5 if m < sigma_1_neg)
            if fora_1sigma_pos >= 4 or fora_1sigma_neg >= 4:
                alerta_amarelo = True
                alertas_amarelos.append((timestamps[i], media))

        # Regra 4: 8 pontos consecutivos no mesmo lado da média
        if i >= 7:
            pontos_ultimos_8 = medias[i-7:i+1]
            todos_acima = all(m > media_geral for m in pontos_ultimos_8)
            todos_abaixo = all(m < media_geral for m in pontos_ultimos_8)
            if todos_acima or todos_abaixo:
                alerta_amarelo = True
                alertas_amarelos.append((timestamps[i], media))

    # Salvar os estados no cache para o Arduino
    cache.set("alerta_vermelho", alerta_vermelho, timeout=300)
    cache.set("alerta_amarelo", alerta_amarelo, timeout=300)

    # Criar o gráfico
    plt.figure(figsize=(12, 6), facecolor='white')
    plt.plot(timestamps, medias, marker='o', color='#1f77b4', linewidth=2, label='Valores do Sensor')

    # Adicionar linhas de controle
    plt.axhline(y=media_geral, color='green', linestyle='-', linewidth=1.5, label=f'Média Geral ({media_geral:.2f})')
    plt.axhline(y=lcs, color='red', linestyle='--', linewidth=1.5, label=f'LCS ({lcs:.2f})')
    plt.axhline(y=lci, color='red', linestyle='--', linewidth=1.5, label=f'LCI ({lci:.2f})')
    plt.axhline(y=sigma_1_pos, color='orange', linestyle=':', linewidth=1, alpha=0.5, label=f'+1σ ({sigma_1_pos:.2f})')
    plt.axhline(y=sigma_1_neg, color='orange', linestyle=':', linewidth=1, alpha=0.5, label=f'-1σ ({sigma_1_neg:.2f})')
    plt.axhline(y=sigma_2_pos, color='yellow', linestyle=':', linewidth=1, alpha=0.5, label=f'+2σ ({sigma_2_pos:.2f})')
    plt.axhline(y=sigma_2_neg, color='yellow', linestyle=':', linewidth=1, alpha=0.5, label=f'-2σ ({sigma_2_neg:.2f})')

    # Destacar pontos com alertas
    for timestamp, media in alertas_vermelhos:
        plt.plot(timestamp, media, 'ro', markersize=10, label='Fora de Controle (Regra 1)' if (timestamp, media) == alertas_vermelhos[0] else "")
    for timestamp, media in alertas_amarelos:
        plt.plot(timestamp, media, 'yo', markersize=10, label='Alerta (Regras 2-4)' if (timestamp, media) == alertas_amarelos[0] else "")

    # Configurações estéticas
    plt.xlabel("Tempo", fontsize=12, weight='bold')
    plt.ylabel("Média", fontsize=12, weight='bold')
    plt.title("Gráfico de Controle (CEP) - Western Electric Rules", fontsize=14, weight='bold', pad=10)
    plt.legend(loc='best', fontsize=10, frameon=True, shadow=True)
    plt.grid(True, linestyle='--', alpha=0.5, color='gray')
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)
    plt.tight_layout()

    # Salvar como imagem
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
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


def grafico_r_view(request):
    # Pegar os dados do cache
    dados_grafico = cache.get("dados_grafico", [])
    if not dados_grafico:
        dados_grafico = []  # Lista vazia se nada estiver no cache

    # Extrair timestamps e amplitudes (ranges)
    timestamps = [dado["timestamp"] for dado in dados_grafico]
    amplitudes = [max(dado["dados_originais"]) - min(dado["dados_originais"]) for dado in dados_grafico]

    if not amplitudes:  # Se não houver dados, retornar gráfico vazio
        plt.figure(figsize=(12, 6))
        plt.title("Gráfico R - Amplitude (Sem Dados)", fontsize=14, weight='bold')
        plt.xlabel("Tempo", fontsize=12)
        plt.ylabel("Amplitude", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        imagem_png = buffer.getvalue()
        buffer.close()
        plt.close()
        imagem_base64 = base64.b64encode(imagem_png).decode("utf-8")
        return render(request, "grafico_r.html", {"imagem_grafico": imagem_base64})

    # Cálculos para o gráfico R (n = 5)
    media_amplitudes = np.mean(amplitudes)  # Média das amplitudes (R̄)
    D4 = 2.114  # Fator para LCS com n = 5
    D3 = 0      # Fator para LCI com n = 5 (sempre 0 para n ≤ 6)
    lcs = D4 * media_amplitudes  # Limite de Controle Superior (D4 * R̄)
    lci = D3 * media_amplitudes  # Limite de Controle Inferior (0 * R̄ = 0)

    # Criar o gráfico
    plt.figure(figsize=(12, 6), facecolor='white')
    plt.plot(timestamps, amplitudes, marker='o', color='#1f77b4', linewidth=2, label='Amplitude da Amostra')

    # Adicionar linhas de controle
    plt.axhline(y=media_amplitudes, color='green', linestyle='-', linewidth=1.5, label=f'Média das Amplitudes ({media_amplitudes:.2f})')
    plt.axhline(y=lcs, color='red', linestyle='--', linewidth=1.5, label=f'LCS ({lcs:.2f})')
    plt.axhline(y=lci, color='red', linestyle='--', linewidth=1.5, label=f'LCI ({lci:.2f})')

    # Destacar pontos fora dos limites
    for i, amplitude in enumerate(amplitudes):
        if amplitude > lcs or amplitude < lci:
            plt.plot(timestamps[i], amplitude, 'ro', markersize=10, label='Fora de Controle' if i == 0 else "")

    # Configurações estéticas
    plt.xlabel("Tempo", fontsize=12, weight='bold')
    plt.ylabel("Amplitude", fontsize=12, weight='bold')
    plt.title("Gráfico de Controle R - Amplitude (n=5)", fontsize=14, weight='bold', pad=10)
    plt.legend(loc='best', fontsize=10, frameon=True, shadow=True)
    plt.grid(True, linestyle='--', alpha=0.5, color='gray')
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)
    plt.tight_layout()

    # Salvar como imagem
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
    buffer.seek(0)
    imagem_png = buffer.getvalue()
    buffer.close()
    plt.close()

    # Codificar em base64
    imagem_base64 = base64.b64encode(imagem_png).decode("utf-8")

    return render(request, "grafico_r.html", {
        "imagem_grafico": imagem_base64,
        "dados_grafico": dados_grafico
    })