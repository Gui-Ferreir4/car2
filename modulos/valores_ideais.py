import json

def carregar_valores_ideais(caminho_arquivo="valores_ideais.json"):
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Erro ao carregar o arquivo de valores ideais: {e}")

def obter_valores_para_modelo(modelo: str, combustivel: str, valores_ideais: dict):
    modelo = modelo.lower().strip()
    combustivel = combustivel.lower().strip()

    if modelo not in valores_ideais:
        raise ValueError(f"Modelo '{modelo}' não encontrado na base de valores ideais.")
    
    dados_modelo = valores_ideais[modelo]

    if combustivel not in dados_modelo:
        raise ValueError(f"Combustível '{combustivel}' não disponível para o modelo '{modelo}'.")

    return dados_modelo[combustivel]
