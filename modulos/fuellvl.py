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

    media_inicio_pct = janela_inicial["FUELLVL(%)"].mean()
    media_fim_pct = janela_final["FUELLVL(%)"].mean()

    consumo_pct = media_inicio_pct - media_fim_pct
    if consumo_pct < 0:
        consumo_pct = 0

    volume_inicio_l = media_inicio_pct / 100.0 * VOLUME_TANQUE
    volume_fim_l = media_fim_pct / 100.0 * VOLUME_TANQUE
    consumo_litros = consumo_pct / 100.0 * VOLUME_TANQUE

    # Calcula distância total, se disponível
    distancia = None
    if "TRIP_ODOM(km)" in df.columns:
        odometro = pd.to_numeric(df["TRIP_ODOM(km)"].replace("-", np.nan), errors='coerce').dropna()
        if not odometro.empty:
            distancia = odometro.max() - odometro.min()

    # Calcula consumo km/l
    consumo_kml = None
    if distancia is not None and consumo_litros > 0:
        consumo_kml = distancia / consumo_litros

    # Verifica consumo ideal no JSON
    consumo_ideal_min = None
    if modelo in valores_ideais:
        combustivel_info = valores_ideais[modelo].get(combustivel, {})
        consumo_ideal_min = combustivel_info.get("consumo_minimo_kml")

    alerta_consumo = False
    if consumo_kml is not None and consumo_ideal_min is not None:
        if consumo_kml < consumo_ideal_min:
            alerta_consumo = True

    # Monta mensagem para exibição
    mensagem = (
        f"Nível médio inicial: {media_inicio_pct:.2f}% ({volume_inicio_l:.2f} litros)\n"
        f"Nível médio final: {media_fim_pct:.2f}% ({volume_fim_l:.2f} litros)\n"
        f"Combustível consumido: {consumo_litros:.2f} litros\n"
    )
    if distancia is not None:
        mensagem += f"Distância percorrida: {distancia:.2f} km\n"
    if consumo_kml is not None:
        mensagem += f"Consumo médio: {consumo_kml:.2f} km/l\n"
        if alerta_consumo:
            mensagem += f"⚠️ Consumo abaixo do esperado para este veículo (mínimo esperado: {consumo_ideal_min:.2f} km/l)\n"
    else:
        mensagem += "Consumo médio não calculado devido a dados insuficientes."

    status = "alerta" if alerta_consumo else ("OK" if consumo_kml is not None else "alerta")

    valores = {
        "media_inicio_pct": media_inicio_pct,
        "media_fim_pct": media_fim_pct,
        "volume_inicio_l": volume_inicio_l,
        "volume_fim_l": volume_fim_l,
        "consumo_litros": consumo_litros,
        "distancia_km": distancia,
        "consumo_kml": consumo_kml,
        "consumo_ideal_min_kml": consumo_ideal_min,
        "alerta_consumo": alerta_consumo
    }

    return {
        "status": status,
        "titulo": "Nível de Combustível",
        "mensagem": mensagem,
        "valores": valores
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

    col1.metric("Volume inicial (litros)", f"{valores.get('volume_inicio_l', 0):.2f} L")
    col2.metric("Volume final (litros)", f"{valores.get('volume_fim_l', 0):.2f} L")

    if valores.get("distancia_km") is not None:
        st.metric("Distância percorrida (km)", f"{valores['distancia_km']:.2f}")
    else:
        st.metric("Distância percorrida (km)", "N/A")

    if valores.get("consumo_litros") is not None:
        st.metric("Combustível consumido (L)", f"{valores['consumo_litros']:.2f}")
    else:
        st.metric("Combustível consumido (L)", "N/A")

    if valores.get("consumo_kml") is not None:
        st.metric("Consumo médio (km/L)", f"{valores['consumo_kml']:.2f}")
    else:
        st.metric("Consumo médio (km/L)", "N/A")
