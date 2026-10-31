import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Painel Barsi", page_icon="📈", layout="wide")

PADRAO = {
    "BBAS3": "Banco", "BBSE3": "Seguros", "BRAP4": "Holding/Mineração",
    "CSMG3": "Saneamento", "CXSE3": "Seguros", "CYRE4": "Construção",
    "ISAE4": "Energia", "PETR4": "Petróleo",
}
SETORES = ["Banco", "Seguros", "Energia", "Saneamento", "Telecom", "Holding/Mineração",
           "Petróleo", "Construção", "Varejo", "Indústria", "Outros"]
PERENES = {"Banco", "Energia", "Saneamento", "Seguros", "Telecom"}
PESOS = {
    "Setor perene": 1.0, "Div. consistentes": 2.0, "DY ok": 2.0, "Lucro +": 1.0,
    "ROE ok": 1.5, "Dívida ok": 1.0, "Abaixo do teto": 1.5,
}

# ---------- Carteira salva no link da página ----------
def carregar():
    txt = st.query_params.get("c")
    if txt:
        cart = {}
        for item in txt.split(";"):
            if ":" in item:
                t, s = item.split(":", 1)
                cart[t] = s
        if cart:
            return cart
    return dict(PADRAO)

def salvar():
    st.query_params["c"] = ";".join(f"{t}:{s}" for t, s in st.session_state.carteira.items())

if "carteira" not in st.session_state:
    st.session_state.carteira = carregar()

# ---------- Busca de dados ----------
@st.cache_data(ttl=900)
def buscar(ticker):
    acao = yf.Ticker(f"{ticker}.SA")
    try:
        info = acao.info or {}
    except Exception:
        info = {}
    preco = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose")
    if not preco:
        try:
            fech = acao.history(period="1mo")["Close"].dropna()
            preco = float(fech.iloc[-1]) if not fech.empty else None
        except Exception:
            preco = None
    divs = acao.dividends
    return preco, divs, info.get("returnOnEquity"), info.get("debtToEquity"), info.get("trailingPE")

# ---------- Barra lateral ----------
st.sidebar.header("Minha carteira")
with st.sidebar.form("adicionar", clear_on_submit=True):
    novo = st.text_input("Ticker (ex: ITSA4)")
    setor_novo = st.selectbox("Setor", SETORES)
    adicionar = st.form_submit_button("➕ Adicionar")
if adicionar and novo.strip():
    t = novo.strip().upper().replace(".SA", "")
    if t in st.session_state.carteira:
        st.sidebar.info(f"{t} já está na carteira.")
    elif buscar(t)[0] is None:
        st.sidebar.error(f"Não encontrei {t} no Yahoo Finance. Confira o ticker.")
    else:
        st.session_state.carteira[t] = setor_novo
        salvar()
        st.sidebar.success(f"{t} adicionado!")

remover = st.sidebar.multiselect("Remover tickers", list(st.session_state.carteira))
if st.sidebar.button("🗑️ Remover selecionados") and remover:
    for t in remover:
        st.session_state.carteira.pop(t, None)
    salvar()
    st.rerun()
if st.sidebar.button("↩️ Restaurar carteira original"):
    st.session_state.carteira = dict(PADRAO)
    salvar()
    st.rerun()

st.sidebar.header("Parâmetros")
DY_MIN = st.sidebar.slider("DY mínimo (%)", 3.0, 12.0, 6.0, 0.5) / 100
ANOS = st.sidebar.slider("Anos seguidos pagando dividendos", 3, 10, 5)
ROE_MIN = st.sidebar.slider("ROE mínimo (%)", 5, 25, 10) / 100
DIV_MAX = st.sidebar.slider("Dívida/PL máxima (%)", 20, 150, 70)
NOTA_MIN = st.sidebar.slider("Nota mínima para compra", 5.0, 10.0, 7.0, 0.5)

# ---------- Avaliação ----------
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
    status = "✅ DENTRO" if nota >= NOTA_MIN else "⚠️ QUASE" if nota >= NOTA_MIN - 1.5 else "❌ FORA"

    linha = {"Ticker": ticker, "Setor": setor, "Preço": preco, "Teto Bazin": teto,
             "Margem até o teto (%)": (teto / preco - 1) * 100 if preco and teto else None,
             "DY 12m (%)": dy * 100 if dy is not None else None,
             "ROE (%)": roe * 100 if roe is not None else None, "P/L": pl}
    linha.update({k: "➖" if v is None else ("✅" if v else "❌") for k, v in crit.items()})
    linha["Nota (0-10)"] = nota
    linha["Status"] = status
    return linha

# ---------- Página ----------
st.title("📈 Painel Barsi da minha carteira")
col1, col2 = st.columns([3, 1])
col1.caption(f"Atualizado em {datetime.now():%d/%m/%Y %H:%M} · Yahoo Finance (atraso ~15 min) · ➖ = sem dado")
if col2.button("🔄 Atualizar agora"):
    st.cache_data.clear()

linhas = []
with st.spinner("Buscando dados..."):
    for t, s in st.session_state.carteira.items():
        try:
            linhas.append(analisar(t, s))
        except Exception as e:
            st.warning(f"{t}: não consegui buscar os dados ({e})")

df = pd.DataFrame(linhas)
if df.empty:
    st.info("A carteira está vazia. Adicione tickers na barra lateral.")
else:
    df = df.sort_values("Nota (0-10)", ascending=False)
    dentro = (df["Status"] == "✅ DENTRO").sum()
    quase = (df["Status"] == "⚠️ QUASE").sum()
    fora = len(df) - dentro - quase
    media = df["Nota (0-10)"].mean()

    # Cartões de resumo, sempre numa linha só (inclusive no celular)
    cartoes = [("✅ Dentro", dentro, "#2e7d32"), ("⚠️ Quase", quase, "#f9a825"),
               ("❌ Fora", fora, "#c62828"), ("⭐ Média", f"{media:.1f}", "#1565c0")]
    html = "".join(
        f"<div style='flex:1;min-width:0;border-left:4px solid {c};background:rgba(255,255,255,0.05);"
        f"border-radius:8px;padding:8px 6px;text-align:center'>"
        f"<div style='font-size:0.75rem;opacity:0.8;white-space:nowrap'>{rot}</div>"
        f"<div style='font-size:1.6rem;font-weight:700;line-height:1.2'>{val}</div></div>"
        for rot, val, c in cartoes)
    st.markdown(f"<div style='display:flex;gap:8px;margin:8px 0 16px'>{html}</div>",
                unsafe_allow_html=True)

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
        st.write(pd.DataFrame({"Critério": list(PESOS), "Peso": list(PESOS.values())}))
        st.caption("Critérios sem dado saem da conta; a nota é proporcional aos critérios avaliados.")

st.info("Lembrete: qualidade da gestão e respeito ao minoritário não dá para automatizar. "
        "Isto é uma ferramenta de apoio, não uma recomendação de compra.")
