import streamlit as st
import numpy as np
import pandas as pd

def encontrar_coluna(df, nomes_possiveis):
    for nome in nomes_possiveis:
        if nome in df.columns:
            return nome
    return None

def sanitizar_coluna(df, coluna):
    if coluna not in df.columns:
        return pd.Series(dtype=float)
    serie = df[coluna].replace(["-", "NA", "NaN", "nan", None], pd.NA)
    serie = pd.to_numeric(serie, errors="coerce")
    return serie.dropna()

def analisar(df, modelo, combustivel, valores_ideais):
    coluna_fuel = encontrar_coluna(df, ["FUELLVL(%)", "FUEL LVL(%)", "FuelLevel", "Fuel Level (%)"])
    if coluna_fuel is None:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Coluna de nível de combustível não encontrada.",
            "valores": {}
        }

    coluna_velocidade = encontrar_coluna(df, ["VSS(km/h)", "IC_SPDMTR(km/h)", "speed"])
    if coluna_velocidade is None:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Coluna de velocidade não encontrada para análise.",
            "valores": {}
        }

    coluna_odometer = encontrar_coluna(df, ["ODOMETER(km)", "odometer", "odometer_km"])
    if coluna_odometer is None:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Coluna ODOMETER(km) não encontrada para cálculo de consumo.",
            "valores": {}
        }

    fuel = sanitizar_coluna(df, coluna_fuel)
    speed = sanitizar_coluna(df, coluna_velocidade)
    odometer = sanitizar_coluna(df, coluna_odometer)

    if fuel.empty or speed.empty or odometer.empty:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Dados insuficientes para análise.",
            "valores": {}
        }

    # Filtra registros com velocidade zero e combustível válido para início e fim
    df_valido = df[(df[coluna_velocidade] == 0) & (df[coluna_fuel].notna())]

    janela_inicial = df_valido.head(10)
    janela_final = df_valido.tail(10)

    fuel_inicio = sanitizar_coluna(janela_inicial, coluna_fuel)
    media_inicio = fuel_inicio.mean() if not fuel_inicio.empty else float('nan')

    fuel_fim = sanitizar_coluna(janela_final, coluna_fuel)
    media_fim = fuel_fim.mean() if not fuel_fim.empty else float('nan')

    capacidade_tanque = 55.0  # litros

    if np.isnan(media_inicio) or np.isnan(media_fim):
        diferenca_litros = np.nan
    else:
        diferenca_percent = media_inicio - media_fim
        diferenca_litros = (diferenca_percent / 100) * capacidade_tanque
        if diferenca_litros < 0:
            # Possível reabastecimento ou dados inconsistentes
            diferenca_litros = np.nan

    odometro_inicio = odometer.iloc[0]
    odometro_fim = odometer.iloc[-1]
    km_rodados = odometro_fim - odometro_inicio if pd.notna(odometro_inicio) and pd.notna(odometro_fim) else np.nan
    if km_rodados < 0:
        km_rodados = np.nan  # dados inconsistentes

    consumo = km_rodados / diferenca_litros if (diferenca_litros and diferenca_litros > 0 and km_rodados and km_rodados > 0) else np.nan

    if np.isnan(media_inicio) or np.isnan(media_fim):
        status = "alerta"
        mensagem = "Dados insuficientes para análise do nível de combustível no início e no fim da viagem."
    elif np.isnan(consumo):
        status = "alerta"
        mensagem = "Não foi possível calcular o consumo devido a dados inconsistentes."
    else:
        status = "OK"
        mensagem = (
            f"Nível de combustível no início: {media_inicio:.1f}% | "
            f"no fim: {media_fim:.1f}%\n"
            f"Combustível consumido: {diferenca_litros:.2f} litros\n"
            f"Distância percorrida: {km_rodados:.2f} km\n"
            f"Consumo médio calculado: {consumo:.2f} km/l"
        )

    return {
        "status": status,
        "titulo": coluna_fuel,
        "mensagem": mensagem,
        "valores": {
            "media_inicio_pct": media_inicio,
            "media_fim_pct": media_fim,
            "diferenca_litros": diferenca_litros,
            "km_rodados": km_rodados,
            "consumo_kml": consumo
        }
    }


def exibir(resultado: dict):
    st.markdown(f"### ⛽ {resultado['titulo']}")

    if resultado["status"] == "erro":
        st.error(resultado["mensagem"])
        return

    if resultado["status"] == "alerta":
        st.warning(f"⚠️ {resultado['mensagem']}")
    else:
        st.success(resultado["mensagem"])

    valores = resultado.get("valores", {})

    col1, col2 = st.columns(2)
    col1.metric("Nível médio inicial (%)", f"{valores.get('media_inicio_pct', 0):.1f}%")
    col2.metric("Nível médio final (%)", f"{valores.get('media_fim_pct', 0):.1f}%")

    col3, col4 = st.columns(2)
    if valores.get("diferenca_litros") is not None and not (valores["diferenca_litros"] != valores["diferenca_litros"]):  # isnan check
        col3.metric("Combustível consumido (L)", f"{valores['diferenca_litros']:.2f}")
    else:
        col3.metric("Combustível consumido (L)", "N/A")

    if valores.get("km_rodados") is not None and not (valores["km_rodados"] != valores["km_rodados"]):
        col4.metric("Distância percorrida (km)", f"{valores['km_rodados']:.2f}")
    else:
        col4.metric("Distância percorrida (km)", "N/A")

    if valores.get("consumo_kml") is not None and not (valores["consumo_kml"] != valores["consumo_kml"]):
        st.metric("Consumo médio (km/L)", f"{valores['consumo_kml']:.2f}")
    else:
        st.metric("Consumo médio (km/L)", "N/A")
