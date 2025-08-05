# modulos/fuellvl.py

import pandas as pd
import numpy as np
import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

VOLUME_TANQUE = 55.0  # Litros

# Aliases para nomes de colunas que podem variar
COLUNAS_EQUIVALENTES = {
    "FUELLVL(%)": ["FUELLVL(%)", "FUEL_LVL(%)", "FUELLEVEL(%)"],
    "TRIP_ODOM(km)": ["TRIP_ODOM(km)", "TRIP(km)"],
    "ODOMETER(km)": ["ODOMETER(km)", "ODO(km)"],
    "IC_SPDMTR(km/h)": ["IC_SPDMTR(km/h)", "SPEED(km/h)"],
    "ENGI_IDLE": ["ENGI_IDLE", "IDLE"],
    "AF_RATIO(:1)": ["AF_RATIO(:1)", "AFR(:1)"],
    "SHRTFT1(%)": ["SHRTFT1(%)", "STFT1(%)"],
    "LONGFT1(%)": ["LONGFT1(%)", "LTFT1(%)"],
    "LAMBDA_1": ["LAMBDA_1", "LAMBDA"],
    "LMD_EGO1(:1)": ["LMD_EGO1(:1)", "EGO(:1)"],
    "LOAD.OBDII(%)": ["LOAD.OBDII(%)", "LOAD(%)"],
    "TP.OBDII(%)": ["TP.OBDII(%)", "TPS(%)"],
    "ECT_GAUGE(Â°C)": ["ECT_GAUGE(Â°C)", "ECT(°C)"],
    "IAT(Â°C)": ["IAT(Â°C)", "IAT(°C)"],
    "VBAT_1(V)": ["VBAT_1(V)", "VBAT(V)"]
}

def get_col(df, colname):
    """Retorna a primeira coluna existente do DataFrame que corresponde aos aliases."""
    for alias in COLUNAS_EQUIVALENTES.get(colname, [colname]):
        if alias in df.columns:
            return alias
    return None

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    resultado = {
        "status": "OK",
        "mensagem": "",
        "valores": {}
    }

    # --- Identificar colunas principais ---
    fuellvl_col = get_col(df, "FUELLVL(%)")
    trip_col = get_col(df, "TRIP_ODOM(km)")
    odo_col = get_col(df, "ODOMETER(km)")
    speed_col = get_col(df, "IC_SPDMTR(km/h)")
    idle_col = get_col(df, "ENGI_IDLE")

    # --- Sanitização ---
    fuellvl = sanitizar_coluna(df, fuellvl_col) if fuellvl_col else pd.Series(dtype=float)
    trip_odom = sanitizar_coluna(df, trip_col) if trip_col else pd.Series(dtype=float)
    odometer = sanitizar_coluna(df, odo_col) if odo_col else pd.Series(dtype=float)

    engi_idle = df.get(idle_col, pd.Series(dtype=str)).astype(str).str.lower().replace({
        "sim": 1, "não": 0, "nao": 0, "nÃ£o": 0,
        "yes": 1, "no": 0, "-": 0, "": 0
    })
    engi_idle = pd.to_numeric(engi_idle, errors="coerce").fillna(0).astype(int)

    # --- Mistura ---
    af_ratio = sanitizar_coluna(df, get_col(df, "AF_RATIO(:1)"))
    shrtft1 = sanitizar_coluna(df, get_col(df, "SHRTFT1(%)"))
    longft1 = sanitizar_coluna(df, get_col(df, "LONGFT1(%)"))
    lambda1 = sanitizar_coluna(df, get_col(df, "LAMBDA_1"))
    ego = sanitizar_coluna(df, get_col(df, "LMD_EGO1(:1)"))

    # --- Contexto do motor ---
    load = sanitizar_coluna(df, get_col(df, "LOAD.OBDII(%)"))
    tps = sanitizar_coluna(df, get_col(df, "TP.OBDII(%)"))
    ect = sanitizar_coluna(df, get_col(df, "ECT_GAUGE(Â°C)"))
    iat = sanitizar_coluna(df, get_col(df, "IAT(Â°C)"))
    vbat = sanitizar_coluna(df, get_col(df, "VBAT_1(V)"))

    # --- Cálculo de viagem ---
    tempo_total_seg = None
    if "time(ms)" in df.columns:
        tempo_total_seg = (df["time(ms)"].max() - df["time(ms)"].min()) / 1000.0

    if not trip_odom.empty:
        distancia_km = trip_odom.max() - trip_odom.min()
    elif not odometer.empty:
        distancia_km = odometer.max() - odometer.min()
    else:
        distancia_km = None

    consumo_litros = None
    consumo_pct = None
    if not fuellvl.empty:
        inicio = fuellvl.head(10).mean()
        fim = fuellvl.tail(10).mean()
        consumo_pct = max(inicio - fim, 0)
        consumo_litros = round(consumo_pct / 100.0 * VOLUME_TANQUE, 2)

    kml = None
    if distancia_km and consumo_litros and consumo_litros > 0:
        kml = round(distancia_km / consumo_litros, 2)

    # --- Estatísticas ---
    def stats_or_none(serie):
        stats = calcular_estatisticas(serie)
        return {k: (float(v) if v is not None else None) for k, v in stats.items()}

    resultado["valores"] = {
        "consumo_litros": consumo_litros,
        "consumo_pct": consumo_pct,
        "distancia_km": distancia_km,
        "kml": kml,
        "tempo_total_seg": tempo_total_seg,
        "mistura": {
            "AF_RATIO": stats_or_none(af_ratio),
            "SHRTFT1": stats_or_none(shrtft1),
            "LONGFT1": stats_or_none(longft1),
            "Lambda": stats_or_none(lambda1),
            "EGO": stats_or_none(ego)
        },
        "motor": {
            "LOAD": stats_or_none(load),
            "TPS": stats_or_none(tps),
            "ECT": stats_or_none(ect),
            "IAT": stats_or_none(iat),
            "VBAT": stats_or_none(vbat)
        }
    }

    # --- Avaliação ---
    status_msgs = []
    faixas = valores_ideais.get(modelo, {}).get(combustivel, {})

    if kml is not None and "consumo_minimo_kml" in faixas:
        if kml < faixas["consumo_minimo_kml"]:
            status_msgs.append(f"⚠️ Consumo médio {kml} km/L abaixo do ideal ({faixas['consumo_minimo_kml']} km/L)")
            resultado["status"] = "alerta"

    for campo, stats in resultado["valores"]["mistura"].items():
        if stats["média"] is None:
            continue
        faixa = faixas.get(campo)
        if faixa and not (faixa[0] <= stats["média"] <= faixa[1]):
            status_msgs.append(f"{campo} médio {stats['média']} fora da faixa {faixa}")
            resultado["status"] = "alerta"

    if not status_msgs:
        status_msgs.append("Parâmetros de consumo e mistura dentro do esperado.")

    resultado["mensagem"] = "\n".join(status_msgs)
    return resultado


def exibir(resultado: dict):
    st.subheader("⛽ Análise de Consumo e Eficiência")

    valores = resultado.get("valores", {})
    consumo_litros = valores.get("consumo_litros")
    distancia_km = valores.get("distancia_km")
    kml = valores.get("kml")

    col1, col2, col3 = st.columns(3)
    col1.metric("Distância (km)", f"{distancia_km:.2f}" if distancia_km else "N/A")
    col2.metric("Consumo (L)", f"{consumo_litros:.2f}" if consumo_litros else "N/A")
    col3.metric("Consumo Médio (km/L)", f"{kml:.2f}" if kml else "N/A")

    st.markdown("### 🔹 Mistura e Correções de Combustível")
    for key, stats in valores.get("mistura", {}).items():
        if stats["média"] is not None:
            st.write(f"**{key}** — Média: {stats['média']:.2f}, Mín: {stats['mínimo']}, Máx: {stats['máximo']}")

    st.markdown("### 🔹 Parâmetros do Motor")
    for key, stats in valores.get("motor", {}).items():
        if stats["média"] is not None:
            st.write(f"**{key}** — Média: {stats['média']:.2f}, Mín: {stats['mínimo']}, Máx: {stats['máximo']}")

    if resultado["status"] == "alerta":
        st.warning(resultado["mensagem"])
    elif resultado["status"] == "erro":
        st.error(resultado["mensagem"])
    else:
        st.success(resultado["mensagem"])
