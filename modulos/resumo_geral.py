import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta

# Importa funções utilitárias já existentes
from utilitarios import calcular_estatisticas, sanitizar_coluna

COLUNAS_ANALISE = [
    "IC_SPDMTR(km/h)",
    "RPM(1/min)",
    "ECT_GAUGE(Â°C)",
    "SHRTFT1(%)",
    "LONGFT1(%)",
    "AF_RATIO(:1)",
    "LMD_EGO1(:1)",
    "FUELPW(ms)",
    "FUELLVL(%)"
]

def analisar(df, modelo, combustivel, valores_ideais):
    """
    Calcula o resumo geral de desempenho do veículo.
    """
    df = df.copy()

    # Dicionário de resultados
    estatisticas = {}

    # Calcula estatísticas básicas para as colunas de interesse
    for coluna in COLUNAS_ANALISE:
        if coluna not in df.columns:
            continue

        serie = sanitizar_coluna(df[coluna])
        if serie.dropna().empty:
            continue

        stats = calcular_estatisticas(serie)
        estatisticas[coluna] = stats

    # Tempo total de viagem (baseado na coluna time(ms) se existir)
    tempo_total = None
    if "time(ms)" in df.columns:
        t_min = pd.to_numeric(df["time(ms)"], errors="coerce").min()
        t_max = pd.to_numeric(df["time(ms)"], errors="coerce").max()
        if pd.notna(t_min) and pd.notna(t_max):
            tempo_total = timedelta(milliseconds=int(t_max - t_min))

    # Distância total percorrida (ODOMETER ou TRIP_ODOMETER)
    distancia = None
    for col in ["ODOMETER(km)", "TRIP_ODOMETER(km)", "TRIP_ODOM(km)"]:
        if col in df.columns:
            serie = sanitizar_coluna(df[col])
            if not serie.dropna().empty:
                distancia = serie.max() - serie.min()
                break

    return {
        "status": "OK",
        "titulo": "Resumo Geral do Desempenho",
        "mensagem": "Resumo calculado com sucesso.",
        "estatisticas": estatisticas,
        "tempo_total": tempo_total,
        "distancia": distancia
    }


def exibir(resultado):
    """
    Exibe o resumo geral no Streamlit de forma organizada
    """
    st.markdown(f"## 📈 {resultado['titulo']}")

    # Exibe tempo total e distância
    col1, col2 = st.columns(2)
    tempo_str = str(resultado["tempo_total"]) if resultado["tempo_total"] else "N/A"
    distancia_str = f"{resultado['distancia']:.2f} km" if resultado["distancia"] else "N/A"

    col1.metric("⏱️ Tempo Total da Viagem", tempo_str)
    col2.metric("🛣️ Distância Percorrida", distancia_str)

    st.markdown("---")
    st.markdown("### Estatísticas Básicas das Principais Variáveis")

    # Exibe estatísticas das colunas
    for coluna, stats in resultado["estatisticas"].items():
        st.markdown(f"**{coluna}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Mínimo", f"{stats['min']:.2f}")
        c2.metric("Média", f"{stats['mean']:.2f}")
        c3.metric("Máximo", f"{stats['max']:.2f}")
        st.markdown("---")
