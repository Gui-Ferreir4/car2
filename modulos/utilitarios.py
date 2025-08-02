import pandas as pd
import numpy as np

def sanitizar_coluna(df: pd.DataFrame, coluna: str) -> pd.Series:
    """
    Limpa e converte uma coluna para valores numéricos:
    - Remove espaços, %, vírgulas
    - Converte para float
    - Substitui valores inválidos por NaN
    - Retorna série sem NaN
    """
    if coluna not in df.columns:
        return pd.Series([], dtype=float)

    serie = df[coluna].astype(str)

    # Remove espaços e símbolos comuns
    serie = (
        serie
        .str.strip()
        .str.replace(',', '.', regex=False)    # vírgula -> ponto
        .str.replace('%', '', regex=False)     # remove porcentagem
    )

    # Substitui strings conhecidas inválidas por NaN
    serie = serie.replace(['', '-', 'nan', 'None', 'NaT'], pd.NA)

    # Converte para numérico e remove NaN
    serie = pd.to_numeric(serie, errors='coerce').dropna()

    return serie

def calcular_estatisticas(serie: pd.Series) -> dict:
    """
    Retorna um dicionário com estatísticas básicas de uma série numérica.
    """
    if serie.empty:
        return {
            "média": None,
            "mínimo": None,
            "máximo": None,
            "mediana": None,
            "desvio_padrao": None,
            "q1": None,
            "q3": None
        }

    return {
        "média": round(serie.mean(), 2),
        "mínimo": round(serie.min(), 2),
        "máximo": round(serie.max(), 2),
        "mediana": round(serie.median(), 2),
        "desvio_padrao": round(serie.std(), 2),
        "q1": round(serie.quantile(0.25), 2),
        "q3": round(serie.quantile(0.75), 2)
    }

def avaliar_status(media: float, faixa_ideal: dict) -> str:
    """
    Avalia se a média está dentro da faixa ideal.
    Retorna 'OK' ou 'Alerta'.
    """
    if media is None:
        return "erro"

    minimo = faixa_ideal.get("min", -np.inf)
    maximo = faixa_ideal.get("max", np.inf)

    return "OK" if minimo <= media <= maximo else "Alerta"

def interpretar_status(coluna: str, status: str) -> str:
    """
    Retorna uma mensagem interpretativa padrão baseada no status.
    Pode ser customizada por módulo se necessário.
    """
    if status == "OK":
        return f"{coluna}: valores dentro do esperado."
    elif status == "Alerta":
        return f"{coluna}: valores fora da faixa ideal. Investigue possíveis causas."
    else:
        return f"{coluna}: dados insuficientes para análise."
