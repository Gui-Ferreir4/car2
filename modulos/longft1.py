import numpy as np
import streamlit as st

def analisar(df, modelo, combustivel, valores_ideais):
    col = 'LONGFT1(%)'

    if col not in df.columns:
        return {
            "status": "erro",
            "titulo": "LONGFT1(%)",
            "mensagem": f"Coluna '{col}' não encontrada no CSV.",
            "valores": {}
        }

    serie = df[col].dropna()
    if serie.empty:
        return {
            "status": "erro",
            "titulo": "LONGFT1(%)",
            "mensagem": f"Sem dados válidos para '{col}'.",
            "valores": {}
        }

    media = np.mean(serie)
    minimo = np.min(serie)
    maximo = np.max(serie)

    faixa_ideal = {"min": -100, "max": 100}
    try:
        faixa_ideal = valores_ideais[modelo][combustivel].get("LONGFT1pct", faixa_ideal)
    except KeyError:
        pass

    status = "OK" if faixa_ideal["min"] <= media <= faixa_ideal["max"] else "Alerta"
    mensagem = "Ajuste de combustível em longo prazo dentro dos padrões." if status == "OK" \
        else "Ajuste de combustível em longo prazo fora da faixa ideal. Pode indicar problema persistente."

    return {
        "status": status,
        "titulo": "LONGFT1(%)",
        "mensagem": mensagem,
        "valores": {
            "média": round(media, 2),
            "mínimo": round(minimo, 2),
            "máximo": round(maximo, 2),
            "faixa_ideal": faixa_ideal
        }
    }

def exibir(resultado):
    st.markdown(f"### 🔍 {resultado['titulo']}")

    if resultado["status"] == "erro":
        st.error(resultado["mensagem"])
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Média", f"{resultado['valores']['média']}%")
    col2.metric("Mínimo", f"{resultado['valores']['mínimo']}%")
    col3.metric("Máximo", f"{resultado['valores']['máximo']}%")

    if resultado["status"] == "OK":
        st.success(resultado["mensagem"])
    else:
        st.warning(f"⚠️ {resultado['mensagem']}")
