import streamlit as st
import pandas as pd
import numpy as np

from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

VOLUME_TANQUE = 55.0  # litros

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa consumo de combustível, mistura, e carga do motor.
    Retorna métricas detalhadas e status de eficiência.
    """
    resultado = {
        "status": "OK",
        "mensagem": "",
        "valores": {}
    }

    df = df.copy()

    # --- Consumo de combustível ---
    consumo_litros = None
    distancia_km = None
    consumo_kml = None
    msg_consumo = ""

    # Sanitiza colunas principais
    fuel = sanitizar_coluna(df, "FUELLVL(%)")
    idle = df.get("ENGI_IDLE")
    odom = None

    # Detecta colunas de odômetro
    for col in ["TRIP_ODOM(km)", "TRIP_ODOMETER(km)", "ODOMETER(km)"]:
        if col in df.columns:
            odom = sanitizar_coluna(df, col)
            break

    if not fuel.empty and idle is not None:
        # Normaliza marcha lenta (Sim/Não, etc.)
        idle_norm = (
            idle.astype(str)
            .str.lower()
            .replace({
                "sim": 1, "não": 0, "nao": 0, "n": 0, "s": 1
            })
        )
        idle_norm = pd.to_numeric(idle_norm, errors="coerce").fillna(0).astype(int)

        # Janela inicial e final (5% do tempo total)
        t = pd.to_numeric(df["time(ms)"], errors="coerce") if "time(ms)" in df.columns else pd.Series(range(len(df)))
        tempo_total = t.max() - t.min() if not t.empty else len(df)
        inicio = df[t <= t.min() + 0.05 * tempo_total]
        fim = df[t >= t.max() - 0.05 * tempo_total]

        # Calcula consumo em litros
        fuel_inicio = sanitizar_coluna(inicio, "FUELLVL(%)").mean()
        fuel_fim = sanitizar_coluna(fim, "FUELLVL(%)").mean()
        if pd.notna(fuel_inicio) and pd.notna(fuel_fim):
            consumo_pct = max(fuel_inicio - fuel_fim, 0)
            consumo_litros = round(consumo_pct / 100 * VOLUME_TANQUE, 2)

        # Distância percorrida
        if odom is not None and not odom.empty:
            distancia_km = round(odom.max() - odom.min(), 2)

        # Consumo médio km/l
        if consumo_litros and distancia_km:
            consumo_kml = round(distancia_km / consumo_litros, 2)

        msg_consumo = (
            f"Combustível inicial: {fuel_inicio:.2f}% ({fuel_inicio/100*VOLUME_TANQUE:.1f} L) | "
            f"final: {fuel_fim:.2f}% ({fuel_fim/100*VOLUME_TANQUE:.1f} L) | "
            f"consumo: {consumo_litros if consumo_litros else 'N/A'} L"
        )

    resultado["valores"]["consumo_litros"] = consumo_litros
    resultado["valores"]["distancia_km"] = distancia_km
    resultado["valores"]["consumo_kml"] = consumo_kml

    # --- Mistura e correções ---
    mistura_stats = {}
    for col in ["AF_RATIO(:1)", "SHRTFT1(%)", "LONGFT1(%)"]:
        serie = sanitizar_coluna(df, col)
        if not serie.empty:
            mistura_stats[col] = calcular_estatisticas(serie)
    resultado["valores"]["mistura"] = mistura_stats

    # --- Carga e TPS ---
    carga_stats = {}
    for col in ["LOAD.OBDII(%)", "TP.OBDII(%)"]:
        serie = sanitizar_coluna(df, col)
        if not serie.empty:
            carga_stats[col] = calcular_estatisticas(serie)
    resultado["valores"]["carga_tps"] = carga_stats

    # --- Avaliação com JSON de valores ideais ---
    faixa_ideais = valores_ideais.get(modelo, {}).get(combustivel.lower(), {})
    alertas = []

    if consumo_kml and "consumo_kml_min" in faixa_ideais:
        if consumo_kml < faixa_ideais["consumo_kml_min"]:
            resultado["status"] = "alerta"
            alertas.append(f"Consumo abaixo do esperado ({consumo_kml} km/L)")

    for col, stats in mistura_stats.items():
        if col in faixa_ideais:
            status = avaliar_status(stats["média"], faixa_ideais[col])
            if status != "OK":
                resultado["status"] = "alerta"
                alertas.append(f"{col} fora da faixa ideal (média {stats['média']})")

    resultado["mensagem"] = msg_consumo + (" | " + " / ".join(alertas) if alertas else "")

    return resultado


def exibir(resultado: dict):
    """
    Exibe os resultados de consumo e eficiência de combustível no Streamlit.
    """
    st.markdown("## ⛽ Análise de Consumo e Eficiência do Motor")

    # Bloco principal de métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Distância (km)", f"{resultado['valores']['distancia_km'] or 'N/A'}")
    col2.metric("Consumo (L)", f"{resultado['valores']['consumo_litros'] or 'N/A'}")
    col3.metric("Média (km/L)", f"{resultado['valores']['consumo_kml'] or 'N/A'}")

    # Mistura
    st.markdown("### 🔹 Mistura e Correções de Injeção")
    for col, stats in resultado["valores"]["mistura"].items():
        st.write(f"**{col}** → média {stats['média']}, min {stats['mínimo']}, máx {stats['máximo']}")

    # Carga e TPS
    st.markdown("### 🔹 Carga e Posição da Borboleta")
    for col, stats in resultado["valores"]["carga_tps"].items():
        st.write(f"**{col}** → média {stats['média']}, min {stats['mínimo']}, máx {stats['máximo']}")

    # Mensagem final
    if resultado["status"] == "alerta":
        st.warning(f"⚠️ {resultado['mensagem']}")
    elif resultado["status"] == "erro":
        st.error(f"❌ {resultado['mensagem']}")
    else:
        st.success(f"✅ {resultado['mensagem']}")
