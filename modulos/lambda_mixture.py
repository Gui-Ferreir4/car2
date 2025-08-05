import streamlit as st
import pandas as pd
from utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa mistura ar/combustível e sensores lambda:
    - AF_RATIO(:1)
    - LMD_EGO1(:1)
    - O2S11_V(V)
    """

    colunas = ["AF_RATIO(:1)", "LMD_EGO1(:1)", "O2S11_V(V)"]
    resultados = {}
    status_geral = "OK"
    mensagens = []

    # --- Análise de cada coluna ---
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

        # Mensagem interpretativa por coluna
        if serie.empty:
            mensagens.append(f"{coluna}: sem dados válidos para análise.")
        else:
            if status == "OK":
                mensagens.append(f"{coluna}: dentro da faixa ideal. Média={estat['média']}")
            else:
                mensagens.append(f"{coluna}: fora da faixa ideal. Média={estat['média']}")

    # --- Análise especial do sensor O2 ---
    o2_serie = sanitizar_coluna(df, "O2S11_V(V)")
    if not o2_serie.empty:
        variacao_o2 = o2_serie.max() - o2_serie.min()
        resultados["O2S11_V(V)"]["variacao"] = round(variacao_o2, 3)

        if variacao_o2 < 0.2:
            mensagens.append("O2S11_V: baixa oscilação detectada → mistura constante ou sensor lento.")
            status_geral = "Alerta"

    # Resultado final
    return {
        "status": status_geral,
        "mensagem": " | ".join(mensagens),
        "valores": resultados,
    }


def exibir(resultado: dict):
    """Exibe resultados da análise de mistura/lambda no Streamlit"""
    st.subheader("🔬 Análise da Mistura e Sensores Lambda")

    status = resultado.get("status", "erro")
    mensagem = resultado.get("mensagem", "")

    # Mensagem geral
    if status == "OK":
        st.success(mensagem)
    elif status == "Alerta":
        st.warning(mensagem)
    else:
        st.error(mensagem)

    # Exibir estatísticas
    valores = resultado.get("valores", {})
    for coluna, dados in valores.items():
        estat = dados.get("estatisticas", {})
        st.markdown(f"**{coluna}** — Status: {dados.get('status','-')}")
        if estat["média"] is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric("Média", estat["média"])
            col2.metric("Mínimo", estat["mínimo"])
            col3.metric("Máximo", estat["máximo"])

        # Mostrar variação do O2
        if coluna == "O2S11_V(V)" and "variacao" in dados:
            st.caption(f"Variação do O2S11: {dados['variacao']} V")
