import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status, interpretar_status

def analisar(df, modelo, combustivel, valores_ideais):
    """
    Analisa a coluna SHRTFT1(%) do DataFrame:
    - Limpeza dos dados
    - Cálculo de estatísticas
    - Comparação com valores ideais
    """
    coluna = 'SHRTFT1(%)'

    # Sanitiza a coluna antes de qualquer cálculo
    serie = sanitizar_coluna(df, coluna)
    if serie.empty:
        return {
            "status": "erro",
            "titulo": coluna,
            "mensagem": f"Sem dados válidos para '{coluna}'.",
            "valores": {}
        }

    # Calcula estatísticas básicas
    estatisticas = calcular_estatisticas(serie)

    # Busca faixa ideal no JSON de valores
    faixa_ideal = {"min": -100, "max": 100}  # fallback
    try:
        faixa = valores_ideais.get(modelo.lower(), {}).get(combustivel.lower(), {}).get("SHRTFT1pct")
        if faixa and isinstance(faixa, list) and len(faixa) == 2:
            faixa_ideal = {"min": faixa[0], "max": faixa[1]}
    except Exception:
        pass

    # Avalia status com base na média
    status = avaliar_status(estatisticas["média"], faixa_ideal)
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
    st.markdown(f"### 🔍 {resultado['titulo']}")

    if resultado["status"] == "erro":
        st.error(resultado["mensagem"])
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Média", f"{resultado['valores']['média']}%")
    col2.metric("Mínimo", f"{resultado['valores']['mínimo']}%")
    col3.metric("Máximo", f"{resultado['valores']['máximo']}%")

    # Exibe status interpretativo
    if resultado["status"] == "OK":
        st.success(resultado["mensagem"])
    else:
        st.warning(f"⚠️ {resultado['mensagem']}")

    # Mostra faixa ideal
    faixa = resultado["valores"]["faixa_ideal"]
    st.caption(f"Faixa ideal: {faixa['min']}% a {faixa['max']}%")
