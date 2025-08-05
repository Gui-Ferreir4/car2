import streamlit as st
import pandas as pd
from utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

COLUNAS_SPK = ["SPKDUR_1(ms)", "SPKDUR_2(ms)", "SPKDUR_3(ms)", "SPKDUR_4(ms)"]

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa os tempos de centelha (spark duration) dos 4 cilindros.
    Identifica variações anormais e avalia consistência entre cilindros.
    """
    resultados = {}
    medias_cilindros = []
    status_geral = "OK"
    mensagens = []

    # Loop pelos 4 cilindros
    for coluna in COLUNAS_SPK:
        serie = sanitizar_coluna(df, coluna)
        estat = calcular_estatisticas(serie)

        # Obtém faixa ideal do JSON, se existir
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

        if estat["média"] is not None:
            medias_cilindros.append(estat["média"])

        mensagens.append(
            f"{coluna}: média={estat['média']}, min={estat['mínimo']}, max={estat['máximo']}"
            if estat["média"] is not None
            else f"{coluna}: sem dados válidos"
        )

    # Avaliação de balanceamento entre cilindros
    variacao_max = None
    if len(medias_cilindros) >= 2:
        variacao_max = max(medias_cilindros) - min(medias_cilindros)
        perc_diff = (variacao_max / max(medias_cilindros)) * 100 if max(medias_cilindros) else 0
        resultados["desbalanceamento_%"] = round(perc_diff, 2)

        if perc_diff > 20:  # 20% de diferença entre cilindros
            status_geral = "Alerta"
            mensagens.append(f"⚠️ Diferença entre cilindros: {round(perc_diff,2)}% → possível desbalanceamento")

    return {
        "status": status_geral,
        "mensagem": " | ".join(mensagens),
        "valores": resultados
    }


def exibir(resultado: dict):
    """Exibe a análise de tempos de centelha (spark duration)"""
    st.subheader("⚡ Análise do Tempo de Centelha (Spark Duration)")

    status = resultado.get("status", "erro")
    mensagem = resultado.get("mensagem", "")

    if status == "OK":
        st.success(mensagem)
    elif status == "Alerta":
        st.warning(mensagem)
    else:
        st.error(mensagem)

    valores = resultado.get("valores", {})
    for coluna in COLUNAS_SPK:
        if coluna in valores:
            estat = valores[coluna]["estatisticas"]
            st.markdown(f"**{coluna}** — Status: {valores[coluna]['status']}")
            if estat["média"] is not None:
                c1, c2, c3 = st.columns(3)
                c1.metric("Média (ms)", estat["média"])
                c2.metric("Mínimo (ms)", estat["mínimo"])
                c3.metric("Máximo (ms)", estat["máximo"])

    if "desbalanceamento_%" in valores:
        st.caption(f"Desbalanceamento entre cilindros: {valores['desbalanceamento_%']}%")
