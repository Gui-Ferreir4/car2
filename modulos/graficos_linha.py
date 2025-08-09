# =========================
# Módulo: graficos_linha.py
# =========================
import streamlit as st
import pandas as pd
import plotly.express as px

# Lista de campos que terão gráfico
CAMPOS_GRAFICOS = [
    "IC_SPDMTR(km/h)",
    "RPM(1/min)",
    "FUELLVL(%)",
    "SHRTFT1(%)",
    "LONGFT1(%)",
    "AF_RATIO(:1)",
    "LMD_EGO1(:1)",
    "ECT_GAUGE(°C)",
    "ECT(°C)"
]

def exibir(df: pd.DataFrame):
    """Exibe gráficos de linha para os campos definidos."""
    st.subheader("📈 Gráficos de Linha dos Sensores")

    if "time(ms)" not in df.columns:
        st.error("A coluna 'time(ms)' não foi encontrada no arquivo. Não é possível gerar gráficos de linha.")
        return

    # Converter tempo para segundos
    tempo_segundos = pd.to_numeric(df["time(ms)"], errors="coerce") / 1000
    df_graficos = df.copy()
    df_graficos["Tempo (s)"] = tempo_segundos

    for campo in CAMPOS_GRAFICOS:
        if campo not in df.columns:
            st.warning(f"Coluna '{campo}' ausente no arquivo CSV.")
            continue

        # Converter para numérico, ignorando valores inválidos
        serie = pd.to_numeric(df[campo], errors="coerce")
        if serie.dropna().empty:
            st.warning(f"Sem dados numéricos válidos para '{campo}'.")
            continue

        # Criar gráfico
        fig = px.line(
            df_graficos,
            x="Tempo (s)",
            y=campo,
            title=f"{campo} ao longo do tempo",
            labels={"Tempo (s)": "Tempo (segundos)", campo: campo},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
