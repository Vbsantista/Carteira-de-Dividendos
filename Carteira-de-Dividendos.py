import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Painel Barsi", page_icon="📈", layout="wide")

CARTEIRA = {
    "BBAS3": "Banco", "BBSE3": "Seguros", "BRAP4": "Holding/Mineração",
    "CSMG3": "Saneamento", "CXSE3": "Seguros", "CYRE4": "Construção",
    "ISAE4": "Energia", "PETR4": "Petróleo",
}
PERENES = {"Banco", "Energia", "Saneamento", "Seguros", "Telecom"}

st.sidebar.header("Parâmetros")
DY_MIN = st.sidebar.slider("DY mínimo (%)", 3.0, 12.0, 6.0, 0.5) / 100
ANOS = st.sidebar.slider("Anos seguidos pagando dividendos", 3, 10, 5)
ROE_MIN = st.sidebar.slider("ROE mínimo (%)", 5, 25, 10) / 100
DIV_MAX = st.sidebar.slider("Dívida/PL máxima (%)", 20, 150, 70)
extras = st.sidebar.text_input("Adicionar tickers (ex: ITSA4:Banco, TAEE11:Energia)")
for item in [x.strip() for x in extras.split(",") if ":" in x]:
    t, s = item.split(":")
    CARTEIRA[t.strip().upper()] = s.strip()

@st.cache_data(ttl=900)
def buscar(ticker):
    acao = yf.Ticker(f"{ticker}.SA")
    hist = acao.history(period="5d")
    preco = float(hist["Close"].iloc[-1]) if not hist.empty else None
    divs = acao.dividends
    try:
        info = acao.info or {}
    except Exception:
        info = {}
    return preco, divs, info.get("returnOnEquity"), info.get("debtToEquity"), info.get("trailingPE")

def analisar(ticker, setor):
    preco, divs, roe, divida, pl = buscar(ticker)
    ano = datetime.now().year
    if not divs.empty:
        por_ano = divs.groupby(divs.index.year).sum()
        corte = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1)
        ult12 = divs[divs.index > corte].sum()
    else:
        por_ano, ult12 = pd.Series(dtype=float), 0
    pagou = all(por_ano.get(a, 0) > 0 for a in range(ano - ANOS, ano))
    media3 = por_ano.reindex(range(ano - 3, ano)).fillna(0).mean() if not por_ano.empty else 0
    teto = media3 / DY_MIN
    dy = ult12 / preco if preco else None

    # True = passou, False = reprovou, None = sem dado (não conta)
    crit = {
        "Setor perene": setor in PERENES,
        f"Div. {ANOS} anos": pagou,
        "DY ok": None if dy is None else dy >= DY_MIN,
        "Lucro +": None if pl is None else pl > 0,
        "ROE ok": None if roe is None else roe >= ROE_MIN,
        "Dívida ok": None if divida is None else divida < DIV_MAX,
        "Abaixo do teto": None if not preco or teto == 0 else preco < teto,
    }
    avaliados = [v for v in crit.values() if v is not None]
    n, total = sum(avaliados), len(avaliados)
    status = "✅ DENTRO" if n == total else "⚠️ QUASE" if n == total - 1 else "❌ FORA"

    linha = {"Ticker": ticker, "Setor": setor, "Preço": preco, "Teto Bazin": teto,
             "Margem até o teto (%)": (teto / preco - 1) * 100 if preco and teto else None,
             "DY 12m (%)": dy * 100 if dy is not None else None,
             "ROE (%)": roe * 100 if roe is not None else None, "P/L": pl}
    linha.update({k: "➖" if v is None else ("✅" if v else "❌") for k, v in crit.items()})
    linha["Nota"] = f"{n}/{total}"
    linha["Status"] = status
    return linha

st.title("📈 Painel Barsi da minha carteira")
col1, col2 = st.columns([3, 1])
col1.caption(f"Atualizado em {datetime.now():%d/%m/%Y %H:%M} · Yahoo Finance (atraso ~15 min) · ➖ = sem dado")
if col2.button("🔄 Atualizar agora"):
    st.cache_data.clear()

linhas = []
with st.spinner("Buscando dados..."):
    for t, s in CARTEIRA.items():
        try:
            linhas.append(analisar(t, s))
        except Exception as e:
            st.warning(f"{t}: não consegui buscar os dados ({e})")

df = pd.DataFrame(linhas)
if not df.empty:
    dentro = (df["Status"] == "✅ DENTRO").sum()
    quase = (df["Status"] == "⚠️ QUASE").sum()
    a, b, c = st.columns(3)
    a.metric("Dentro para compra", dentro)
    b.metric("Quase", quase)
    c.metric("Fora", len(df) - dentro - quase)

    def cor(v):
        return {"✅ DENTRO": "background-color:#2e7d32;color:white",
                "⚠️ QUASE": "background-color:#f9a825;color:black",
                "❌ FORA": "background-color:#c62828;color:white"}.get(v, "")

    st.dataframe(
        df.style.map(cor, subset=["Status"]).format({
            "Preço": "R$ {:.2f}", "Teto Bazin": "R$ {:.2f}", "Margem até o teto (%)": "{:+.1f}",
            "DY 12m (%)": "{:.1f}", "ROE (%)": "{:.1f}", "P/L": "{:.1f}"}, na_rep="—"),
        use_container_width=True, hide_index=True)

st.info("Lembrete: qualidade da gestão e respeito ao minoritário não dá para automatizar. "
        "Isto é uma ferramenta de apoio, não uma recomendação de compra.")
