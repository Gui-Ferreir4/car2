import streamlit as st
import numpy as np
from modulos.utilitarios import sanitizar_coluna

def analisar(df, modelo, combustivel, valores_ideais):
    coluna_fuel = "FUELLVL(%)"
    coluna_velocidade = None

    # Detecta coluna de velocidade (tentando colunas comuns)
    for c in ["VSS(km/h)", "IC_SPDMTR(km/h)", "speed"]:
        if c in df.columns:
            coluna_velocidade = c
            break

    if coluna_velocidade is None:
        return {
            "status": "erro",
            "titulo": coluna_fuel,
            "mensagem": "Coluna de velocidade não encontrada para análise de nível de combustível.",
            "valores": {}
        }

    # Sanitiza as colunas importantes
    fuel = sanitizar_coluna(df, coluna_fuel)
    speed = sanitizar_coluna(df, coluna_velocidade)
    odometer_col = None
    for c in ["ODOMETER(km)", "odometer", "odometer_km"]:
        if c in df.columns:
            odometer_col = c
            break

    if odometer_col is None:
        return {
            "status": "erro",
            "titulo": coluna_fuel,
            "mensagem": "Coluna ODOMETER(km) não encontrada para cálculo de consumo.",
            "valores": {}
        }

    odometer = sanitizar_coluna(df, odometer_col)

    if fuel.empty or speed.empty or odometer.empty:
        return {
            "status": "erro",
            "titulo": coluna_fuel,
            "mensagem": "Dados insuficientes para análise.",
            "valores": {}
        }

    # Define janela inicial: registros do início com velocidade zero
    janela_inicial = df[(speed == 0)].head(10)
    fuel_inicio = sanitizar_coluna(janela_inicial, coluna_fuel)
    media_inicio = np.nan
    if not fuel_inicio.empty:
        media_inicio = fuel_inicio.mean()

    # Define janela final: registros do fim com velocidade zero
    janela_final = df[(speed == 0)].tail(10)
    fuel_fim = sanitizar_coluna(janela_final, coluna_fuel)
    media_fim = np.nan
    if not fuel_fim.empty:
        media_fim = fuel_fim.mean()

    # Calcula diferença em litros
    capacidade_tanque = 55.0  # litros
    if np.isnan(media_inicio) or np.isnan(media_fim):
        diferenca_litros = np.nan
    else:
        diferenca_percent = media_inicio - media_fim
        diferenca_litros = (diferenca_percent / 100) * capacidade_tanque
        if diferenca_litros < 0:
            # Pode ocorrer caso o tanque tenha sido abastecido durante a viagem
            diferenca_litros = np.nan

    # Calcula km rodados
    km_rodados = np.nan
    odometro_inicio = odometer.iloc[0]
    odometro_fim = odometer.iloc[-1]
    if not np.isnan(odometro_inicio) and not np.isnan(odometro_fim):
        km_rodados = odometro_fim - odometro_inicio
        if km_rodados < 0:
            km_rodados = np.nan  # erro possível

    # Calcula consumo km/l
    consumo = np.nan
    if diferenca_litros and diferenca_litros > 0 and km_rodados and km_rodados > 0:
        consumo = km_rodados / diferenca_litros

    # Define status e mensagens
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
