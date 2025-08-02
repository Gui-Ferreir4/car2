import streamlit as st
import pandas as pd
import numpy as np

VOLUME_TANQUE = 55.0  # litros

def analisar(df, modelo, combustivel, valores_ideais):
    if "FUELLVL(%)" not in df.columns:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Coluna 'FUELLVL(%)' não encontrada no arquivo.",
            "valores": {}
        }

    if "ENGI_IDLE" not in df.columns:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Coluna 'ENGI_IDLE' não encontrada no arquivo.",
            "valores": {}
        }

    df = df.copy()

    # Normaliza ENGI_IDLE para 0/1 com tratamento robusto
    df["ENGI_IDLE"] = df["ENGI_IDLE"].replace({
        "Sim": 1, "Não": 0, "Nao": 0, "nao": 0, "não": 0
    })
    df["ENGI_IDLE"] = pd.to_numeric(df["ENGI_IDLE"], errors='coerce').fillna(0).astype(int)

    # Filtra registros em marcha lenta (ENGI_IDLE == 1)
    df_idle = df[df["ENGI_IDLE"] == 1]
    if df_idle.empty:
        return {
            "status": "alerta",
            "titulo": "Nível de Combustível",
            "mensagem": "Não foram encontrados registros em marcha lenta (ENGI_IDLE == 1).",
            "valores": {}
        }

    # Converte coluna de combustível para numérico, substituindo "-" por NaN
    df_idle["FUELLVL(%)"] = pd.to_numeric(df_idle["FUELLVL(%)"].replace("-", np.nan), errors='coerce')

    # Remove registros inválidos em combustível
    df_idle = df_idle.dropna(subset=["FUELLVL(%)"])
    if df_idle.empty:
        return {
            "status": "alerta",
            "titulo": "Nível de Combustível",
            "mensagem": "Não foram encontrados registros válidos de nível de combustível em marcha lenta.",
            "valores": {}
        }

    # Calcula tempo total em ms da marcha lenta
    tempo_min = df_idle["time(ms)"].min()
    tempo_max = df_idle["time(ms)"].max()
    intervalo = tempo_max - tempo_min
    janela_tempo = intervalo * 0.05  # 5% do tempo total

    # Define janela inicial e final
    janela_inicial = df_idle[df_idle["time(ms)"] <= tempo_min + janela_tempo]
    janela_final = df_idle[df_idle["time(ms)"] >= tempo_max - janela_tempo]

    media_inicio = janela_inicial["FUELLVL(%)"].mean()
    media_fim = janela_final["FUELLVL(%)"].mean()

    consumo_pct = media_inicio - media_fim
    if consumo_pct < 0:
        consumo_pct = 0

    diferenca_litros = consumo_pct / 100.0 * VOLUME_TANQUE

    # Calcula distância total, se disponível
    distancia = None
    if "TRIP_ODOM(km)" in df.columns:
        odometro = pd.to_numeric(df["TRIP_ODOM(km)"].replace("-", np.nan), errors='coerce').dropna()
        if not odometro.empty:
            distancia = odometro.max() - odometro.min()

    # Calcula consumo km/l
    consumo_kml = None
    if distancia is not None and diferenca_litros > 0:
        consumo_kml = distancia / diferenca_litros

    # Monta mensagem para exibição
    mensagem = (
        f"Nível médio inicial: {media_inicio:.2f}%\n"
        f"Nível médio final: {media_fim:.2f}%\n"
        f"Combustível consumido: {diferenca_litros:.2f} litros\n"
    )
    if distancia is not None:
        mensagem += f"Distância percorrida: {distancia:.2f} km\n"
    if consumo_kml is not None:
        mensagem += f"Consumo médio: {consumo_kml:.2f} km/l"
    else:
        mensagem += "Consumo médio não calculado devido a dados insuficientes."

    status = "OK" if consumo_kml is not None else "alerta"

    return {
        "status": status,
        "titulo": "Nível de Combustível",
        "mensagem": mensagem,
        "valores": {
            "media_inicio_pct": media_inicio,
            "media_fim_pct": media_fim,
            "combustivel_consumido_l": diferenca_litros,
            "distancia_km": distancia,
            "consumo_kml": consumo_kml
        }
    }

def exibir(resultado):
    st.markdown(f"### ⛽ {resultado['titulo']}")

    if resultado["status"] == "erro":
        st.error(resultado["mensagem"])
        return

    if resultado["status"] == "alerta":
        st.warning(resultado["mensagem"])
    else:
        st.success(resultado["mensagem"])

    valores = resultado.get("valores", {})

    col1, col2 = st.columns(2)
    col1.metric("Nível médio inicial (%)", f"{valores.get('media_inicio_pct', 0):.2f}%")
    col2.metric("Nível médio final (%)", f"{valores.get('media_fim_pct', 0):.2f}%")

    if valores.get("distancia_km") is not None:
        st.metric("Distância percorrida (km)", f"{valores['distancia_km']:.2f}")
    else:
        st.metric("Distância percorrida (km)", "N/A")

    if valores.get("combustivel_consumido_l") is not None:
        st.metric("Combustível consumido (L)", f"{valores['combustivel_consumido_l']:.2f}")
    else:
        st.metric("Combustível consumido (L)", "N/A")

    if valores.get("consumo_kml") is not None:
        st.metric("Consumo médio (km/L)", f"{valores['consumo_kml']:.2f}")
    else:
        st.metric("Consumo médio (km/L)", "N/A")
