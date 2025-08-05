import pandas as pd
import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas

# --- Faixas ideais esperadas para cada sensor ---
FAIXAS_IDEAL = {
    "BRK_LVL": (1, 1),        # Sempre 1 (nível OK)
    "FUEL_RESER": (0, 0),     # 0 = Não acionado
    "PSP": (0, 0),            # 0 = Sem pressão anormal
    "ANY_DR_AJ": (0, 0),      # 0 = Nenhuma porta aberta
    "T_AJAR": (0, 0),         # 0 = Porta-malas fechado
}

DESCRICOES = {
    "BRK_LVL": "Nível do fluido de freio (1=OK, 0=Baixo)",
    "FUEL_RESER": "Indicador do tanquinho de partida a frio (1=ativo, 0=desligado)",
    "PSP": "Pressão da direção hidráulica (1=ativa, 0=normal)",
    "ANY_DR_AJ": "Indica se alguma porta ficou aberta em movimento",
    "T_AJAR": "Indica porta-malas aberto (1=aberto, 0=fechado)"
}

def analisar(df, modelo=None, combustivel=None, valores_ideais=None):
    """
    Analisa dados gerais da viagem e sensores de segurança.
    Retorna estatísticas detalhadas e status interpretativo.
    """
    resultado = {
        "status": "OK",
        "mensagem": "",
        "resumo_viagem": {},
        "sensores": {}
    }

    # --- 1. Dados gerais da viagem ---
    distancia_km = None
    if "TRIP_ODOM(km)" in df.columns:
        trip = sanitizar_coluna(df, "TRIP_ODOM(km)")
        if not trip.empty:
            distancia_km = trip.max() - trip.min()
    elif "ODOMETER(km)" in df.columns:
        odom = sanitizar_coluna(df, "ODOMETER(km)")
        if not odom.empty:
            distancia_km = odom.max() - odom.min()

    duracao_s = None
    if "time(ms)" in df.columns:
        duracao_s = (df["time(ms)"].max() - df["time(ms)"].min()) / 1000.0

    vel_series = sanitizar_coluna(df, "IC_SPDMTR(km/h)")
    rpm_series = sanitizar_coluna(df, "RPM")

    resultado["resumo_viagem"] = {
        "Distância (km)": round(distancia_km, 2) if distancia_km else None,
        "Duração (h)": round(duracao_s / 3600, 2) if duracao_s else None,
        "Velocidade Média": round(vel_series.mean(), 2) if not vel_series.empty else None,
        "Velocidade Máx": round(vel_series.max(), 2) if not vel_series.empty else None,
        "RPM Médio": round(rpm_series.mean(), 0) if not rpm_series.empty else None,
        "RPM Máx": round(rpm_series.max(), 0) if not rpm_series.empty else None
    }

    # --- 2. Sensores / Atuadores ---
    for campo, faixa in FAIXAS_IDEAL.items():
        serie = sanitizar_coluna(df, campo)
        if serie.empty:
            resultado["sensores"][campo] = {
                "descricao": DESCRICOES.get(campo, ""),
                "status": "erro",
                "mensagem": f"Sem dados para {campo}",
                "estatisticas": {}
            }
            resultado["status"] = "Alerta"
            continue

        # Estatísticas básicas
        estat = calcular_estatisticas(serie)

        # Proporção de tempo dentro da faixa
        dentro = ((serie >= faixa[0]) & (serie <= faixa[1])).sum()
        total = len(serie)
        proporcao_dentro = round(dentro / total * 100, 2) if total > 0 else 0

        # Status
        if proporcao_dentro >= 75:
            status = "OK"
        elif proporcao_dentro >= 50:
            status = "Alerta"
            resultado["status"] = "Alerta"
        else:
            status = "Crítico"
            resultado["status"] = "Alerta"

        resultado["sensores"][campo] = {
            "descricao": DESCRICOES.get(campo, ""),
            "status": status,
            "proporcao_dentro_%": proporcao_dentro,
            "estatisticas": estat
        }

    # Monta mensagem geral
    status_sensores = [f"{c}: {v['status']}" for c, v in resultado["sensores"].items()]
    resultado["mensagem"] = " | ".join(status_sensores)

    return resultado

def exibir(resultado: dict):
    """Exibe visão geral da viagem no Streamlit"""
    st.subheader("🚗 Visão Geral da Viagem")

    # --- Resumo da Viagem ---
    st.markdown("### 📊 Dados da Viagem")
    colunas = st.columns(len(resultado["resumo_viagem"]))
    for i, (k, v) in enumerate(resultado["resumo_viagem"].items()):
        colunas[i].metric(k, v if v is not None else "N/A")

    # --- Sensores ---
    st.markdown("### 🔹 Sensores e Atuadores Críticos")
    for campo, dados in resultado["sensores"].items():
        st.markdown(f"**{campo}** — {dados['descricao']}")
        if dados["status"] == "OK":
            st.success(f"{dados['status']} — {dados['proporcao_dentro_%']}% dentro da faixa ideal")
        elif dados["status"] == "Alerta":
            st.warning(f"{dados['status']} — {dados['proporcao_dentro_%']}% dentro da faixa ideal")
        else:
            st.error(f"{dados['status']} — {dados['proporcao_dentro_%']}% dentro da faixa ideal")
