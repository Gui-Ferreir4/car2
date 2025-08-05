# modulos/combustivel_avancado.py

import streamlit as st
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas

# Campos de mistura suportados (sem LAMBDA_1)
CAMPOS_MISTURA = {
    "SHRTFT1(%)": "Correção de combustível em curto prazo (STFT).",
    "LONGFT1(%)": "Correção de combustível em longo prazo (LTFT).",
    "AF_RATIO(:1)": "Relação ar-combustível (AFR) medida pelo sensor.",
    "LMD_EGO1(:1)": "Lambda estimado pelo sensor O2 pré-catalisador."
}

def analisar(df, modelo, combustivel, valores_ideais):
    """
    Analisa parâmetros de mistura com métricas detalhadas:
    - Estatísticas básicas
    - Percentual de tempo dentro/fora da faixa
    - Picos máximos e mínimos
    """
    resultados = []
    modelo_key = modelo.lower()
    combustivel_key = combustivel.lower()
    faixas_modelo = valores_ideais.get(modelo_key, {}).get(combustivel_key, {})

    for coluna, descricao in CAMPOS_MISTURA.items():
        serie = sanitizar_coluna(df, coluna)

        if serie.empty:
            resultados.append({
                "status": "erro",
                "titulo": coluna,
                "descricao": descricao,
                "mensagem": f"Sem dados válidos para '{coluna}'.",
                "valores": {}
            })
            continue

        # Estatísticas básicas
        estat = calcular_estatisticas(serie)

        # Faixa ideal do JSON
        chave_json = (
            coluna.replace("(%)", "pct")
                  .replace("(:1)", "")
                  .replace(".", "_")
                  .replace(":", "")
        )
        faixa = faixas_modelo.get(chave_json)
        faixa_ideal = None
        if faixa and isinstance(faixa, list) and len(faixa) == 2:
            faixa_ideal = {"min": faixa[0], "max": faixa[1]}

        # Cálculos avançados: tempo dentro/fora da faixa
        dentro, abaixo, acima = None, None, None
        if faixa_ideal:
            total = len(serie)
            dentro = ((serie >= faixa_ideal["min"]) & (serie <= faixa_ideal["max"])).sum() / total * 100
            abaixo = (serie < faixa_ideal["min"]).sum() / total * 100
            acima = (serie > faixa_ideal["max"]).sum() / total * 100
            status = "OK" if dentro >= 80 else "Alerta"
            mensagem = (
                f"{coluna}: {dentro:.1f}% dentro da faixa "
                f"({abaixo:.1f}% abaixo, {acima:.1f}% acima)."
            )
        else:
            status = "OK"
            mensagem = f"{coluna}: média={estat['média']:.2f} (sem faixa definida no JSON)."

        resultados.append({
            "status": status,
            "titulo": coluna,
            "descricao": descricao,
            "mensagem": mensagem,
            "valores": {
                **estat,
                "faixa_ideal": faixa_ideal,
                "percentual_dentro": dentro,
                "percentual_abaixo": abaixo,
                "percentual_acima": acima
            }
        })

    return resultados


def exibir(resultados: list):
    """
    Exibe análise avançada de mistura em Streamlit
    """
    for r in resultados:
        st.markdown(f"### 🔍 {r['titulo']}")
        st.caption(r["descricao"])

        if r["status"] == "erro":
            st.error(r["mensagem"])
            continue

        # Bloco de métricas principais
        estat = r["valores"]
        col1, col2, col3 = st.columns(3)
        col1.metric("Média", f"{estat['média']:.2f}")
        col2.metric("Mínimo", f"{estat['mínimo']:.2f}")
        col3.metric("Máximo", f"{estat['máximo']:.2f}")

        # Percentuais dentro/fora da faixa
        if estat.get("percentual_dentro") is not None:
            st.caption(
                f"Dentro da faixa: {estat['percentual_dentro']:.1f}% | "
                f"Abaixo: {estat['percentual_abaixo']:.1f}% | "
                f"Acima: {estat['percentual_acima']:.1f}%"
            )

        # Mensagem interpretativa
        if r["status"] == "OK":
            st.success(r["mensagem"])
        else:
            st.warning(f"⚠️ {r['mensagem']}")

        # Faixa ideal
        if estat.get("faixa_ideal"):
            faixa = estat["faixa_ideal"]
            st.caption(f"Faixa ideal: {faixa['min']} a {faixa['max']}")
