import pandas as pd
import streamlit as st
import plotly.express as px

# Lista de campos e rótulos
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

def preparar_tempo(df: pd.DataFrame):
    """Converte time(ms) para tempo em minutos ou formato HH:MM:SS"""
    if "time(ms)" not in df.columns:
        return pd.Series(range(len(df)), name="Tempo")
    
    tempo_seg = pd.to_numeric(df["time(ms)"], errors="coerce") / 1000
    tempo_fmt = tempo_seg.apply(lambda x: f"{int(x//3600):02}:{int((x%3600)//60):02}:{int(x%60):02}" if pd.notna(x) else None)
    return tempo_fmt

def exibir_graficos(df: pd.DataFrame):
    st.subheader("📊 Gráficos de Linha - Diagnóstico OBD")

    tempo = preparar_tempo(df)

    for campo in CAMPOS_GRAFICOS:
        if campo not in df.columns:
            st.warning(f"Coluna '{campo}' ausente nos dados.")
            continue

        serie = pd.to_numeric(df[campo], errors="coerce")
        if serie.dropna().empty:
            st.info(f"Sem dados numéricos válidos para '{campo}'.")
            continue

        dados_plot = pd.DataFrame({
            "Tempo": tempo,
            campo: serie
        })

        fig = px.line(
            dados_plot,
            x="Tempo",
            y=campo,
            title=f"Evolução de {campo} ao longo do tempo",
            labels={"Tempo": "Tempo (HH:MM:SS)", campo: campo}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
