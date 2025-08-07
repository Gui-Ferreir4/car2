import pandas as pd
import numpy as np
import streamlit as st

# =========================
# Configurações globais
# =========================
st.set_page_config(page_title="Análise de Dados OBD", layout="wide")

# =========================
# Funções auxiliares
# =========================
def media_segura(serie):
    """Calcula a média ignorando NaN."""
    return np.nanmean(serie) if not serie.empty else np.nan

def status_valor(valor, ideal_min=None, ideal_max=None):
    """
    Retorna status textual e cor de alerta baseado no intervalo ideal.
    """
    if valor is None or np.isnan(valor):
        return "Sem dados", "⚪"
    if ideal_min is not None and valor < ideal_min:
        return "Baixo", "🔵"
    if ideal_max is not None and valor > ideal_max:
        return "Alto", "🔴"
    return "Normal", "🟢"

def formatar_resultado(nome, valor, unidade, status, cor):
    """Retorna dict compacto com todos os dados."""
    return {
        "Parâmetro": nome,
        "Valor Médio": f"{valor:.3f} {unidade}" if valor is not None else "-",
        "Status": f"{cor} {status}"
    }

# =========================
# Função principal de análise
# =========================

def analisar(df: pd.DataFrame) -> dict:
    """
    Recebe DataFrame com dados OBD e retorna dict com análise estruturada.
    Aplica médias winsorizadas e outras análises conforme solicitado.
    """

    resultado = {}

    # ============ time(ms) ============
    if "time(ms)" in df.columns:
        tempo_segundos = df["time(ms)"].max() / 1000 if not df["time(ms)"].empty else 0
        horas = int(tempo_segundos // 3600)
        minutos = int((tempo_segundos % 3600) // 60)
        segundos = int(tempo_segundos % 60)
        resultado["time(ms)"] = {
            "Descrição": "Tempo total da viagem (HH:MM:SS)",
            "Valor": f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        }
    else:
        resultado["time(ms)"] = {"Descrição": "Tempo total da viagem (HH:MM:SS)", "Valor": "Sem dados"}

    # ============ IC_SPDMTR(km/h) ============
    if "IC_SPDMTR(km/h)" in df.columns:
        col = df["IC_SPDMTR(km/h)"].dropna()
        if not col.empty:
            winsor = col.clip(lower=col.quantile(0.05), upper=col.quantile(0.95))
            media_wins = winsor.mean()
            resultado["IC_SPDMTR(km/h)"] = {
                "Descrição": "Velocidade do veículo em km/h",
                "Mínimo": round(col.min(), 2),
                "Mediana": round(col.median(), 2),
                "Máximo": round(col.max(), 2),
                "Média Winsorizada": round(media_wins, 2),
            }
        else:
            resultado["IC_SPDMTR(km/h)"] = {"Descrição": "Velocidade do veículo em km/h", "Mensagem": "Sem dados"}
    else:
        resultado["IC_SPDMTR(km/h)"] = {"Descrição": "Velocidade do veículo em km/h", "Mensagem": "Coluna ausente"}

    # ============ RPM(1/min) ============
    if "RPM(1/min)" in df.columns:
        col = df["RPM(1/min)"].dropna()
        if not col.empty:
            winsor = col.clip(lower=col.quantile(0.05), upper=col.quantile(0.95))
            media_wins = winsor.mean()
            resultado["RPM(1/min)"] = {
                "Descrição": "Rotação do motor em rotações por minuto",
                "Mínimo": round(col.min(), 2),
                "Mediana": round(col.median(), 2),
                "Máximo": round(col.max(), 2),
                "Média Winsorizada": round(media_wins, 2),
            }
        else:
            resultado["RPM(1/min)"] = {"Descrição": "Rotação do motor em rotações por minuto", "Mensagem": "Sem dados"}
    else:
        resultado["RPM(1/min)"] = {"Descrição": "Rotação do motor em rotações por minuto", "Mensagem": "Coluna ausente"}

    # ============ ODOMETER(km) ============
    if "ODOMETER(km)" in df.columns:
        col = df["ODOMETER(km)"].dropna()
        if not col.empty:
            inicio = col.min()
            fim = col.max()
            distancia = fim - inicio
            resultado["ODOMETER(km)"] = {
                "Descrição": "Odômetro do veículo em km",
                "Início": round(inicio, 2),
                "Fim": round(fim, 2),
                "Distância Percorrida": round(distancia, 2),
            }
        else:
            resultado["ODOMETER(km)"] = {"Descrição": "Odômetro do veículo em km", "Mensagem": "Sem dados"}
    else:
        resultado["ODOMETER(km)"] = {"Descrição": "Odômetro do veículo em km", "Mensagem": "Coluna ausente"}

    # ============ TRIP_ODOM(km) ============
    if "TRIP_ODOM(km)" in df.columns:
        col = df["TRIP_ODOM(km)"].dropna()
        if not col.empty:
            inicio = col.min()
            fim = col.max()
            distancia = fim - inicio
            resultado["TRIP_ODOM(km)"] = {
                "Descrição": "Odômetro parcial da viagem em km",
                "Início": round(inicio, 2),
                "Fim": round(fim, 2),
                "Distância Percorrida": round(distancia, 2),
            }
        else:
            resultado["TRIP_ODOM(km)"] = {"Descrição": "Odômetro parcial da viagem em km", "Mensagem": "Sem dados"}
    else:
        resultado["TRIP_ODOM(km)"] = {"Descrição": "Odômetro parcial da viagem em km", "Mensagem": "Coluna ausente"}

    return resultado

import numpy as np
from scipy.ndimage import uniform_filter1d  # para suavização

def percentual_valores(col: pd.Series, valores_esperados: list[str]) -> dict:
    """
    Calcula percentual de ocorrência de cada valor esperado na série,
    além de detectar valores inesperados.
    Retorna dicionário com porcentagens.
    """
    total = len(col)
    result = {}
    for val in valores_esperados:
        count = (col == val).sum()
        result[val] = round(100 * count / total, 2) if total > 0 else 0.0

    # Verificar se há valores inesperados
    valores_unicos = set(col.unique())
    inesperados = valores_unicos - set(valores_esperados)
    if inesperados:
        result["Valores inesperados"] = list(inesperados)

    return result

def analisar_booleano(df: pd.DataFrame, coluna: str, valores_esperados: list[str], descricao: str) -> dict:
    if coluna not in df.columns:
        return {"Descrição": descricao, "Mensagem": "Coluna ausente"}

    col = df[coluna].dropna().astype(str).str.upper()
    if col.empty:
        return {"Descrição": descricao, "Mensagem": "Sem dados"}

    percentuais = percentual_valores(col, [v.upper() for v in valores_esperados])
    return {
        "Descrição": descricao,
        "Percentual por valor": percentuais
    }

def analisar_fuellvl(df: pd.DataFrame, descricao: str, capacidade_tanque_litros: float = 55.0) -> dict:
    """
    Calcula o volume de combustível consumido com base em FUELLVL(%).
    Usa média winsorizada para suavizar outliers, e suavização para estabilizar a curva.
    Estima volume inicial e final em litros, e calcula consumo estimado.
    """
    coluna = "FUELLVL(%)"
    if coluna not in df.columns:
        return {"Descrição": descricao, "Mensagem": "Coluna ausente"}

    col = df[coluna].dropna()
    if col.empty:
        return {"Descrição": descricao, "Mensagem": "Sem dados"}

    # Winsorização 5%
    q05 = col.quantile(0.05)
    q95 = col.quantile(0.95)
    col_wins = col.clip(lower=q05, upper=q95)

    # Suavização com média móvel (janela 5)
    col_suav = uniform_filter1d(col_wins.values, size=5, mode='nearest')

    # Valores estimados inicial e final (percentual)
    inicial_pct = col_suav[:10].mean()  # primeiros 10 pontos suavizados
    final_pct = col_suav[-10:].mean()   # últimos 10 pontos suavizados

    # Calcula volumes em litros
    inicial_l = capacidade_tanque_litros * (inicial_pct / 100.0)
    final_l = capacidade_tanque_litros * (final_pct / 100.0)
    consumido_l = max(inicial_l - final_l, 0.0)

    return {
        "Descrição": descricao,
        "Valor inicial (%)": round(inicial_pct, 2),
        "Valor final (%)": round(final_pct, 2),
        "Volume inicial (L)": round(inicial_l, 2),
        "Volume final (L)": round(final_l, 2),
        "Consumo estimado (L)": round(consumido_l, 2),
        "Observação": "Média winsorizada e suavização aplicadas para melhor estimativa"
    }

# Exemplo de uso para booleanos:
# analisar_booleano(df, "ENGI_IDLE", ["SIM", "NÃO"], "Motor em marcha lenta (SIM/NÃO)")

# Próxima parte: Análise das colunas com valores numéricos e top3 valores mais frequentes

from scipy.stats import mstats

def estatisticas_winsorizadas(serie: pd.Series, limite=0.05) -> dict:
    """
    Calcula estatísticas com winsorização para reduzir impacto de outliers.
    Retorna min, mediana, max e média winsorizada.
    """
    dados = serie.dropna()
    if dados.empty:
        return {}

    min_val = float(dados.min())
    med_val = float(dados.median())
    max_val = float(dados.max())
    # winsorização 5% para cada cauda
    wins_med = float(mstats.winsorize(dados, limits=limite).mean())

    return {
        "min": round(min_val, 2),
        "mediana": round(med_val, 2),
        "max": round(max_val, 2),
        "media_winsorizada": round(wins_med, 2)
    }

def top3_frequentes(serie: pd.Series, arredondar_casas=2) -> list[dict]:
    """
    Retorna os 3 valores mais frequentes na série com a respectiva % de aparição.
    Para numéricos, arredonda valores.
    """
    dados = serie.dropna()
    if dados.empty:
        return []

    if pd.api.types.is_numeric_dtype(dados):
        dados = dados.round(arredondar_casas)

    contagem = dados.value_counts(normalize=True).head(3) * 100
    top3 = []
    for valor, perc in zip(contagem.index, contagem.values):
        top3.append({
            "valor": valor,
            "percentual": round(perc, 2)
        })
    return top3

def analisar_coluna_numerica(df: pd.DataFrame, coluna: str, descricao: str, arredondar=2, calcular_top3=True) -> dict:
    """
    Analisa coluna numérica: estatísticas winsorizadas + top 3 valores frequentes + descrição.
    """
    if coluna not in df.columns:
        return {"Descrição": descricao, "Mensagem": "Coluna ausente"}

    serie = df[coluna].dropna()
    if serie.empty:
        return {"Descrição": descricao, "Mensagem": "Sem dados"}

    estatisticas = estatisticas_winsorizadas(serie, limite=0.05)
    resultado = {
        "Descrição": descricao,
        **estatisticas
    }

    if calcular_top3:
        resultado["Top 3 valores mais frequentes"] = top3_frequentes(serie, arredondar)

    return resultado

# Exemplo de uso:
# analisar_coluna_numerica(df, "SHRTFT1(%)", "Correção curta de combustível (%)")

# Na próxima parte, juntamos tudo, e começamos a construir a função principal para analisar todas as colunas listadas com seus formatos e descrições específicas.

# =========================
# Parte 2: Análise das colunas restantes conforme especificado
# =========================

def analisar_ic_spdmtr(df):
    return analisar_coluna_numerica(
        df, "IC_SPDMTR(km/h)", 
        "Velocidade do veículo em km/h (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_rpm(df):
    return analisar_coluna_numerica(
        df, "RPM(1/min)",
        "Rotação do motor em rotações por minuto (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_engi_idle(df):
    return analisar_booleano(
        df, "ENGI_IDLE", ["SIM", "NÃO"], 
        "Motor em marcha lenta (SIM/NÃO) - percentual de ocorrência"
    )

def analisar_openloop(df):
    return analisar_booleano(
        df, "OPENLOOP", ["ON", "OFF"], 
        "Estado de circuito aberto (ON/OFF) - percentual de ocorrência"
    )

def analisar_eng_stab(df):
    return analisar_booleano(
        df, "ENG_STAB", ["SIM", "NÃO"], 
        "Estabilidade do motor (SIM/NÃO) - percentual de ocorrência"
    )

def analisar_fuelpw(df):
    return analisar_coluna_numerica(
        df, "FUELPW(ms)", 
        "Tempo de injeção de combustível em milissegundos (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_fuel_corr(df):
    return analisar_coluna_numerica(
        df, "FUEL_CORR(:1)", 
        "Correção de combustível (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_shrtft1(df):
    return analisar_coluna_numerica(
        df, "SHRTFT1(%)", 
        "Correção curta de combustível (%) (Min, Mediana, Máximo, Média Winsorizada e Top 3 Valores)",
        calcular_top3=True
    )

def analisar_longft1(df):
    return analisar_coluna_numerica(
        df, "LONGFT1(%)", 
        "Correção longa de combustível (%) (Min, Mediana, Máximo, Média Winsorizada e Top 3 Valores)",
        calcular_top3=True
    )

def analisar_af_ratio(df):
    return analisar_coluna_numerica(
        df, "AF_RATIO(:1)", 
        "Razão ar/combustível (Min, Mediana, Máximo, Média Winsorizada e Top 3 Valores)",
        calcular_top3=True
    )

def analisar_lmd_ego1(df):
    return analisar_coluna_numerica(
        df, "LMD_EGO1(:1)", 
        "Sonda lambda (Min, Mediana, Máximo, Média Winsorizada e Top 3 Valores)",
        calcular_top3=True
    )

def analisar_o2s11_v(df):
    return analisar_coluna_numerica(
        df, "O2S11_V(V)", 
        "Tensão do sensor de oxigênio (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_ect_gauge(df):
    return analisar_coluna_numerica(
        df, "ECT_GAUGE(Â°C)", 
        "Temperatura do líquido de arrefecimento - gauge (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_ect(df):
    return analisar_coluna_numerica(
        df, "ECT(Â°C)", 
        "Temperatura do líquido de arrefecimento (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_iat(df):
    return analisar_coluna_numerica(
        df, "IAT(Â°C)", 
        "Temperatura do ar de admissão (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_map_v(df):
    return analisar_coluna_numerica(
        df, "MAP(V)", 
        "Pressão do coletor MAP em volts (Min, Mediana, Máximo, Média Winsorizada e Top 3 Valores)",
        calcular_top3=True
    )

def analisar_map_obdii(df):
    return analisar_coluna_numerica(
        df, "MAP.OBDII(kPa)", 
        "Pressão do coletor MAP em kPa (Min, Mediana, Máximo, Média Winsorizada e Top 3 Valores)",
        calcular_top3=True
    )

def analisar_mixcnt_stat(df):
    return analisar_booleano(
        df, "MIXCNT_STAT", ["ABERTO", "FECHADO"], 
        "Estado do misturador (ABERTO/FECHADO) - percentual de ocorrência"
    )

def analisar_lambda_1(df):
    if "LAMBDA_1" not in df.columns:
        return {"Descrição": "Mistura lambda (Lean Mix/Rich Mix/ETC)", "Mensagem": "Coluna ausente"}
    col = df["LAMBDA_1"].dropna().astype(str).str.upper()
    if col.empty:
        return {"Descrição": "Mistura lambda (Lean Mix/Rich Mix/ETC)", "Mensagem": "Sem dados"}
    valores_esperados = ["LEAN MIX", "RICH MIX", "ETC"]
    percentuais = percentual_valores(col, valores_esperados)
    return {
        "Descrição": "Mistura lambda (Lean Mix/Rich Mix/ETC) - percentual de ocorrência",
        "Percentual por valor": percentuais
    }

# =========================
# Parte 3: Análise das colunas SPKDUR, VBAT, BRK_LVL, PSP, FANLO, FANHI
# =========================

def analisar_spkdur(df, coluna):
    return analisar_coluna_numerica(
        df, coluna,
        f"Duração do pulso da bobina {coluna} (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_vbat_1(df):
    return analisar_coluna_numerica(
        df, "VBAT_1(V)",
        "Tensão da bateria do veículo (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_brk_lvl(df):
    coluna = "BRK_LVL"
    descricao = "Nível de freio (Alto/Médio/Baixo) - validação se está OK"

    if coluna not in df.columns:
        return {"Descrição": descricao, "Mensagem": "Coluna ausente"}

    col = df[coluna].dropna().astype(str).str.upper()
    if col.empty:
        return {"Descrição": descricao, "Mensagem": "Sem dados"}

    # Percentual dos valores esperados
    valores_esperados = ["ALTO", "MÉDIO", "MEDIO", "BAIXO"]
    percentuais = percentual_valores(col, valores_esperados)

    # Validação simples: se algum valor inesperado, alerta
    status = "OK"
    inesperados = [v for v in col.unique() if v not in valores_esperados]
    if inesperados:
        status = f"Alerta: Valores inesperados {inesperados}"

    return {
        "Descrição": descricao,
        "Percentual por valor": percentuais,
        "Status": status
    }

def analisar_psp(df):
    coluna = "PSP"
    descricao = "Pressão do combustível (High/Medium/Low) - validação se está OK"

    if coluna not in df.columns:
        return {"Descrição": descricao, "Mensagem": "Coluna ausente"}

    col = df[coluna].dropna().astype(str).str.upper()
    if col.empty:
        return {"Descrição": descricao, "Mensagem": "Sem dados"}

    valores_esperados = ["HIGH", "MEDIUM", "LOW"]
    percentuais = percentual_valores(col, valores_esperados)

    status = "OK"
    inesperados = [v for v in col.unique() if v not in valores_esperados]
    if inesperados:
        status = f"Alerta: Valores inesperados {inesperados}"

    return {
        "Descrição": descricao,
        "Percentual por valor": percentuais,
        "Status": status
    }

def analisar_fanlo(df):
    return analisar_coluna_numerica(
        df, "FANLO",
        "Velocidade do ventilador baixo (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

def analisar_fanhi(df):
    return analisar_coluna_numerica(
        df, "FANHI",
        "Velocidade do ventilador alto (Min, Mediana, Máximo e Média Winsorizada)",
        calcular_top3=False
    )

# Função auxiliar para todas SPKDUR de 1 a 4
def analisar_spkdur_todas(df):
    resultado = {}
    for i in range(1, 5):
        coluna = f"SPKDUR_{i}(ms)"
        resultado[coluna] = analisar_spkdur(df, coluna)
    return resultado

def analisar_todas_colunas(df):
    resultado = {}

    # time(ms)
    if "time(ms)" in df.columns:
        tempo_segundos = df["time(ms)"].max() / 1000 if not df["time(ms)"].empty else 0
        h = int(tempo_segundos // 3600)
        m = int((tempo_segundos % 3600) // 60)
        s = int(tempo_segundos % 60)
        resultado["time(ms)"] = {
            "Descrição": "Tempo total da viagem (HH:MM:SS)",
            "Valor": f"{h:02d}:{m:02d}:{s:02d}"
        }
    else:
        resultado["time(ms)"] = {"Descrição": "Tempo total da viagem (HH:MM:SS)", "Mensagem": "Coluna ausente"}

    # IC_SPDMTR(km/h)
    resultado["IC_SPDMTR(km/h)"] = analisar_coluna_numerica(
        df, "IC_SPDMTR(km/h)", "Velocidade do veículo em km/h (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # RPM(1/min)
    resultado["RPM(1/min)"] = analisar_coluna_numerica(
        df, "RPM(1/min)", "Rotação do motor em rpm (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # ODOMETER(km)
    if "ODOMETER(km)" in df.columns:
        col = df["ODOMETER(km)"].dropna()
        if not col.empty:
            inicio = round(col.min(), 2)
            fim = round(col.max(), 2)
            distancia = round(fim - inicio, 2)
            resultado["ODOMETER(km)"] = {
                "Descrição": "Odômetro do veículo em km",
                "Início": inicio,
                "Fim": fim,
                "Distância Percorrida": distancia
            }
        else:
            resultado["ODOMETER(km)"] = {"Descrição": "Odômetro do veículo em km", "Mensagem": "Sem dados"}
    else:
        resultado["ODOMETER(km)"] = {"Descrição": "Odômetro do veículo em km", "Mensagem": "Coluna ausente"}

    # TRIP_ODOM(km)
    if "TRIP_ODOM(km)" in df.columns:
        col = df["TRIP_ODOM(km)"].dropna()
        if not col.empty:
            inicio = round(col.min(), 2)
            fim = round(col.max(), 2)
            distancia = round(fim - inicio, 2)
            resultado["TRIP_ODOM(km)"] = {
                "Descrição": "Odômetro parcial da viagem em km",
                "Início": inicio,
                "Fim": fim,
                "Distância Percorrida": distancia
            }
        else:
            resultado["TRIP_ODOM(km)"] = {"Descrição": "Odômetro parcial da viagem em km", "Mensagem": "Sem dados"}
    else:
        resultado["TRIP_ODOM(km)"] = {"Descrição": "Odômetro parcial da viagem em km", "Mensagem": "Coluna ausente"}

    # ENGI_IDLE
    resultado["ENGI_IDLE"] = analisar_booleano(
        df, "ENGI_IDLE", ["SIM", "NÃO"], "Motor em marcha lenta (SIM/NÃO)"
    )

    # OPENLOOP
    resultado["OPENLOOP"] = analisar_booleano(
        df, "OPENLOOP", ["ON", "OFF"], "Modo Open Loop (ON/OFF)"
    )

    # ENG_STAB
    resultado["ENG_STAB"] = analisar_booleano(
        df, "ENG_STAB", ["SIM", "NÃO"], "Estabilidade do motor (SIM/NÃO)"
    )

    # FUELLVL(%)
    resultado["FUELLVL(%)"] = analisar_fuellvl(
        df, "Nível de combustível (%) e consumo estimado, tanque 55L"
    )

    # FUELPW(ms)
    resultado["FUELPW(ms)"] = analisar_coluna_numerica(
        df, "FUELPW(ms)", "Tempo de pulso de combustível em ms (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # FUEL_CORR(:1)
    resultado["FUEL_CORR(:1)"] = analisar_coluna_numerica(
        df, "FUEL_CORR(:1)", "Correção de combustível (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # SHRTFT1(%)
    resultado["SHRTFT1(%)"] = analisar_coluna_numerica(
        df, "SHRTFT1(%)", "Correção curta de combustível (%) (Min, Mediana, Máximo, Média Winsorizada e Top 3 frequentes)"
    )

    # LONGFT1(%)
    resultado["LONGFT1(%)"] = analisar_coluna_numerica(
        df, "LONGFT1(%)", "Correção longa de combustível (%) (Min, Mediana, Máximo, Média Winsorizada e Top 3 frequentes)"
    )

    # AF_RATIO(:1)
    resultado["AF_RATIO(:1)"] = analisar_coluna_numerica(
        df, "AF_RATIO(:1)", "Razão ar/combustível (Min, Mediana, Máximo, Média Winsorizada e Top 3 frequentes)"
    )

    # LMD_EGO1(:1)
    resultado["LMD_EGO1(:1)"] = analisar_coluna_numerica(
        df, "LMD_EGO1(:1)", "Sensor Lambda (Min, Mediana, Máximo, Média Winsorizada e Top 3 frequentes)"
    )

    # O2S11_V(V)
    resultado["O2S11_V(V)"] = analisar_coluna_numerica(
        df, "O2S11_V(V)", "Tensão do sensor de oxigênio (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # ECT_GAUGE(Â°C)
    resultado["ECT_GAUGE(Â°C)"] = analisar_coluna_numerica(
        df, "ECT_GAUGE(Â°C)", "Temperatura do líquido de arrefecimento (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # ECT(Â°C)
    resultado["ECT(Â°C)"] = analisar_coluna_numerica(
        df, "ECT(Â°C)", "Temperatura do motor (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # IAT(Â°C)
    resultado["IAT(Â°C)"] = analisar_coluna_numerica(
        df, "IAT(Â°C)", "Temperatura do ar de admissão (Min, Mediana, Máximo e Média Winsorizada)"
    )

    # MAP(V)
    resultado["MAP(V)"] = analisar_coluna_numerica(
        df, "MAP(V)", "Pressão absoluta do coletor (Min, Mediana, Máximo, Média Winsorizada e Top 3 frequentes)"
    )

    # MAP.OBDII(kPa)
    resultado["MAP.OBDII(kPa)"] = analisar_coluna_numerica(
        df, "MAP.OBDII(kPa)", "Pressão do coletor OBDII (Min, Mediana, Máximo, Média Winsorizada e Top 3 frequentes)"
    )

    # MIXCNT_STAT
    resultado["MIXCNT_STAT"] = analisar_booleano(
        df, "MIXCNT_STAT", ["ABERTO", "FECHADO"], "Status do sistema de mistura (ABERTO/FECHADO)"
    )

    # LAMBDA_1
    resultado["LAMBDA_1"] = analisar_booleano(
        df, "LAMBDA_1", ["LEAN MIX", "RICH MIX", "ETC"], "Status Lambda (Lean Mix/Rich Mix/ETC)"
    )

    # SPKDUR_1(ms) até SPKDUR_4(ms)
    resultado.update(analisar_spkdur_todas(df))

    # VBAT_1(V)
    resultado["VBAT_1(V)"] = analisar_vbat_1(df)

    # BRK_LVL
    resultado["BRK_LVL"] = analisar_brk_lvl(df)

    # PSP
    resultado["PSP"] = analisar_psp(df)

    # FANLO
    resultado["FANLO"] = analisar_fanlo(df)

    # FANHI
    resultado["FANHI"] = analisar_fanhi(df)

    return resultado

def exibir_analise_streamlit(resultado: dict):
    st.title("📊 Análise Completa dos Dados OBD")

    for coluna, dados in resultado.items():
        st.header(f"🔹 {coluna}")
        descricao = dados.get("Descrição", "Sem descrição")
        st.markdown(f"**Descrição:** {descricao}")

        if "Mensagem" in dados:
            st.warning(dados["Mensagem"])
            continue

        # Tratando o caso especial do time(ms) que tem valor formatado
        if coluna == "time(ms)":
            valor = dados.get("Valor", "-")
            st.markdown(f"**Tempo total da viagem:** `{valor}`")
            st.markdown("---")
            continue

        # Se a análise tem percentuais (booleanos)
        if "Percentual por valor" in dados:
            st.markdown("**Percentual por valor:**")
            percentuais = dados["Percentual por valor"]
            for val, perc in percentuais.items():
                if val != "Valores inesperados":
                    st.write(f"- {val}: {perc}%")
            if "Valores inesperados" in percentuais:
                st.error(f"⚠️ Valores inesperados: {percentuais['Valores inesperados']}")
            st.markdown("---")
            continue

        # Se a análise tem valores estatísticos
        estatisticas_chaves = ["min", "mediana", "max", "media_winsorizada"]
        if any(chave in dados for chave in estatisticas_chaves):
            st.markdown("**Estatísticas:**")
            for chave in estatisticas_chaves:
                if chave in dados:
                    nome_exibicao = {
                        "min": "Mínimo",
                        "mediana": "Mediana",
                        "max": "Máximo",
                        "media_winsorizada": "Média Winsorizada"
                    }[chave]
                    st.write(f"- {nome_exibicao}: {dados[chave]}")
            # Top 3 valores frequentes
            if "Top 3 valores mais frequentes" in dados:
                st.markdown("**Top 3 valores mais frequentes:**")
                for item in dados["Top 3 valores mais frequentes"]:
                    st.write(f"- {item['valor']} → {item['percentual']}%")
            st.markdown("---")
            continue

        # Caso especial: colunas com Início, Fim e Distância (como ODOMETER, TRIP_ODOM)
        chaves_distancia = ["Início", "Fim", "Distância Percorrida"]
        if any(chave in dados for chave in chaves_distancia):
            for chave in chaves_distancia:
                if chave in dados:
                    st.write(f"- {chave}: {dados[chave]}")
            st.markdown("---")
            continue

        # Caso especial: análise de combustível
        if "Volume inicial (L)" in dados:
            st.write(f"- Valor inicial (%): {dados.get('Valor inicial (%)', '-')}")
            st.write(f"- Valor final (%): {dados.get('Valor final (%)', '-')}")
            st.write(f"- Volume inicial (L): {dados.get('Volume inicial (L)', '-')}")
            st.write(f"- Volume final (L): {dados.get('Volume final (L)', '-')}")
            st.write(f"- Consumo estimado (L): {dados.get('Consumo estimado (L)', '-')}")
            st.caption(dados.get("Observação", ""))
            st.markdown("---")
            continue

        # Caso especial: status com cor (BRK_LVL, PSP)
        if "Status" in dados and "Valor Médio" in dados:
            st.write(f"- Valor Médio: {dados['Valor Médio']}")
            st.write(f"- Status: {dados['Status']}")
            st.markdown("---")
            continue


def analisar(df, modelo=None, combustivel=None, valores_ideais=None):
    return analisar_todas_colunas(df)

def exibir(resultado):
    exibir_analise_streamlit(resultado)

        # Se não entrou em nenhum caso acima, mostrar todos os pares chave:valor do dict
        for k, v in dados.items():
            if k != "Descrição":
                st.write(f"- {k}: {v}")
        st.markdown("---")
