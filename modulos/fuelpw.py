import streamlit as st
import numpy as np
import pandas as pd
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa a coluna FUELPW(ms) - tempo de abertura dos injetores.
    Retorna estatísticas e status com base em valores ideais.
    """
    coluna = "FUELPW(ms)"
    serie = sanitizar_coluna(df, coluna)

    if serie.empty:
        return {
            "status": "erro",
            "mensagem": "Não há dados válidos de FUELPW(ms) para análise.",
            "valores": {}
        }

    # Estatísticas básicas
    estat = calcular_estatisticas(serie)

    # Detecta picos de injeção acima de 2x a média
    picos = serie[serie > (estat["média"] * 2)]
    pico_max = float(picos.max()) if not picos.empty else None

    # Avaliação do status
    faixa_ideal = (
        valores_ideais
        .get(modelo, {})
        .get(combustivel, {})
        .get(coluna, {})
    )
    status = avaliar_status(estat["média"], faixa_ideal)

    # Mensagem interpretativa
    if status == "OK":
        mensagem = (
            f"Tempo médio de injeção: {estat['média']} ms — dentro do esperado."
        )
    else:
        mensagem = (
            f"Tempo médio de injeção fora da faixa ideal. "
            f"Média={estat['média']} ms | Pico={pico_max} ms."
        )

    # Resultado consolidado
    return {
        "status": status,
        "mensagem": mensagem,
        "valores": {
            "estatisticas": estat,
            "pico_max": pico_max,
            "picos_detectados": int(len(picos)),
        }
    }


def exibir(resultado: dict):
    """Exibe os resultados do FUELPW(ms) no Streamlit"""
    st.subheader("⛽ Análise de FUELPW (Tempo de Injeção)")

    status = resultado.get("status", "erro")
    mensagem = resultado.get("mensagem", "")

    # Mensagem geral
    if status == "OK":
        st.success(mensagem)
    elif status == "Alerta":
        st.warning(mensagem)
    else:
        st.error(mensagem)

    valores = resultado.get("valores", {})
    estat = valores.get("estatisticas", {})

    if estat:
        col1, col2, col3 = st.columns(3)
        col1.metric("Média (ms)", estat["média"])
        col2.metric("Máximo (ms)", estat["máximo"])
        col3.metric("Mínimo (ms)", estat["mínimo"])

        # Exibe picos se houver
        pico_max = valores.get("pico_max")
        if pico_max:
            st.info(f"🔹 Pico de injeção detectado: {pico_max} ms "
                    f"({valores['picos_detectados']} registros)")
