import streamlit as st
import pandas as pd
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa o sensor MAP (Manifold Absolute Pressure) em Volts e kPa.
    Verifica variação e consistência com as faixas ideais.
    """
    colunas = ["MAP(V)", "MAP.OBDII(kPa)"]
    resultados = {}
    mensagens = []
    status_geral = "OK"

    for coluna in colunas:
        serie = sanitizar_coluna(df, coluna)
        estat = calcular_estatisticas(serie)

        faixa_ideal = (
            valores_ideais
            .get(modelo, {})
            .get(combustivel, {})
            .get(coluna, {})
        )

        status = avaliar_status(estat["média"], faixa_ideal)
        if status == "Alerta":
            status_geral = "Alerta"

        resultados[coluna] = {
            "estatisticas": estat,
            "status": status,
        }

        # Criar mensagens interpretativas
        if serie.empty:
            mensagens.append(f"{coluna}: sem dados válidos.")
        else:
            variacao = estat["máximo"] - estat["mínimo"] if estat["máximo"] is not None else None
            if variacao is not None and variacao < 1:
                mensagens.append(f"{coluna}: baixa variação → sensor possivelmente travado.")
                status_geral = "Alerta"
            else:
                mensagens.append(f"{coluna}: média={estat['média']}, variação={round(variacao,2) if variacao else '-'}")

    # --- Checagem cruzada MAP em V e kPa ---
    serie_volts = sanitizar_coluna(df, "MAP(V)")
    serie_kpa = sanitizar_coluna(df, "MAP.OBDII(kPa)")

    correlacao = None
    if not serie_volts.empty and not serie_kpa.empty:
        correlacao = serie_volts.corr(serie_kpa)
        if correlacao and correlacao < 0.8:
            mensagens.append("⚠️ MAP: baixa correlação entre V e kPa → possível problema no sensor ou conversão.")
            status_geral = "Alerta"

    return {
        "status": status_geral,
        "mensagem": " | ".join(mensagens),
        "valores": resultados,
        "correlacao_V_kPa": round(correlacao, 3) if correlacao else None
    }


def exibir(resultado: dict):
    """Exibe os resultados da análise do sensor MAP no Streamlit"""
    st.subheader("🌡️ Análise do Sensor MAP")

    status = resultado.get("status", "erro")
    mensagem = resultado.get("mensagem", "")

    # Mensagem geral
    if status == "OK":
        st.success(mensagem)
    elif status == "Alerta":
        st.warning(mensagem)
    else:
        st.error(mensagem)

    # Exibir estatísticas organizadas
    valores = resultado.get("valores", {})
    for coluna, dados in valores.items():
        estat = dados.get("estatisticas", {})
        st.markdown(f"**{coluna}** — Status: {dados.get('status','-')}")
        if estat.get("média") is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric("Média", estat["média"])
            col2.metric("Mínimo", estat["mínimo"])
            col3.metric("Máximo", estat["máximo"])

    # Exibir correlação entre V e kPa
    correlacao = resultado.get("correlacao_V_kPa")
    if correlacao is not None:
        st.caption(f"Correlação MAP(V) x MAP(kPa): {correlacao}")
