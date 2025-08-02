import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status, interpretar_status

def analisar(df, modelo, combustivel, valores_ideais):
    """
    Analisa a coluna ECT_GAUGE(°C) do DataFrame:
    - Limpeza dos dados
    - Cálculo de estatísticas
    - Comparação com valores ideais
    """
    coluna = "ECT_GAUGE(°C)"

    # Sanitiza a coluna
    serie = sanitizar_coluna(df, coluna)
    if serie.empty:
        return {
            "status": "erro",
            "titulo": coluna,
            "mensagem": f"Sem dados válidos para '{coluna}'.",
            "valores": {}
        }

    # Estatísticas básicas
    estatisticas = calcular_estatisticas(serie)

    # Busca faixa ideal no JSON
    faixa_ideal = {"min": 80, "max": 100}  # fallback
    try:
        faixa = (
            valores_ideais
            .get(modelo.lower(), {})
            .get(combustivel.lower(), {})
            .get("ECT_GAUGE")
        )
        if faixa and isinstance(faixa, list) and len(faixa) == 2:
            faixa_ideal = {"min": faixa[0], "max": faixa[1]}
    except Exception:
        pass

    # Avalia status com base na média
    status = avaliar_status(estatisticas["média"], faixa_ideal)

    # Interpretação detalhada
    if status == "OK":
        mensagem = "Temperatura do motor dentro da faixa normal de operação."
    elif estatisticas["média"] < faixa_ideal["min"]:
        mensagem = (
            "Motor operando frio. Possível termostato aberto ou sensor ECT defeituoso."
        )
    elif estatisticas["média"] > faixa_ideal["max"]:
        mensagem = (
            "Temperatura acima do ideal. Possível superaquecimento ou falha na ventoinha."
        )
    else:
        mensagem = interpretar_status(coluna, status)

    return {
        "status": status,
        "titulo": coluna,
        "mensagem": mensagem,
        "valores": {
            **estatisticas,
            "faixa_ideal": faixa_ideal
        }
    }


def exibir(resultado: dict):
    """
    Exibe o resultado no Streamlit
    """
    st.markdown(f"### 🌡️ {resultado['titulo']}")

    if resultado["status"] == "erro":
        st.error(resultado["mensagem"])
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Média", f"{resultado['valores']['média']}°C")
    col2.metric("Mínimo", f"{resultado['valores']['mínimo']}°C")
    col3.metric("Máximo", f"{resultado['valores']['máximo']}°C")

    # Status visual
    if resultado["status"] == "OK":
        st.success(resultado["mensagem"])
    else:
        st.warning(f"⚠️ {resultado['mensagem']}")

    # Mostra faixa ideal
    faixa = resultado["valores"]["faixa_ideal"]
    st.caption(f"Faixa ideal: {faixa['min']}°C a {faixa['max']}°C")
