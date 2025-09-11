import streamlit as st
import json
import hashlib
from datetime import datetime
import os

USERS_FILE = "users.json"
DATA_FILE = "data.json"

# ---------------- UTILIDADES ----------------
def ensure_files():
    if not os.path.exists(USERS_FILE):
        default_user = {
            "users": [
                {
                    "username": "admin",
                    "password_hash": hashlib.sha256("1234".encode()).hexdigest(),
                }
            ]
        }
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_user, f, indent=2)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"products": []}, f, indent=2)

def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["users"]

def verify_login(username, password):
    users = load_users()
    phash = hashlib.sha256(password.encode()).hexdigest()
    return any(u["username"] == username and u["password_hash"] == phash for u in users)

def load_products():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["products"]

def save_products(products):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f, indent=2)

def format_currency(v):
    return f"R$ {v:.2f}"

# ---------------- LOGIN ----------------
def login_screen():
    st.title("🔑 Sistema de Produtos - Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if verify_login(username, password):
            st.session_state["logged"] = True
            st.session_state["user"] = username
            st.success("Login realizado com sucesso!")
        else:
            st.error("Usuário ou senha incorretos.")

# ---------------- DASHBOARD ----------------
def dashboard():
    st.title("📦 Sistema de Produtos")
    st.write(f"👤 Usuário: {st.session_state['user']}")
    st.write("Data/Hora:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    products = load_products()

    # Exibir tabela
    st.subheader("📋 Lista de Produtos")
    if products:
        st.table(
            [{"Produto": p["name"], "Custo": format_currency(p["cost"]), "Venda": format_currency(p["price"])}
             for p in products]
        )
    else:
        st.info("Nenhum produto cadastrado ainda.")

    # Adicionar produto
    st.subheader("➕ Adicionar Produto")
    name = st.text_input("Nome do Produto")
    cost = st.number_input("Custo", min_value=0.0, format="%.2f")
    price = st.number_input("Preço de Venda", min_value=0.0, format="%.2f")

    if st.button("Salvar Produto"):
        if name and cost and price:
            products.append({"name": name, "cost": float(cost), "price": float(price)})
            save_products(products)
            st.success("Produto adicionado!")
            st.experimental_rerun()
        else:
            st.error("Preencha todos os campos.")

    # Remover produto
    st.subheader("🗑️ Remover Produto")
    nomes = [p["name"] for p in products]
    if nomes:
        sel = st.selectbox("Selecione o produto", nomes)
        if st.button("Remover"):
            products = [p for p in products if p["name"] != sel]
            save_products(products)
            st.success(f"Produto '{sel}' removido!")
            st.experimental_rerun()

# ---------------- APP ----------------
def main():
    ensure_files()

    if "logged" not in st.session_state:
        st.session_state["logged"] = False

    if not st.session_state["logged"]:
        login_screen()
    else:
        dashboard()

if __name__ == "__main__":
    main()
