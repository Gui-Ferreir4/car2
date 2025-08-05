import pandas as pd
import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas

VOLUME_TANQUE = 55.0  # Litros

PARAMETROS_MONITORADOS = [
    "AF_RATIO(:1)", "SHRTFT1(%)", "LONGFT1(%)", "LAMBDA_1", "LMD_EGO1(:1)",
    "LOAD.OBDII(%)", "TP.OBDII(%)", "ECT_GAUGE(Â°C)", "IAT(Â°C)", "VBAT_1(V)"
]

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    resultado = {"status": "OK", "mensagem": "", "valores": {}}
    mensagens = []
    status_geral = "OK"
    faixa_ideais = valores_ideais.get(modelo, {}).get(combustivel, {})

    # --- Consumo estimado ---
    fuellvl = sanitizar_coluna(df, "FUELLVL(%)")
    trip_odom = sanitizar_coluna(df, "TRIP_ODOM(km)")
    odometer = sanitizar_coluna(df, "ODOMETER(km)")

    distancia_km = (trip_odom.max() - trip_odom.min()) if not trip_odom.empty else (
        odometer.max() - odometer.min() if not odometer.empty else None
    )

    consumo_litros = None
    consumo_pct = None
    if not fuellvl.empty:
        inicio, fim = fuellvl.head(10).mean(), fuellvl.tail(10).mean()
        consumo_pct = max(inicio - fim, 0)
        consumo_litros = round(consumo_pct / 100.0 * VOLUME_TANQUE, 2)

    kml = round(distancia_km / consumo_litros, 2) if distancia_km and consumo_litros and consumo_litros > 0 else None

    # --- Estatísticas e checagem de faixas ---
    stats_parametros = {}
    fora_faixa = []

    for param in PARAMETROS_MONITORADOS:
        serie = sanitizar_coluna(df, param)
        estat = calcular_estatisticas(serie)
        stats_parametros[param] = estat

        # Avaliar contra faixa do JSON
        faixa = faixa_ideais.get(param.replace("(%)", "").replace("(:1)", "").replace("(Â°C)", ""))
        if faixa and estat["média"] is not None:
            if estat["média"] < faixa[0] or estat["média"] > faixa[1]:
                fora_faixa.append(f"{param}: média {estat['média']:.2f} (ideal {faixa[0]}-{faixa[1]})")
                status_geral = "Alerta"

    # --- Status consumo ---
    if kml is not None:
        consumo_minimo = faixa_ideais.get("consumo_minimo_kml")
        if consumo_minimo and kml < consumo_minimo:
            fora_faixa.append(f"Consumo {kml:.2f} km/L < mínimo ideal {consumo_minimo} km/L")
            status_geral = "Alerta"

    mensagens.append("✅ Todos parâmetros dentro do esperado." if not fora_faixa else "⚠️ " + " | ".join(fora_faixa))

    resultado["status"] = status_geral
    resultado["mensagem"] = "\n".join(mensagens)
    resultado["valores"] = {
        "distancia_km": distancia_km,
        "consumo_litros": consumo_litros,
        "consumo_pct": consumo_pct,
        "kml": kml,
        "parametros": stats_parametros
    }
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

    st.markdown("### 🔹 Parâmetros Monitorados")
    for param, estat in valores.get("parametros", {}).items():
        if estat["média"] is not None:
            st.write(f"**{param}** → média: {estat['média']:.2f}, min: {estat['mínimo']}, max: {estat['máximo']}")

    status = resultado.get("status", "OK")
    if status == "Alerta":
        st.warning(resultado["mensagem"])
    elif status == "Erro":
        st.error(resultado["mensagem"])
    else:
        st.success(resultado["mensagem"])
