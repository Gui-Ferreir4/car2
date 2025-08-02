import streamlit as st
import pandas as pd
import numpy as np

VOLUME_TANQUE = 55.0  # litros

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

    coluna_tempo = encontrar_coluna(df, ["time(ms)", "TIME(ms)", "time"])
    if coluna_tempo is None:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Coluna de tempo não encontrada para análise.",
            "valores": {}
        }

    coluna_odometro = encontrar_coluna(df, ["ODOMETER(km)", "odometer", "odometer_km", "TRIP_ODOM(km)"])
    if coluna_odometro is None:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Coluna de odômetro não encontrada para cálculo de consumo.",
            "valores": {}
        }

    # Sanitiza as colunas
    fuel = sanitizar_coluna(df, coluna_fuel)
    speed = sanitizar_coluna(df, coluna_velocidade)
    tempo = sanitizar_coluna(df, coluna_tempo)
    odometro = sanitizar_coluna(df, coluna_odometro)

    if fuel.empty or speed.empty or tempo.empty or odometro.empty:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Dados insuficientes para análise.",
            "valores": {}
        }

    # Filtra dados com velocidade zero (veículo parado)
    df_parado = df[(df[coluna_velocidade] == 0) & (df[coluna_fuel].notna()) & (df[coluna_tempo].notna())]

    if df_parado.empty:
        return {
            "status": "erro",
            "titulo": "Nível de Combustível",
            "mensagem": "Não há registros com velocidade zero e nível de combustível válido para análise.",
            "valores": {}
        }

    tempo_min = df_parado[coluna_tempo].min()
    tempo_max = df_parado[coluna_tempo].max()
    intervalo = tempo_max - tempo_min
    janela_tempo = intervalo * 0.05  # 5% do intervalo total

    # Janela inicial: registros no primeiro 5% do tempo
    janela_inicial = df_parado[df_parado[coluna_tempo] <= (tempo_min + janela_tempo)]
    # Janela final: registros no último 5% do tempo
    janela_final = df_parado[df_parado[coluna_tempo] >= (tempo_max - janela_tempo)]

    # Calcula médias do nível combustível nessas janelas
    media_inicio = sanitizar_coluna(janela_inicial, coluna_fuel).mean()
    media_fim = sanitizar_coluna(janela_final, coluna_fuel).mean()

    # Calcula diferença em litros
    if pd.isna(media_inicio) or pd.isna(media_fim):
        diferenca_litros = np.nan
    else:
        diferenca_pct = media_inicio - media_fim
        diferenca_litros = (diferenca_pct / 100) * VOLUME_TANQUE
        if diferenca_litros < 0:
            # Possível reabastecimento ou erro
            diferenca_litros = np.nan

    # Calcula distância rodada
    odometro_inicio = odometro.iloc[0]
    odometro_fim = odometro.iloc[-1]
    km_rodados = odometro_fim - odometro_inicio if pd.notna(odometro_inicio) and pd.notna(odometro_fim) else np.nan
    if km_rodados < 0:
        km_rodados = np.nan

    # Calcula consumo médio km/l
    consumo = km_rodados / diferenca_litros if (diferenca_litros and diferenca_litros > 0 and km_rodados and km_rodados > 0) else np.nan

    # Monta mensagens e status
    if pd.isna(media_inicio) or pd.isna(media_fim):
        status = "alerta"
        mensagem = "Dados insuficientes para análise do nível de combustível no início e fim da viagem."
    elif pd.isna(consumo):
        status = "alerta"
        mensagem = "Não foi possível calcular o consumo devido a dados inconsistentes."
    else:
        status = "OK"
        mensagem = (
            f"Nível inicial: {media_inicio:.1f}% | Nível final: {media_fim:.1f}%\n"
            f"Combustível consumido: {diferenca_litros:.2f} litros\n"
            f"Distância percorrida: {km_rodados:.2f} km\n"
            f"Consumo médio: {consumo:.2f} km/l"
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

def exibir(resultado):
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
    if valores.get("diferenca_litros") is not None and not pd.isna(valores["diferenca_litros"]):
        col3.metric("Combustível consumido (L)", f"{valores['diferenca_litros']:.2f}")
    else:
        col3.metric("Combustível consumido (L)", "N/A")

    if valores.get("km_rodados") is not None and not pd.isna(valores["km_rodados"]):
        col4.metric("Distância percorrida (km)", f"{valores['km_rodados']:.2f}")
    else:
        col4.metric("Distância percorrida (km)", "N/A")

    if valores.get("consumo_kml") is not None and not pd.isna(valores["consumo_kml"]):
        st.metric("Consumo médio (km/L)", f"{valores['consumo_kml']:.2f}")
    else:
        st.metric("Consumo médio (km/L)", "N/A")
