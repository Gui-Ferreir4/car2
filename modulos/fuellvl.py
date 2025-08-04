# modulos/fuellvl.py

import pandas as pd
import numpy as np
import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

VOLUME_TANQUE = 55.0  # Litros

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa consumo e eficiência de combustível, mistura e comportamento do motor.
    Retorna dicionário rico em informações para exibição.
    """
    resultado = {
        "status": "OK",
        "mensagem": "",
        "valores": {}
    }

    # --- Sanitizar colunas importantes ---
    fuellvl = sanitizar_coluna(df, "FUELLVL(%)")
    trip_odom = sanitizar_coluna(df, "TRIP_ODOM(km)")
    odometer = sanitizar_coluna(df, "ODOMETER(km)")
    speed = sanitizar_coluna(df, "IC_SPDMTR(km/h)")
    engi_idle = (
        df.get("ENGI_IDLE", pd.Series(dtype=str))
        .astype(str)
        .str.strip()
        .str.lower()
        .replace({
            "sim": 1, "não": 0, "nao": 0, "nÃ£o": 0,
            "yes": 1, "no": 0, "-": 0, "": 0
        })
    )

engi_idle = pd.to_numeric(engi_idle, errors="coerce").fillna(0).astype(int)

    # Mistura
    af_ratio = sanitizar_coluna(df, "AF_RATIO(:1)")
    shrtft1 = sanitizar_coluna(df, "SHRTFT1(%)")
    longft1 = sanitizar_coluna(df, "LONGFT1(%)")
    lambda1 = sanitizar_coluna(df, "LAMBDA_1")
    ego = sanitizar_coluna(df, "LMD_EGO1(:1)")

    # Contexto do motor
    load = sanitizar_coluna(df, "LOAD.OBDII(%)")
    tps = sanitizar_coluna(df, "TP.OBDII(%)")
    ect = sanitizar_coluna(df, "ECT_GAUGE(Â°C)")
    iat = sanitizar_coluna(df, "IAT(Â°C)")
    vbat = sanitizar_coluna(df, "VBAT_1(V)")

    # --- Tempo total de viagem ---
    if "time(ms)" in df.columns:
        tempo_total_seg = (df["time(ms)"].max() - df["time(ms)"].min()) / 1000.0
    else:
        tempo_total_seg = None

    # --- Distância percorrida ---
    if not trip_odom.empty:
        distancia_km = trip_odom.max() - trip_odom.min()
    elif not odometer.empty:
        distancia_km = odometer.max() - odometer.min()
    else:
        distancia_km = None

    # --- Consumo de combustível estimado ---
    consumo_litros = None
    consumo_pct = None
    if not fuellvl.empty:
        inicio = fuellvl.head(10).mean()
        fim = fuellvl.tail(10).mean()
        consumo_pct = max(inicio - fim, 0)
        consumo_litros = round(consumo_pct / 100.0 * VOLUME_TANQUE, 2)

    # --- Eficiência km/L ---
    kml = None
    if distancia_km and consumo_litros and consumo_litros > 0:
        kml = round(distancia_km / consumo_litros, 2)

    # --- Mistura e correções ---
    af_stats = calcular_estatisticas(af_ratio)
    sft_stats = calcular_estatisticas(shrtft1)
    lft_stats = calcular_estatisticas(longft1)

    # --- Contexto adicional ---
    load_stats = calcular_estatisticas(load)
    tps_stats = calcular_estatisticas(tps)
    ect_stats = calcular_estatisticas(ect)
    iat_stats = calcular_estatisticas(iat)
    vbat_stats = calcular_estatisticas(vbat)

    # --- Avaliação de status geral ---
    status_msgs = []
    if kml is not None:
        faixa = valores_ideais.get(modelo, {}).get(combustivel, {}).get("km_l", {})
        if faixa:
            status = avaliar_status(kml, faixa)
            if status == "Alerta":
                status_msgs.append(f"Consumo {kml} km/L fora da faixa ideal ({faixa['min']} - {faixa['max']}).")
                resultado["status"] = "alerta"

    if not status_msgs:
        status_msgs.append("Parâmetros de consumo e mistura dentro do esperado.")

    # --- Monta resultado ---
    resultado["mensagem"] = "\n".join(status_msgs)
    resultado["valores"] = {
        "consumo_litros": consumo_litros,
        "consumo_pct": consumo_pct,
        "distancia_km": distancia_km,
        "kml": kml,
        "tempo_total_seg": tempo_total_seg,
        "mistura": {
            "AF_RATIO": af_stats,
            "SHRTFT1": sft_stats,
            "LONGFT1": lft_stats,
            "Lambda": calcular_estatisticas(lambda1),
            "EGO": calcular_estatisticas(ego)
        },
        "motor": {
            "LOAD": load_stats,
            "TPS": tps_stats,
            "ECT": ect_stats,
            "IAT": iat_stats,
            "VBAT": vbat_stats
        }
    }

    return resultado


def exibir(resultado: dict):
    """
    Exibe os resultados no Streamlit de forma organizada.
    """
    st.subheader("⛽ Análise de Consumo e Eficiência")

    valores = resultado.get("valores", {})
    consumo_litros = valores.get("consumo_litros")
    distancia_km = valores.get("distancia_km")
    kml = valores.get("kml")

    # --- Bloco de métricas principais ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Distância (km)", f"{distancia_km:.2f}" if distancia_km else "N/A")
    col2.metric("Consumo (L)", f"{consumo_litros:.2f}" if consumo_litros else "N/A")
    col3.metric("Consumo Médio (km/L)", f"{kml:.2f}" if kml else "N/A")

    # --- Bloco de mistura ---
    st.markdown("### 🔹 Mistura e Correções de Combustível")
    mistura = valores.get("mistura", {})
    for key, stats in mistura.items():
        st.write(f"**{key}**: {stats}")

    # --- Bloco de contexto do motor ---
    st.markdown("### 🔹 Parâmetros do Motor")
    motor = valores.get("motor", {})
    for key, stats in motor.items():
        st.write(f"**{key}**: {stats}")

    # --- Status e mensagem ---
    if resultado["status"] == "alerta":
        st.warning("⚠️ " + resultado["mensagem"])
    elif resultado["status"] == "erro":
        st.error("❌ " + resultado["mensagem"])
    else:
        st.success("✅ " + resultado["mensagem"])
