# modulos/correcao_combustivel.py

import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status, interpretar_status

# Lista de colunas suportadas neste módulo
COLUNAS_SUPORTADAS = [
    "SHRTFT1(%)",
    "LONGFT1(%)",
    "AF_RATIO(:1)",
    "LAMBDA_1",
    "LMD_EGO1(:1)"
]

def analisar(df, modelo, combustivel, valores_ideais):
    """
    Analisa todos os parâmetros de mistura (STFT, LTFT, AFR, Lambda, EGO)
    usando o JSON de valores ideais.
    Retorna uma lista de resultados por coluna.
    """
    resultados = []

    modelo_key = modelo.lower()
    combustivel_key = combustivel.lower()
    faixas_modelo = valores_ideais.get(modelo_key, {}).get(combustivel_key, {})

    for coluna in COLUNAS_SUPORTADAS:
        # Sanitiza dados
        serie = sanitizar_coluna(df, coluna)
        if serie.empty:
            resultados.append({
                "status": "erro",
                "titulo": coluna,
                "mensagem": f"Sem dados válidos para '{coluna}'.",
                "valores": {}
            })
            continue

        # Estatísticas
        estatisticas = calcular_estatisticas(serie)

        # Faixa ideal
        faixa_ideal = {"min": -9999, "max": 9999}  # fallback
        chave_json = (
            coluna.replace("(%)", "pct")
                  .replace("(:1)", "")
                  .replace(".", "_")
                  .replace(":", "")
        )  # Normaliza o nome para o JSON

        faixa = faixas_modelo.get(chave_json)
        if faixa and isinstance(faixa, list) and len(faixa) == 2:
            faixa_ideal = {"min": faixa[0], "max": faixa[1]}

        # Status com base na média
        status = avaliar_status(estatisticas["média"], faixa_ideal)
        mensagem = interpretar_status(coluna, status)

        resultados.append({
            "status": status,
            "titulo": coluna,
            "mensagem": mensagem,
            "valores": {
                **estatisticas,
                "faixa_ideal": faixa_ideal
            }
        })

    return resultados


def exibir(resultados: list):
    """
    Exibe uma lista de resultados no Streamlit em formato uniforme
    """
    for resultado in resultados:
        st.markdown(f"### 🔍 {resultado['titulo']}")

        if resultado["status"] == "erro":
            st.error(resultado["mensagem"])
            continue

        col1, col2, col3 = st.columns(3)
        col1.metric("Média", f"{resultado['valores']['média']:.2f}")
        col2.metric("Mínimo", f"{resultado['valores']['mínimo']:.2f}")
        col3.metric("Máximo", f"{resultado['valores']['máximo']:.2f}")

        # Status
        if resultado["status"] == "OK":
            st.success(resultado["mensagem"])
        else:
            st.warning(f"⚠️ {resultado['mensagem']}")

        # Faixa ideal
        faixa = resultado["valores"]["faixa_ideal"]
        st.caption(f"Faixa ideal: {faixa['min']} a {faixa['max']}")
