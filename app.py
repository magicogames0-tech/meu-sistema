import streamlit as st
import hashlib
import json
from datetime import datetime

# ------------------- DADOS INTERNOS -------------------
USERS = [
    {"username": "bk", "password_hash": hashlib.sha256("64920169".encode()).hexdigest()}
]

PRODUCTS = []

# ------------------- FUNÇÕES -------------------
def verify_login(username, password):
    phash = hashlib.sha256(password.encode()).hexdigest()
    for u in USERS:
        if u["username"] == username and u["password_hash"] == phash:
            return True
    return False

def format_currency(value: float) -> str:
    return f"R$ {value:.2f}"

# ------------------- STREAMLIT -------------------
st.set_page_config(page_title="Sistema de Produtos", layout="wide")

if "logged" not in st.session_state:
    st.session_state.logged = False
if "user" not in st.session_state:
    st.session_state.user = None

# Login
if not st.session_state.logged:
    st.title("🔑 Login no Sistema")
    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if verify_login(user, pwd):
            st.session_state.logged = True
            st.session_state.user = user
            st.success("✅ Login realizado com sucesso!")
        else:
            st.error("❌ Usuário ou senha incorretos.")

else:
    st.sidebar.success(f"Usuário: {st.session_state.user}")
    st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"logged": False}))

    st.title("📦 Sistema de Produtos")

    # Adicionar produto
    with st.expander("➕ Adicionar Produto"):
        name = st.text_input("Nome")
        cost = st.number_input("Custo", min_value=0.0, step=0.01)
        price = st.number_input("Venda", min_value=0.0, step=0.01)
        if st.button("Salvar Produto"):
            PRODUCTS.append({"name": name, "cost": cost, "price": price})
            st.success("Produto adicionado!")

    # Lista de produtos
    st.subheader("📋 Lista de Produtos")
    if PRODUCTS:
        total_cost = sum(p["cost"] for p in PRODUCTS)
        total_price = sum(p["price"] for p in PRODUCTS)
        lucro = total_price - total_cost

        st.table([
            {"Produto": p["name"], "Custo": format_currency(p["cost"]), "Venda": format_currency(p["price"])}
            for p in PRODUCTS
        ])

        st.info(f"**Itens:** {len(PRODUCTS)} | **Custo Total:** {format_currency(total_cost)} | **Venda Total:** {format_currency(total_price)} | **Lucro:** {format_currency(lucro)}")
    else:
        st.warning("Nenhum produto cadastrado ainda.")
