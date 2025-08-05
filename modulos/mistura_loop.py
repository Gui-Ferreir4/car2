import streamlit as st
import pandas as pd
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas

COLUNAS = [
    "MIXCNT_STAT",
    "LAMBDA_1",
    "OPENLOOP",
    "FUEL_CORR(:1)",
    "AF_LEARN"
]

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa o comportamento do controle de mistura e do loop da ECU.
    """
    resultados = {}
    mensagens = []
    status_geral = "OK"

    # 1. Lambda
    lambda_series = sanitizar_coluna(df, "LAMBDA_1")
    estat_lambda = calcular_estatisticas(lambda_series)
    resultados["lambda"] = estat_lambda
    if estat_lambda["média"] is not None:
        if estat_lambda["média"] < 0.95 or estat_lambda["média"] > 1.05:
            status_geral = "Alerta"
            mensagens.append(f"Lambda médio {estat_lambda['média']} → mistura fora do ideal.")
        else:
            mensagens.append(f"Lambda médio {estat_lambda['média']} → dentro do ideal.")

    # 2. Open Loop vs Closed Loop
    openloop_col = df.get("OPENLOOP")
    closed_loop_pct = None
    if openloop_col is not None:
        openloop_num = openloop_col.astype(str).str.strip().str.lower()
        openloop_num = openloop_num.replace({
            "sim": 1, "não": 0, "nao": 0, "true": 1, "false": 0
        })
        openloop_num = pd.to_numeric(openloop_num, errors='coerce').fillna(0).astype(int)
        closed_loop_pct = round((openloop_num == 0).sum() / len(openloop_num) * 100, 2)
        resultados["closed_loop_%"] = closed_loop_pct
        mensagens.append(f"Closed Loop: {closed_loop_pct}% do tempo")

        if closed_loop_pct < 70:
            status_geral = "Alerta"
            mensagens.append("Pouco tempo em closed loop → possível problema de aquecimento ou O2.")

    # 3. Fuel Corrections
    for coluna in ["FUEL_CORR(:1)", "AF_LEARN"]:
        serie = sanitizar_coluna(df, coluna)
        estat = calcular_estatisticas(serie)
        resultados[coluna] = estat
        if estat["média"] is not None:
            mensagens.append(f"{coluna} médio: {estat['média']}")

    # 4. MIXCNT_STAT (contagem de estados)
    if "MIXCNT_STAT" in df.columns:
        mix_counts = df["MIXCNT_STAT"].astype(str).value_counts().to_dict()
        resultados["mixcnt_stat"] = mix_counts
        mensagens.append(f"Estados de mistura: {mix_counts}")

    return {
        "status": status_geral,
        "mensagem": " | ".join(mensagens),
        "valores": resultados
    }


def exibir(resultado: dict):
    """Exibe a análise de mistura e loop de combustível."""
    st.subheader("🔄 Controle de Mistura e Loop da ECU")

    status = resultado.get("status", "erro")
    mensagem = resultado.get("mensagem", "")

    if status == "OK":
        st.success(mensagem)
    elif status == "Alerta":
        st.warning(mensagem)
    else:
        st.error(mensagem)

    valores = resultado.get("valores", {})
    if "lambda" in valores:
        st.metric("Lambda Médio", valores["lambda"]["média"])
    if "closed_loop_%" in valores:
        st.metric("Closed Loop (%)", valores["closed_loop_%"])
