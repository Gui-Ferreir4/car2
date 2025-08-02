import pandas as pd
from datetime import timedelta

def converter_tempo(ms):
    try:
        segundos = int(ms) // 1000
        return str(timedelta(seconds=segundos))
    except:
        return "Inválido"

def carregar_e_processar_csv(arquivo_csv):
    # Leitura inicial (tentando encoding e separador mais comum)
    df = pd.read_csv(arquivo_csv, encoding='utf-8', sep=';', skip_blank_lines=True)

    # Padroniza nomes de colunas
    df.columns = df.columns.str.strip()

    # Remove caracteres inválidos se houver
    df.columns = df.columns.str.replace("\uFFFD", "", regex=True)

    # Verificações mínimas
    if "time(ms)" not in df.columns or "ENGI_IDLE" not in df.columns:
        raise Exception("Colunas obrigatórias não encontradas: 'time(ms)' ou 'ENGI_IDLE'.")

    # Coluna de tempo convertida (opcional, útil para visualizações)
    df["TIME_CONVERTED"] = df["time(ms)"].apply(converter_tempo)

    # Trata ENGI_IDLE (categorias inconsistentes)
    df["ENGI_IDLE"] = df["ENGI_IDLE"].replace({
        "Sim": 1, "Não": 0, "Nao": 0, "nao": 0, "não": 0
    }).fillna(0).astype(int)

    # Cria uma coluna "ativa" com base no funcionamento do motor
    df["ACTIVE"] = df["ENGI_IDLE"].apply(lambda x: 0 if x == 1 else 1)

    # Limpa e converte todas as colunas numéricas que têm "-" ou strings
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].replace("-", pd.NA)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove linhas completamente vazias (exceto tempo convertido)
    df.dropna(axis=0, how='all', subset=[col for col in df.columns if col != "TIME_CONVERTED"], inplace=True)

    return df
