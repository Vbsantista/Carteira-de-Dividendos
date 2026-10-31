import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Painel Barsi", page_icon="📈", layout="wide")

CARTEIRA = {
    "BBAS3": "Banco", "BBSE3": "Seguros", "BRAP4": "Holding/Mineração",
    "CSMG3": "Saneamento", "CXSE3": "Seguros", 
    "ISAE4": "Energia", "PETR4": "Petróleo", "ITSA4", "Banco",
}
PERENES = {"Banco", "Energia", "Saneamento", "Seguros", "Telecom"}

st.sidebar.header("Parâmetros")
DY_MIN = st.sidebar.slider("DY mínimo (%)", 3.0, 12.0, 6.0, 0.5) / 100
ANOS = st.sidebar.slider("Anos seguidos pagando dividendos", 3, 10, 5)
ROE_MIN = st.sidebar.slider("ROE mínimo (%)", 5, 25, 10) / 100
DIV_MAX = st.sidebar.slider("Dívida/PL máxima (%)", 20, 150, 70)
NOTA_MIN = st.sidebar.slider("Nota mínima para compra", 5.0, 10.0, 7.0, 0.5)
extras = st.sidebar.text_input("Adicionar tickers (ex: ITSA4:Banco, TAEE11:Energia)")
for item in [x.strip() for x in extras.split(",") if ":" in x]:
    t, s = item.split(":")
    CARTEIRA[t.strip().upper()] = s.strip()

PESOS = {
    "Setor perene": 1.0, "Div. consistentes": 2.0, "DY ok": 2.0, "Lucro +": 1.0,
    "ROE ok": 1.5, "Dívida ok": 1.0, "Abaixo do teto": 1.5,
}

@st.cache_data(ttl=900)
def buscar(ticker):
    acao = yf.Ticker(f"{ticker}.SA")
    try:
        info = acao.info or {}
    except Exception:
        info = {}
    preco = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")
    if not preco:
        fech = acao.history(period="1mo")["Close"].dropna()
        preco = float(fech.iloc[-1]) if not fech.empty else None
    divs = acao.dividends
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
    teto = media3 / DY_MIN if media3 > 0 else None
    dy = ult12 / preco if preco else None

    # True = passou, False = reprovou, None = sem dado (sai da conta)
    crit = {
        "Setor perene": setor in PERENES,
        "Div. consistentes": pagou,
        "DY ok": None if dy is None else dy >= DY_MIN,
        "Lucro +": None if pl is None else pl > 0,
        "ROE ok": None if roe is None else roe >= ROE_MIN,
        "Dívida ok": None if divida is None else divida < DIV_MAX,
        "Abaixo do teto": None if not preco or not teto else preco < teto,
    }
    peso_avaliado = sum(PESOS[k] for k, v in crit.items() if v is not None)
    peso_ganho = sum(PESOS[k] for k, v in crit.items() if v)
    nota = round(peso_ganho / peso_avaliado * 10, 1) if peso_avaliado else 0.0

    if nota >= NOTA_MIN:
        status = "✅ DENTRO"
    elif nota >= NOTA_MIN - 1.5:
        status = "⚠️ QUASE"
    else:
        status = "❌ FORA"

    linha = {"Ticker": ticker, "Setor": setor, "Preço": preco, "Teto Bazin": teto,
             "Margem até o teto (%)": (teto / preco - 1) * 100 if preco and teto else None,
             "DY 12m (%)": dy * 100 if dy is not None else None,
             "ROE (%)": roe * 100 if roe is not None else None, "P/L": pl}
    linha.update({k: "➖" if v is None else ("✅" if v else "❌") for k, v in crit.items()})
    linha["Nota (0-10)"] = nota
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
    df = df.sort_values("Nota (0-10)", ascending=False)
    dentro = (df["Status"] == "✅ DENTRO").sum()
    quase = (df["Status"] == "⚠️ QUASE").sum()
    a, b, c, d = st.columns(4)
    a.metric("Dentro para compra", dentro)
    b.metric("Quase", quase)
    c.metric("Fora", len(df) - dentro - quase)
    d.metric("Nota média da carteira", f"{df['Nota (0-10)'].mean():.1f}")

    def cor(v):
        return {"✅ DENTRO": "background-color:#2e7d32;color:white",
                "⚠️ QUASE": "background-color:#f9a825;color:black",
                "❌ FORA": "background-color:#c62828;color:white"}.get(v, "")

    st.dataframe(
        df.style.map(cor, subset=["Status"]).format({
            "Preço": "R$ {:.2f}", "Teto Bazin": "R$ {:.2f}", "Margem até o teto (%)": "{:+.1f}",
            "DY 12m (%)": "{:.1f}", "ROE (%)": "{:.1f}", "P/L": "{:.1f}",
            "Nota (0-10)": "{:.1f}"}, na_rep="—"),
        use_container_width=True, hide_index=True)

    with st.expander("Como a nota é calculada"):
        st.write(pd.DataFrame({"Critério": PESOS.keys(), "Peso": PESOS.values()}))
        st.caption("Critérios sem dado saem da conta; a nota é proporcional aos critérios avaliados.")

st.info("Lembrete: qualidade da gestão e respeito ao minoritário não dá para automatizar. "
        "Isto é uma ferramenta de apoio, não uma recomendação de compra.")
