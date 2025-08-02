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
    coluna_velocidade = encontrar_coluna(df, ["VSS(km/h)", "IC_SPDMTR(km/h)", "speed"])
    coluna_tempo = encontrar_coluna(df, ["time(ms)", "TIME(ms)", "time"])
    coluna_odometro = encontrar_coluna(df, ["ODOMETER(km)", "odometer", "odometer_km", "TRIP_ODOM(km)"])

    # Sanitiza colunas
    fuel = sanitizar_coluna(df, coluna_fuel) if coluna_fuel else pd.Series(dtype=float)
    speed = sanitizar_coluna(df, coluna_velocidade) if coluna_velocidade else pd.Series(dtype=float)
    tempo = sanitizar_coluna(df, coluna_tempo) if coluna_tempo else pd.Series(dtype=float)
    odometro = sanitizar_coluna(df, coluna_odometro) if coluna_odometro else pd.Series(dtype=float)

    # Fallback para janelas:
    # 1) tenta filtrar registros com velocidade zero e dados válidos
    if coluna_velocidade and coluna_fuel and coluna_tempo:
        df_parado = df[(df[coluna_velocidade] == 0) & (df[coluna_fuel].notna()) & (df[coluna_tempo].notna())]
    else:
        df_parado = pd.DataFrame()

    # Se não encontrar janelas com velocidade zero, pega janelas com os primeiros 5% e últimos 5% do tempo no df original
    if df_parado.empty and coluna_fuel and coluna_tempo:
        tempo_min = tempo.min()
        tempo_max = tempo.max()
        intervalo = tempo_max - tempo_min
        janela_tempo = intervalo * 0.05  # 5%

        janela_inicial = df[(df[coluna_tempo] >= tempo_min) & (df[coluna_tempo] <= (tempo_min + janela_tempo))]
        janela_final = df[(df[coluna_tempo] >= (tempo_max - janela_tempo)) & (df[coluna_tempo] <= tempo_max)]
    elif not df_parado.empty:
        tempo_min = df_parado[coluna_tempo].min()
        tempo_max = df_parado[coluna_tempo].max()
        intervalo = tempo_max - tempo_min
        janela_tempo = intervalo * 0.05  # 5%
        janela_inicial = df_parado[df_parado[coluna_tempo] <= (tempo_min + janela_tempo)]
        janela_final = df_parado[df_parado[coluna_tempo] >= (tempo_max - janela_tempo)]
    else:
        janela_inicial = pd.DataFrame()
        janela_final = pd.DataFrame()

    # Calcula médias combustível nas janelas
    media_inicio = sanitizar_coluna(janela_inicial, coluna_fuel).mean() if not janela_inicial.empty else fuel.iloc[0] if not fuel.empty else np.nan
    media_fim = sanitizar_coluna(janela_final, coluna_fuel).mean() if not janela_final.empty else fuel.iloc[-1] if not fuel.empty else np.nan

    # Km inicial e final
    km_inicio = odometro.iloc[0] if not odometro.empty else np.nan
    km_fim = odometro.iloc[-1] if not odometro.empty else np.nan
    km_rodados = km_fim - km_inicio if pd.notna(km_inicio) and pd.notna(km_fim) else np.nan
    if km_rodados < 0:
        km_rodados = np.nan

    # Consumo litros
    diferenca_pct = media_inicio - media_fim
    diferenca_litros = (diferenca_pct / 100) * VOLUME_TANQUE if pd.notna(diferenca_pct) else np.nan
    if diferenca_litros < 0:
        diferenca_litros = np.nan

    # Consumo km/l (apenas se valores válidos)
    consumo = km_rodados / diferenca_litros if (diferenca_litros and diferenca_litros > 0 and km_rodados and km_rodados > 0) else np.nan

    # Mensagem e status
    mensagem = f"Nível inicial: {media_inicio:.1f}% | Nível final: {media_fim:.1f}%\n"
    mensagem += f"Distância inicial: {km_inicio if pd.notna(km_inicio) else 'N/A'} km | Distância final: {km_fim if pd.notna(km_fim) else 'N/A'} km\n"

    if pd.notna(consumo):
        mensagem += f"Combustível consumido: {diferenca_litros:.2f} litros\nConsumo médio: {consumo:.2f} km/l"
        status = "OK"
    else:
        mensagem += "Consumo médio não calculado devido a dados insuficientes ou inconsistentes."
        status = "alerta"

    return {
        "status": status,
        "titulo": coluna_fuel if coluna_fuel else "Nível de Combustível",
        "mensagem": mensagem,
        "valores": {
            "media_inicio_pct": media_inicio,
            "media_fim_pct": media_fim,
            "km_inicio": km_inicio,
            "km_fim": km_fim,
            "diferenca_litros": diferenca_litros,
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
    if valores.get("km_inicio") is not None and not pd.isna(valores["km_inicio"]):
        col3.metric("Distância inicial (km)", f"{valores['km_inicio']:.2f}")
    else:
        col3.metric("Distância inicial (km)", "N/A")

    if valores.get("km_fim") is not None and not pd.isna(valores["km_fim"]):
        col4.metric("Distância final (km)", f"{valores['km_fim']:.2f}")
    else:
        col4.metric("Distância final (km)", "N/A")

    if valores.get("diferenca_litros") is not None and not pd.isna(valores["diferenca_litros"]):
        st.metric("Combustível consumido (L)", f"{valores['diferenca_litros']:.2f}")
    else:
        st.metric("Combustível consumido (L)", "N/A")

    if valores.get("consumo_kml") is not None and not pd.isna(valores["consumo_kml"]):
        st.metric("Consumo médio (km/L)", f"{valores['consumo_kml']:.2f}")
    else:
        st.metric("Consumo médio (km/L)", "N/A")
