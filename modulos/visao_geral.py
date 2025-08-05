import streamlit as st
import pandas as pd
from modulos.utilitarios import sanitizar_coluna, calcular_estatisticas, avaliar_status

# Descrições breves dos campos
DESCRICOES = {
    "BRK_LVL": "Nível do freio (Brake Level) indica pressão ou estado do sistema de freios.",
    "FUEL_RESER": "Nível do tanquinho de partida a frio.",
    "PSP ANY_DR_AJ": "Status do sensor de porta (qualquer porta aberta).",
    "T_AJAR": "Indicador de porta mala aberto."
}

def calcular_proporcao_dentro_faixa(serie: pd.Series, faixa: dict) -> float:
    """Calcula a proporção do tempo em que os valores estão dentro da faixa ideal."""
    if serie.empty or faixa is None:
        return 0.0
    dentro = serie[(serie >= faixa["min"]) & (serie <= faixa["max"])]
    proporcao = len(dentro) / len(serie) if len(serie) > 0 else 0.0
    return proporcao

def analisar(df: pd.DataFrame, modelo: str, combustivel: str, valores_ideais: dict) -> dict:
    """
    Analisa os campos da visão geral da viagem:
    - descrição breve de cada campo,
    - cálculo de estatísticas,
    - proporção do tempo dentro da faixa ideal,
    - status com base nessa proporção (<75% considerado alerta).
    """
    campos = ["BRK_LVL", "FUEL_RESER", "PSP ANY_DR_AJ", "T_AJAR"]
    resultado = {
        "status": "OK",
        "mensagem": "",
        "valores": {}
    }
    mensagens = []

    for campo in campos:
        serie = sanitizar_coluna(df, campo)
        estat = calcular_estatisticas(serie)

        # Obter faixa ideal do JSON, se disponível
        faixa_ideal = None
        try:
            faixa = valores_ideais.get(modelo.lower(), {}).get(combustivel.lower(), {}).get(campo)
            if faixa and isinstance(faixa, list) and len(faixa) == 2:
                faixa_ideal = {"min": faixa[0], "max": faixa[1]}
        except Exception:
            faixa_ideal = None

        proporcao = calcular_proporcao_dentro_faixa(serie, faixa_ideal) if faixa_ideal else 0.0
        status = "OK" if proporcao >= 0.75 else "Alerta"

        # Atualiza status geral se algum campo estiver em alerta
        if status == "Alerta":
            resultado["status"] = "Alerta"

        media_val = estat.get('média')
        media_str = f"{media_val:.2f}" if isinstance(media_val, (int, float)) else "N/A"
        
        mensagem_campo = (
            f"{campo}: {DESCRICOES.get(campo, '')} "
            f"Média: {media_str} | "
            f"Tempo dentro da faixa ideal: {proporcao*100:.1f}% "
            f"(Faixa ideal: {faixa_ideal if faixa_ideal else 'N/D'})"
        )
        mensagens.append(mensagem_campo)

        resultado["valores"][campo] = {
            "descricao": DESCRICOES.get(campo, ""),
            "estatisticas": estat,
            "faixa_ideal": faixa_ideal,
            "proporcao_dentro_%": round(proporcao * 100, 2),
            "status": status
        }

    resultado["mensagem"] = "\n".join(mensagens)
    return resultado


def exibir(resultado: dict):
    st.subheader("🚗 Visão Geral da Viagem")

    valores = resultado.get("valores", {})
    status_geral = resultado.get("status", "OK")

    for campo, dados in valores.items():
        st.markdown(f"### {campo}")
        st.write(dados.get("descricao", ""))
        estat = dados.get("estatisticas", {})
        faixa = dados.get("faixa_ideal", None)
        proporcao = dados.get("proporcao_dentro_%", None)
        status = dados.get("status", "OK")

        # Exibe estatísticas básicas se disponíveis
        if estat and estat.get("média") is not None:
            col1, col2, col3 = st.columns(3)
            col1.metric("Média", f"{estat['média']:.2f}")
            col2.metric("Mínimo", f"{estat['mínimo']:.2f}")
            col3.metric("Máximo", f"{estat['máximo']:.2f}")
        else:
            st.write("Sem dados numéricos válidos.")

        # Exibe faixa ideal e proporção dentro da faixa
        if faixa:
            st.caption(f"Faixa ideal: {faixa['min']} a {faixa['max']}")
        if proporcao is not None:
            st.caption(f"Tempo dentro da faixa ideal: {proporcao}%")

        # Mensagem de status
        if status == "OK":
            st.success("Status: OK")
        else:
            st.warning("⚠️ Status: Alerta — menos de 75% do tempo dentro da faixa ideal")

    # Mensagem geral no topo
    if status_geral == "Alerta":
        st.warning("⚠️ Atenção: Alguns parâmetros apresentam mais de 25% do tempo fora da faixa ideal.")
    else:
        st.success("✅ Todos os parâmetros estão dentro do esperado na maior parte do tempo.")
