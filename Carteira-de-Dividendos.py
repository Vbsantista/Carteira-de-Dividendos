# Instalar uma vez:  pip install streamlit yfinance pandas
# Rodar:             streamlit run painel_barsi.py
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
# Barra lateral: ajuste dos parâmetros
st.sidebar.header("Parâmetros")
DY_MIN = st.sidebar.slider("DY mínimo (%)", 3.0, 12.0, 6.0, 0.5) / 100
ANOS = st.sidebar.slider("Anos seguidos pagando dividendos", 3, 10, 5)
ROE_MIN = st.sidebar.slider("ROE mínimo (%)", 5, 25, 10) / 100
DIV_MAX = st.sidebar.slider("Dívida/PL máxima (%)", 20, 150, 70)
extras = st.sidebar.text_input("Adicionar tickers (ex: ITSA4:Banco, TAEE11:Energia)")
for item in [x.strip() for x in extras.split(",") if ":" in x]:
   t, s = item.split(":")
   CARTEIRA[t.strip().upper()] = s.strip()
@st.cache_data(ttl=900)  # guarda os dados por 15 min
def analisar(ticker, setor):
   acao = yf.Ticker(f"{ticker}.SA")
   info = acao.info
   preco = info.get("currentPrice") or info.get("regularMarketPrice")
   divs = acao.dividends
   ano = datetime.now().year
   por_ano = divs.groupby(divs.index.year).sum() if not divs.empty else pd.Series(dtype=float)
   pagou = all(por_ano.get(a, 0) > 0 for a in range(ano - ANOS, ano))
   corte = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1) if not divs.empty else None
   ult12 = divs[divs.index > corte].sum() if corte is not None else 0
   dy = ult12 / preco if preco else 0
   media3 = por_ano.reindex(range(ano - 3, ano)).fillna(0).mean() if not por_ano.empty else 0
   teto = media3 / DY_MIN
   roe, divida, pl = info.get("returnOnEquity"), info.get("debtToEquity"), info.get("trailingPE")
   crit = {
       "Setor perene": setor in PERENES,
       f"Div. {ANOS} anos": pagou,
       "DY ok": dy >= DY_MIN,
       "Lucro +": pl is not None and pl > 0,
       "ROE ok": roe is not None and roe >= ROE_MIN,
       "Dívida ok": divida is None or divida < DIV_MAX,
       "Abaixo do teto": bool(preco) and preco < teto,
   }
   n = sum(crit.values())
   status = "✅ DENTRO" if n == len(crit) else "⚠️ QUASE" if n == len(crit) - 1 else "❌ FORA"
   linha = {"Ticker": ticker, "Setor": setor, "Preço": preco, "Teto Bazin": teto,
            "Margem até o teto (%)": (teto / preco - 1) * 100 if preco else None,
            "DY 12m (%)": dy * 100, "ROE (%)": roe * 100 if roe else None, "P/L": pl}
   linha.update({k: "✅" if v else "❌" for k, v in crit.items()})
   linha["Nota"] = f"{n}/{len(crit)}"
   linha["Status"] = status
   return linha
st.title("📈 Painel Barsi da minha carteira")
col1, col2 = st.columns([3, 1])
col1.caption(f"Atualizado em {datetime.now():%d/%m/%Y %H:%M} · dados do Yahoo Finance (atraso ~15 min)")
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
       return {"✅ DENTRO": "background-color:#c8f7c5", "⚠️ QUASE": "background-color:#fff3b0",
               "❌ FORA": "background-color:#f7c5c5"}.get(v, "")
   st.dataframe(
       df.style.map(cor, subset=["Status"]).format({
           "Preço": "R$ {:.2f}", "Teto Bazin": "R$ {:.2f}", "Margem até o teto (%)": "{:+.1f}",
           "DY 12m (%)": "{:.1f}", "ROE (%)": "{:.1f}", "P/L": "{:.1f}"}, na_rep="—"),
       use_container_width=True, hide_index=True)
st.info("Lembrete: qualidade da gestão e respeito ao minoritário não dá para automatizar. "
       "Isto é uma ferramenta de apoio, não uma recomendação de compra.")
# Instalar uma vez:  pip install streamlit yfinance pandas
# Rodar:             streamlit run painel_barsi.py
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
# Barra lateral: ajuste dos parâmetros
st.sidebar.header("Parâmetros")
DY_MIN = st.sidebar.slider("DY mínimo (%)", 3.0, 12.0, 6.0, 0.5) / 100
ANOS = st.sidebar.slider("Anos seguidos pagando dividendos", 3, 10, 5)
ROE_MIN = st.sidebar.slider("ROE mínimo (%)", 5, 25, 10) / 100
DIV_MAX = st.sidebar.slider("Dívida/PL máxima (%)", 20, 150, 70)
extras = st.sidebar.text_input("Adicionar tickers (ex: ITSA4:Banco, TAEE11:Energia)")
for item in [x.strip() for x in extras.split(",") if ":" in x]:
   t, s = item.split(":")
   CARTEIRA[t.strip().upper()] = s.strip()
@st.cache_data(ttl=900)  # guarda os dados por 15 min
def analisar(ticker, setor):
   acao = yf.Ticker(f"{ticker}.SA")
   info = acao.info
   preco = info.get("currentPrice") or info.get("regularMarketPrice")
   divs = acao.dividends
   ano = datetime.now().year
   por_ano = divs.groupby(divs.index.year).sum() if not divs.empty else pd.Series(dtype=float)
   pagou = all(por_ano.get(a, 0) > 0 for a in range(ano - ANOS, ano))
   corte = pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=1) if not divs.empty else None
   ult12 = divs[divs.index > corte].sum() if corte is not None else 0
   dy = ult12 / preco if preco else 0
   media3 = por_ano.reindex(range(ano - 3, ano)).fillna(0).mean() if not por_ano.empty else 0
   teto = media3 / DY_MIN
   roe, divida, pl = info.get("returnOnEquity"), info.get("debtToEquity"), info.get("trailingPE")
   crit = {
       "Setor perene": setor in PERENES,
       f"Div. {ANOS} anos": pagou,
       "DY ok": dy >= DY_MIN,
       "Lucro +": pl is not None and pl > 0,
       "ROE ok": roe is not None and roe >= ROE_MIN,
       "Dívida ok": divida is None or divida < DIV_MAX,
       "Abaixo do teto": bool(preco) and preco < teto,
   }
   n = sum(crit.values())
   status = "✅ DENTRO" if n == len(crit) else "⚠️ QUASE" if n == len(crit) - 1 else "❌ FORA"
   linha = {"Ticker": ticker, "Setor": setor, "Preço": preco, "Teto Bazin": teto,
            "Margem até o teto (%)": (teto / preco - 1) * 100 if preco else None,
            "DY 12m (%)": dy * 100, "ROE (%)": roe * 100 if roe else None, "P/L": pl}
   linha.update({k: "✅" if v else "❌" for k, v in crit.items()})
   linha["Nota"] = f"{n}/{len(crit)}"
   linha["Status"] = status
   return linha
st.title("📈 Painel Barsi da minha carteira")
col1, col2 = st.columns([3, 1])
col1.caption(f"Atualizado em {datetime.now():%d/%m/%Y %H:%M} · dados do Yahoo Finance (atraso ~15 min)")
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
       return {"✅ DENTRO": "background-color:#c8f7c5", "⚠️ QUASE": "background-color:#fff3b0",
               "❌ FORA": "background-color:#f7c5c5"}.get(v, "")
   st.dataframe(
       df.style.map(cor, subset=["Status"]).format({
           "Preço": "R$ {:.2f}", "Teto Bazin": "R$ {:.2f}", "Margem até o teto (%)": "{:+.1f}",
           "DY 12m (%)": "{:.1f}", "ROE (%)": "{:.1f}", "P/L": "{:.1f}"}, na_rep="—"),
       use_container_width=True, hide_index=True)
st.info("Lembrete: qualidade da gestão e respeito ao minoritário não dá para automatizar. "
       "Isto é uma ferramenta de apoio, não uma recomendação de compra.")
