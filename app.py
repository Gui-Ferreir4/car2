import streamlit as st
import pandas as pd
import json
from modulos import (
    resumo_geral,
    fuellvl,
    shrtft1,
    longft1,
    ect_gauge,
    fuelpw, af_ego_o2#, map_sensor, spkdur, loop_fuelcorr
)


# --- Configuração inicial ---
st.set_page_config(page_title="Analisador de Dados OBD", layout="wide")
st.title("📊 Analisador de Dados OBD")

# --- Upload do CSV ---
st.header("1. Upload do Arquivo CSV")
uploaded_file = st.file_uploader("Selecione o arquivo .csv exportado da ECU", type="csv")

# --- Carregar os valores ideais ---
try:
    with open("valores_ideais.json", "r", encoding="utf-8") as f:
        valores_ideais = json.load(f)
    modelos_disponiveis = list(valores_ideais.keys())
except Exception as e:
    st.error(f"Erro ao carregar valores ideais: {e}")
    st.stop()

# --- Seleção do veículo e combustível ---
st.header("2. Parâmetros do Veículo")
modelo = st.selectbox("Modelo do veículo", modelos_disponiveis)
combustivel = st.selectbox("Combustível utilizado", ["gasolina", "etanol", "flex"])

if not uploaded_file:
    st.info("Faça upload de um arquivo CSV para iniciar a análise.")
    st.stop()

# --- Leitura e pré-visualização do CSV ---
try:
    df = pd.read_csv(uploaded_file, sep=None, engine="python")  # autodetecta separador
    st.success("Arquivo CSV carregado com sucesso!")
    st.write("Prévia dos dados:", df.head())
except Exception as e:
    st.error(f"Erro ao ler o CSV: {e}")
    st.stop()

# --- Executar análises ---
st.header("3. Análises de Sensores")
modulos_analise = [
    resumo_geral,
    fuellvl,
    shrtft1,
    longft1,
    ect_gauge,
    fuelpw,
    af_ego_o2,
    map_sensor,
    spkdur,
    lambda_mixture
]  # Lista de módulos ativos

for modulo in modulos_analise:
    with st.expander(f"🔎 {modulo.__name__.split('.')[-1].upper()}"):
        resultado = modulo.analisar(df, modelo, combustivel, valores_ideais)
        modulo.exibir(resultado)

st.success("✅ Análise concluída.")









