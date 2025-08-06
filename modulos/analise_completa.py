# modulos/analise_completa.py
# Continuação do arquivo: modulos/analise_completa.py
import json
import streamlit as st
import pandas as pd
import numpy as np

def estatisticas_numericas(serie: pd.Series) -> dict:
    """Calcula estatísticas detalhadas para uma série numérica."""
    return {
        "min": float(serie.min()),
        "media": float(serie.mean()),
        "max": float(serie.max()),
        "mediana": float(serie.median()),
        "desvio_padrao": float(serie.std(ddof=0)),
        "q1": float(serie.quantile(0.25)),
        "q3": float(serie.quantile(0.75)),
    }

def top3_valores(serie: pd.Series) -> list:
    """
    Retorna os 3 valores mais frequentes com porcentagem de aparição.
    Para numéricos, arredonda em 2 casas.
    """
    if pd.api.types.is_numeric_dtype(serie):
        serie = serie.round(2)
    contagem = serie.value_counts(normalize=True).head(3) * 100
    return [
        {"valor": val, "percentual": round(freq, 2)}
        for val, freq in zip(contagem.index.tolist(), contagem.values.tolist())
    ]

def detectar_comportamento_numerico(serie: pd.Series, valores_esp: list | None) -> list:
    """
    Detecta comportamentos suspeitos para sensores numéricos:
    - Sensor travado (pouca variação)
    - Tempo dentro/fora da faixa esperada
    """
    comportamento = []

    if serie.std(ddof=0) < 0.01:
        comportamento.append("Pouca variação (sensor possivelmente travado)")

    if valores_esp and isinstance(valores_esp, (list, tuple)) and len(valores_esp) == 2:
        faixa_min, faixa_max = valores_esp
        dentro = serie.between(faixa_min, faixa_max).mean() * 100
        if dentro < 75:
            comportamento.append(f"Só {dentro:.1f}% dentro da faixa ideal")
        else:
            comportamento.append(f"{dentro:.1f}% dentro da faixa ideal")

    return comportamento

def detectar_comportamento_categorico(serie: pd.Series, valores_esp: list | None) -> list:
    """Analisa colunas categóricas para observações úteis."""
    observacoes = [f"{len(serie.unique())} valores distintos detectados"]

    if valores_esp:
        desconhecidos = [v for v in serie.unique() if v not in valores_esp]
        if desconhecidos:
            observacoes.append(f"Valores inesperados detectados: {desconhecidos[:3]}")

    return observacoes

# Continuação do arquivo: modulos/analise_completa.py

def analisar_dataframe_completo(df: pd.DataFrame, valores_ideais: dict | None = None) -> dict:
    """
    Analisa todas as colunas do DataFrame e retorna um JSON estruturado com:
    - Estatísticas numéricas
    - Top 3 valores
    - Detecção de comportamentos
    """
    if valores_ideais is None:
        valores_ideais = {}

    resultado = {}

    colunas = [
        "time(ms)", "IC_SPDMTR(km/h)", "RPM(1/min)", "ODOMETER(km)", "TRIP_ODOM(km)",
        "ENGI_IDLE", "OPENLOOP", "BOO_ABS", "ENG_STAB", "FUELLVL(%)", "FUELPW(ms)",
        "FUEL_CORR(:1)", "AF_LEARN", "SHRTFT1(%)", "LONGFT1(%)", "AF_RATIO(:1)",
        "LMD_EGO1(:1)", "O2S11_V(V)", "ECT_GAUGE(Â°C)", "ECT(Â°C)", "IAT(Â°C)", 
        "MAP(V)", "MAP.OBDII(kPa)", "MIXCNT_STAT", "LAMBDA_1", "SPKDUR_1(ms)",
        "SPKDUR_2(ms)", "SPKDUR_3(ms)", "SPKDUR_4(ms)", "LF_WSPD(km/h)", 
        "RF_WSPD(km/h)", "LR_WSPD(km/h)", "RR_WSPD(km/h)", "VBAT_1(V)", 
        "BRK_LVL", "FUEL_RESER", "PSP", "FANLO", "FANHI", "ANY_DR_AJ", "T_AJAR"
    ]

    for coluna in colunas:
        if coluna not in df.columns:
            resultado[coluna] = {
                "status": "sem_dados",
                "mensagem": f"Coluna '{coluna}' não encontrada no DataFrame."
            }
            continue

        serie = df[coluna].dropna()

        # Detecta se é numérica ou categórica
        if pd.api.types.is_numeric_dtype(serie):
            # Estatísticas numéricas
            stats = estatisticas_numericas(serie)
            top3 = top3_valores(serie)

            faixa_ideal = valores_ideais.get(coluna, None)
            comportamento = detectar_comportamento_numerico(serie, faixa_ideal)

            resultado[coluna] = {
                "tipo": "numerico",
                "valores_esperados": faixa_ideal,
                "estatisticas": stats,
                "top3_valores": top3,
                "comportamento": comportamento
            }

        else:
            # Campos categóricos
            serie = serie.astype(str).str.strip().str.lower()
            top3 = top3_valores(serie)

            valores_esp = valores_ideais.get(coluna, None)
            comportamento = detectar_comportamento_categorico(serie, valores_esp)

            resultado[coluna] = {
                "tipo": "categorico",
                "valores_esperados": valores_esp,
                "top3_valores": top3,
                "comportamento": comportamento
            }

    return resultado


def exportar_json(resultado: dict, caminho_arquivo: str = "analise_completa.json"):
    """
    Exporta o dicionário de análise completa para um arquivo JSON legível.
    """
    try:
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Erro ao exportar JSON: {e}")
        return False

def analisar(df, modelo=None, combustivel=None, valores_ideais=None):
    """Alias para manter compatibilidade com o app principal."""
    return analisar_dataframe_completo(df, valores_ideais)

def exibir(resultado):
    """Alias para manter compatibilidade com o app principal."""
    return exibir_streamlit(resultado)

def exibir_streamlit(resultado: dict):
    """
    Exibe o JSON estruturado no Streamlit de forma organizada.
    - Mostra blocos por tipo de dado (numérico ou categórico)
    - Indica status e principais insights
    """
    st.subheader("📊 Análise Completa do DataFrame")

    for coluna, dados in resultado.items():
        st.markdown(f"### 🔹 {coluna}")

        # Colunas que não tiveram dados
        if dados.get("status") == "sem_dados":
            st.error(dados["mensagem"])
            continue

        # -------------------------------
        # Para dados numéricos
        # -------------------------------
        if dados["tipo"] == "numerico":
            estat = dados.get("estatisticas", {})
            top3 = dados.get("top3_valores", [])
            comportamento = dados.get("comportamento", [])

            # Estatísticas básicas em 3 colunas
            c1, c2, c3 = st.columns(3)
            c1.metric("Média", f"{estat.get('media', 'N/A'):.2f}" if estat.get("media") is not None else "N/A")
            c2.metric("Mínimo", f"{estat.get('minimo', 'N/A'):.2f}" if estat.get("minimo") is not None else "N/A")
            c3.metric("Máximo", f"{estat.get('maximo', 'N/A'):.2f}" if estat.get("maximo") is not None else "N/A")

            # Top 3 valores
            if top3:
                st.caption("Top 3 valores mais frequentes:")
                for item in top3:
                    st.write(f"- {item['valor']} → {item['percentual']:.1f}%")

            # Comportamento
            if comportamento:
                st.caption("🔍 Comportamento detectado:")
                for obs in comportamento:
                    st.write(f"- {obs}")

        # -------------------------------
        # Para dados categóricos
        # -------------------------------
        elif dados["tipo"] == "categorico":
            top3 = dados.get("top3_valores", [])
            comportamento = dados.get("comportamento", [])

            if top3:
                st.caption("Top 3 valores mais frequentes:")
                for item in top3:
                    st.write(f"- {item['valor']} → {item['percentual']:.1f}%")

            if comportamento:
                st.caption("🔍 Comportamento detectado:")
                for obs in comportamento:
                    st.write(f"- {obs}")

        st.markdown("---")

