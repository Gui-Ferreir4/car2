# =========================
# Imports e configuração
# =========================
import pandas as pd
import numpy as np
import streamlit as st
from scipy.stats import mstats
from scipy.ndimage import uniform_filter1d

st.set_page_config(page_title="Análise de Dados OBD", layout="wide")

# =========================
# Funções auxiliares de cálculo
# =========================

def winsorizada(serie: pd.Series, limite=0.05):
    """Aplica winsorização para reduzir impacto de outliers."""
    serie_clean = pd.to_numeric(serie, errors='coerce').dropna()
    if serie_clean.empty:
        return None
    return pd.Series(mstats.winsorize(serie_clean, limits=limite))

def estatisticas(serie: pd.Series) -> dict:
    """Calcula min, mediana, max e média winsorizada."""
    dados = pd.to_numeric(serie, errors='coerce').dropna()
    if dados.empty:
        return {
            "min": None,
            "mediana": None,
            "max": None,
            "media_winsorizada": None,
            "mensagem": "Sem dados válidos"
        }

    winsor = winsorizada(dados)
    return {
        "min": arredondar_seguro(dados.min()),
        "mediana": arredondar_seguro(dados.median()),
        "max": arredondar_seguro(dados.max()),
        "media_winsorizada": arredondar_seguro(winsor.mean()) if winsor is not None else None
    }

def top3_frequentes(serie: pd.Series) -> list:
    """Retorna os 3 valores mais frequentes com percentual."""
    dados = pd.to_numeric(serie, errors='coerce').dropna()
    if dados.empty:
        return []
    freq = dados.round(2).value_counts(normalize=True).head(3) * 100
    return [
        {"valor": k, "percentual": round(v, 2)} for k, v in freq.items()
    ]

def percentual_valores(serie: pd.Series, valores_esperados: list[str]) -> dict:
    """Calcula percentual de ocorrência de cada valor esperado."""
    serie = serie.dropna().astype(str).str.upper()
    total = len(serie)
    resultado = {}
    for v in valores_esperados:
        resultado[v] = round((serie == v).sum() / total * 100, 2) if total > 0 else 0.0
    inesperados = set(serie.unique()) - set([v.upper() for v in valores_esperados])
    if inesperados:
        resultado["Valores inesperados"] = list(inesperados)
    return resultado

def arredondar_seguro(valor, casas=2):
    """Arredonda sem quebrar quando valor é NaN."""
    try:
        if pd.notna(valor):
            return round(float(valor), casas)
        return None
    except:
        return None

def analisar_fuellvl(df: pd.DataFrame, capacidade_tanque=55.0):
    """Analisa nível de combustível com winsorização + suavização."""
    if "FUELLVL(%)" not in df.columns:
        return {"mensagem": "Coluna ausente"}

    # Converte para numérico
    col = pd.to_numeric(df["FUELLVL(%)"], errors='coerce').dropna()
    if col.empty:
        return {"mensagem": "Sem dados válidos"}

    # Evita erro se não houver dados suficientes
    if len(col) < 2:
        return {"mensagem": "Poucos dados para análise"}

    # Winsoriza e suaviza
    q_low = col.quantile(0.05)
    q_high = col.quantile(0.95)
    col_clip = col.clip(lower=q_low, upper=q_high)
    col_suav = uniform_filter1d(col_clip.values, size=5, mode="nearest")

    ini_pct = np.mean(col_suav[:10])
    fim_pct = np.mean(col_suav[-10:])
    ini_l = capacidade_tanque * (ini_pct / 100)
    fim_l = capacidade_tanque * (fim_pct / 100)
    consumo = max(ini_l - fim_l, 0)

    return {
        "Valor inicial (%)": arredondar_seguro(ini_pct),
        "Valor final (%)": arredondar_seguro(fim_pct),
        "Volume inicial (L)": arredondar_seguro(ini_l),
        "Volume final (L)": arredondar_seguro(fim_l),
        "Consumo estimado (L)": arredondar_seguro(consumo),
        "Observação": "Baseado em média winsorizada + suavização"
    }

# =========================
# Análise principal por coluna
# =========================
def analisar(df: pd.DataFrame, modelo=None, combustivel=None, valores_ideais=None) -> dict:
    resultado = {}

    # 1️⃣ Limpeza global: substitui "-" por NaN
    df = df.replace("-", np.nan)

    # ---- 1. Tempo da viagem
    if "time(ms)" in df.columns:
        tempo = pd.to_numeric(df["time(ms)"], errors='coerce').dropna()
        if not tempo.empty:
            total_segundos = tempo.max() / 1000
            h, m, s = int(total_segundos // 3600), int((total_segundos % 3600) // 60), int(total_segundos % 60)
            resultado["time(ms)"] = {"Tempo da viagem": f"{h:02}:{m:02}:{s:02}"}
        else:
            resultado["time(ms)"] = {"mensagem": "Sem dados válidos"}
    else:
        resultado["time(ms)"] = {"mensagem": "Coluna ausente"}

    # ---- 2. IC_SPDMTR(km/h)
    if "IC_SPDMTR(km/h)" in df.columns:
        resultado["IC_SPDMTR(km/h)"] = estatisticas(df["IC_SPDMTR(km/h)"])
    else:
        resultado["IC_SPDMTR(km/h)"] = {"mensagem": "Coluna ausente"}

    # ---- 3. RPM(1/min)
    if "RPM(1/min)" in df.columns:
        resultado["RPM(1/min)"] = estatisticas(df["RPM(1/min)"])
    else:
        resultado["RPM(1/min)"] = {"mensagem": "Coluna ausente"}

    # ---- 4. ODOMETER(km)
    if "ODOMETER(km)" in df.columns:
        col = pd.to_numeric(df["ODOMETER(km)"], errors='coerce').dropna()
        if not col.empty:
            ini = col.min()
            fim = col.max()
            resultado["ODOMETER(km)"] = {
                "Início (km)": arredondar_seguro(ini),
                "Fim (km)": arredondar_seguro(fim),
                "Distância (km)": arredondar_seguro(fim - ini) if pd.notna(fim) and pd.notna(ini) else None
            }
        else:
            resultado["ODOMETER(km)"] = {"mensagem": "Sem dados numéricos válidos"}
    else:
        resultado["ODOMETER(km)"] = {"mensagem": "Coluna ausente"}

    # ---- 5. TRIP_ODOM(km)
    if "TRIP_ODOM(km)" in df.columns:
        col = pd.to_numeric(df["TRIP_ODOM(km)"], errors='coerce').dropna()
        if not col.empty:
            ini = col.min()
            fim = col.max()
            resultado["TRIP_ODOM(km)"] = {
                "Início (km)": arredondar_seguro(ini),
                "Fim (km)": arredondar_seguro(fim),
                "Distância (km)": arredondar_seguro(fim - ini) if pd.notna(fim) and pd.notna(ini) else None
            }
        else:
            resultado["TRIP_ODOM(km)"] = {"mensagem": "Sem dados numéricos válidos"}
    else:
        resultado["TRIP_ODOM(km)"] = {"mensagem": "Coluna ausente"}

    # ---- 6. ENGI_IDLE
    if "ENGI_IDLE" in df.columns:
        resultado["ENGI_IDLE"] = percentual_valores(df["ENGI_IDLE"], ["SIM", "NÃO"])
    else:
        resultado["ENGI_IDLE"] = {"mensagem": "Coluna ausente"}

    # ---- 7. OPENLOOP
    if "OPENLOOP" in df.columns:
        resultado["OPENLOOP"] = percentual_valores(df["OPENLOOP"], ["ON", "OFF"])
    else:
        resultado["OPENLOOP"] = {"mensagem": "Coluna ausente"}

    # ---- 8. ENG_STAB
    if "ENG_STAB" in df.columns:
        resultado["ENG_STAB"] = percentual_valores(df["ENG_STAB"], ["SIM", "NÃO"])
    else:
        resultado["ENG_STAB"] = {"mensagem": "Coluna ausente"}

    # ---- 9. FUELLVL(%)
    resultado["FUELLVL(%)"] = analisar_fuellvl(df)

    # ---- 10. FUELPW(ms)
    if "FUELPW(ms)" in df.columns:
        resultado["FUELPW(ms)"] = estatisticas(df["FUELPW(ms)"])
    else:
        resultado["FUELPW(ms)"] = {"mensagem": "Coluna ausente"}

    # ---- 11. FUEL_CORR(:1)
    if "FUEL_CORR(:1)" in df.columns:
        serie = df["FUEL_CORR(:1)"]
        resultado["FUEL_CORR(:1)"] = {
            **estatisticas(serie),
            "Top 3 valores": top3_frequentes(serie)
        }
    else:
        resultado["FUEL_CORR(:1)"] = {"mensagem": "Coluna ausente"}

    # ---- 12. SHRTFT1(%)
    if "SHRTFT1(%)" in df.columns:
        serie = df["SHRTFT1(%)"]
        resultado["SHRTFT1(%)"] = {
            **estatisticas(serie),
            "Top 3 valores": top3_frequentes(serie)
        }
    else:
        resultado["SHRTFT1(%)"] = {"mensagem": "Coluna ausente"}

    # ---- 13. LONGFT1(%)
    if "LONGFT1(%)" in df.columns:
        serie = df["LONGFT1(%)"]
        resultado["LONGFT1(%)"] = {
            **estatisticas(serie),
            "Top 3 valores": top3_frequentes(serie)
        }
    else:
        resultado["LONGFT1(%)"] = {"mensagem": "Coluna ausente"}

    # ---- 14. AF_RATIO(:1)
    if "AF_RATIO(:1)" in df.columns:
        serie = df["AF_RATIO(:1)"]
        resultado["AF_RATIO(:1)"] = {
            **estatisticas(serie),
            "Top 3 valores": top3_frequentes(serie)
        }
    else:
        resultado["AF_RATIO(:1)"] = {"mensagem": "Coluna ausente"}

    # ---- 15. LMD_EGO1(:1)
    if "LMD_EGO1(:1)" in df.columns:
        serie = df["LMD_EGO1(:1)"]
        resultado["LMD_EGO1(:1)"] = {
            **estatisticas(serie),
            "Top 3 valores": top3_frequentes(serie)
        }
    else:
        resultado["LMD_EGO1(:1)"] = {"mensagem": "Coluna ausente"}

    # ---- 16. O2S11_V(V)
    if "O2S11_V(V)" in df.columns:
        resultado["O2S11_V(V)"] = estatisticas(df["O2S11_V(V)"])
    else:
        resultado["O2S11_V(V)"] = {"mensagem": "Coluna ausente"}

    # ---- 17. ECT_GAUGE(°C)
    if "ECT_GAUGE(°C)" in df.columns:
        resultado["ECT_GAUGE(°C)"] = estatisticas(df["ECT_GAUGE(°C)"])
    else:
        resultado["ECT_GAUGE(°C)"] = {"mensagem": "Coluna ausente"}

    # ---- 18. ECT(°C)
    if "ECT(°C)" in df.columns:
        resultado["ECT(°C)"] = estatisticas(df["ECT(°C)"])
    else:
        resultado["ECT(°C)"] = {"mensagem": "Coluna ausente"}

    # ---- 19. IAT(°C)
    if "IAT(°C)" in df.columns:
        resultado["IAT(°C)"] = estatisticas(df["IAT(°C)"])
    else:
        resultado["IAT(°C)"] = {"mensagem": "Coluna ausente"}

    # ---- 20. MAP(V)
    if "MAP(V)" in df.columns:
        serie = df["MAP(V)"]
        resultado["MAP(V)"] = {
            **estatisticas(serie),
            "Top 3 valores": top3_frequentes(serie)
        }
    else:
        resultado["MAP(V)"] = {"mensagem": "Coluna ausente"}

    # ---- 21. MAP.OBDII(kPa)
    if "MAP.OBDII(kPa)" in df.columns:
        serie = df["MAP.OBDII(kPa)"]
        resultado["MAP.OBDII(kPa)"] = {
            **estatisticas(serie),
            "Top 3 valores": top3_frequentes(serie)
        }
    else:
        resultado["MAP.OBDII(kPa)"] = {"mensagem": "Coluna ausente"}

    # ---- 22. MIXCNT_STAT
    if "MIXCNT_STAT" in df.columns:
        resultado["MIXCNT_STAT"] = percentual_valores(df["MIXCNT_STAT"], ["ABERTO", "FECHADO"])
    else:
        resultado["MIXCNT_STAT"] = {"mensagem": "Coluna ausente"}

    # ---- 23. LAMBDA_1
    if "LAMBDA_1" in df.columns:
        resultado["LAMBDA_1"] = percentual_valores(df["LAMBDA_1"], ["LEAN MIX", "RICH MIX", "ETC"])
    else:
        resultado["LAMBDA_1"] = {"mensagem": "Coluna ausente"}

    # ---- 24-27. SPKDUR_1 a SPKDUR_4
    for i in range(1, 5):
        nome = f"SPKDUR_{i}(ms)"
        if nome in df.columns:
            resultado[nome] = estatisticas(df[nome])
        else:
            resultado[nome] = {"mensagem": "Coluna ausente"}

    # ---- 28. VBAT_1(V)
    if "VBAT_1(V)" in df.columns:
        resultado["VBAT_1(V)"] = estatisticas(df["VBAT_1(V)"])
    else:
        resultado["VBAT_1(V)"] = {"mensagem": "Coluna ausente"}

    # ---- 29. BRK_LVL
    if "BRK_LVL" in df.columns:
        resultado["BRK_LVL"] = percentual_valores(df["BRK_LVL"], ["ALTO", "MÉDIO", "BAIXO"])
    else:
        resultado["BRK_LVL"] = {"mensagem": "Coluna ausente"}

    # ---- 30. PSP
    if "PSP" in df.columns:
        resultado["PSP"] = percentual_valores(df["PSP"], ["HIGH", "MEDIUM", "LOW"])
    else:
        resultado["PSP"] = {"mensagem": "Coluna ausente"}

    # ---- 31. FANLO
    if "FANLO" in df.columns:
        resultado["FANLO"] = estatisticas(df["FANLO"])
    else:
        resultado["FANLO"] = {"mensagem": "Coluna ausente"}

    # ---- 32. FANHI
    if "FANHI" in df.columns:
        resultado["FANHI"] = estatisticas(df["FANHI"])
    else:
        resultado["FANHI"] = {"mensagem": "Coluna ausente"}

    return resultado

# =========================
# Exibição no Streamlit
# =========================

def exibir(resultado: dict):
    st.subheader("Resumo Geral da Viagem (Diagnóstico OBD)")

    for chave, valores in resultado.items():
        st.markdown(f"### 🔹 {chave}")
        
        if not isinstance(valores, dict):
            st.write(valores)
            continue

        if "mensagem" in valores:
            st.info(valores["mensagem"])
            continue

        col1, col2 = st.columns(2)
        with col1:
            for k, v in list(valores.items())[:len(valores)//2 + 1]:
                st.markdown(f"**{k}:** {v}")
        with col2:
            for k, v in list(valores.items())[len(valores)//2 + 1:]:
                st.markdown(f"**{k}:** {v}")
