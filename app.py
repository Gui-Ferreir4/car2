import streamlit as st
import pandas as pd
import json
from io import StringIO
from modulos import shrtft1, longft1  # Importa os módulos prontos

# --- Configuração inicial ---
st.set_page_config(page_title="Analisador de Dados OBD", layout="wide")

st.title("📊 Analisador de Dados OBD")

# --- Upload do CSV ---
st.header("1. Upload do Arquivo CSV")
uploaded_file = st.file_uploader("Selecione o arquivo .csv exportado da ECU", type="csv")

if uploaded_file:
    # Leitura do CSV
    df = pd.read_csv(uploaded_file, sep=None, engine="python")
    st.success("Arquivo CSV carregado com sucesso!")
    st.write("Prévia dos dados:", df.head())

    # --- Seleção do veículo e combustível ---
    st.header("2. Parâmetros do Veículo")
    modelo = st.text_input("Modelo do veículo (ex: Ford Fiesta 1.6 2014)", "")
    combustivel = st.selectbox("Combustível utilizado", ["gasolina", "etanol", "flex"])

    if modelo.strip() == "":
        st.warning("Por favor, informe o modelo do veículo.")
        st.stop()

    # --- Carregar os valores ideais ---
    try:
        with open("valores_ideais.json", "r", encoding="utf-8") as f:
            valores_ideais = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar valores ideais: {e}")
        st.stop()

    # --- Executar análises ---
    st.header("3. Análises")
    modulos_analise = [shrtft1, longft1]  # Lista de módulos ativos

    for modulo in modulos_analise:
        with st.expander(f"🔎 {modulo.__name__.split('.')[-1].upper()}"):
            resultado = modulo.analisar(df, modelo, combustivel, valores_ideais)
            modulo.exibir(resultado)

else:
    st.info("Faça upload de um arquivo CSV para iniciar a análise.")
