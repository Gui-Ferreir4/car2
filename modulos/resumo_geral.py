import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta

# Importa utilitários já existentes
from modulos.utilitarios import (
    sanitizar_coluna,
    calcular_estatisticas,
    avaliar_status,
    interpretar_status
)

# Colunas analisadas no resumo geral
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


def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Calcula o resumo geral do desempenho do veículo, incluindo estatísticas,
    tempo total, distância percorrida e alertas baseados no JSON de valores ideais.
    """
    df = df.copy()
    estatisticas = {}
    alertas = []

    # Tempo total de viagem
    tempo_total = None
    if "time(ms)" in df.columns:
        t_min = pd.to_numeric(df["time(ms)"], errors="coerce").min()
        t_max = pd.to_numeric(df["time(ms)"], errors="coerce").max()
        if pd.notna(t_min) and pd.notna(t_max):
            tempo_total = timedelta(milliseconds=int(t_max - t_min))

    # Distância percorrida
    distancia = None
    for col in ["ODOMETER(km)", "TRIP_ODOMETER(km)", "TRIP_ODOM(km)"]:
        if col in df.columns:
            serie = sanitizar_coluna(df, col)
            if not serie.empty:
                distancia = float(serie.max() - serie.min())
                break

    # Obtém valores ideais para o modelo e combustível
    faixa_ideais = (
        valores_ideais.get(modelo, {}).get(combustivel.lower(), {})
    )

    # Calcula estatísticas e avalia status
    for coluna in COLUNAS_ANALISE:
        if coluna not in df.columns:
            continue

        serie = sanitizar_coluna(df, coluna)
        if serie.empty:
            continue

        stats = calcular_estatisticas(serie)
        estatisticas[coluna] = stats

        # Avalia status se houver faixa ideal no JSON
        if coluna in faixa_ideais:
            status = avaliar_status(stats["média"], faixa_ideais[coluna])
            msg = interpretar_status(coluna, status)
            alertas.append({"coluna": coluna, "status": status, "mensagem": msg})

    return {
        "status": "OK",
        "titulo": "Resumo Geral do Desempenho",
        "estatisticas": estatisticas,
        "tempo_total": tempo_total,
        "distancia": distancia,
        "alertas": alertas
    }


def exibir(resultado: dict):
    """
    Exibe o resumo geral no Streamlit com métricas, estatísticas e alertas.
    """
    st.markdown(f"## 📈 {resultado['titulo']}")

    # Métricas principais
    col1, col2 = st.columns(2)
    tempo_str = str(resultado["tempo_total"]) if resultado["tempo_total"] else "N/A"
    dist_str = f"{resultado['distancia']:.2f} km" if resultado["distancia"] else "N/A"

    col1.metric("⏱️ Tempo Total da Viagem", tempo_str)
    col2.metric("🛣️ Distância Percorrida", dist_str)

    # Estatísticas detalhadas
    st.markdown("---")
    st.markdown("### Estatísticas Detalhadas")
    for coluna, stats in resultado["estatisticas"].items():
        st.markdown(f"**{coluna}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Mínimo", f"{stats['mínimo']}")
        c2.metric("Média", f"{stats['média']}")
        c3.metric("Máximo", f"{stats['máximo']}")
        st.markdown(
            f"Mediana: {stats['mediana']} | Desvio Padrão: {stats['desvio_padrao']}"
        )
        st.markdown(f"Q1: {stats['q1']} | Q3: {stats['q3']}")
        st.markdown("---")

    # Exibe alertas
    if resultado["alertas"]:
        st.markdown("### 🚨 Alertas de Desempenho")
        for alerta in resultado["alertas"]:
            if alerta["status"] == "OK":
                st.success(alerta["mensagem"])
            else:
                st.warning(alerta["mensagem"])
    else:
        st.success("✅ Nenhum alerta crítico identificado.")
