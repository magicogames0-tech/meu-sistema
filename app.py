# app_streamlit.py
import streamlit as st
import json
import hashlib
from datetime import datetime
import requests

# ------------------------ Arquivos ------------------------
USERS_FILE = "users.json"
DATA_FILE = "data.json"

def ensure_files():
    try:
        if not os.path.exists(USERS_FILE):
            default_user = {
                "users": [
                    {"username": "bk", "password_hash": hashlib.sha256("64920169".encode()).hexdigest()}
                ]
            }
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_user, f, ensure_ascii=False, indent=2)
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"products": []}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erro ao criar arquivos: {e}")

def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("users", [])

def verify_login(username, password):
    phash = hashlib.sha256(password.encode()).hexdigest()
    for u in load_users():
        if u.get("username") == username and u.get("password_hash") == phash:
            return True
    return False

def load_products():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("products", [])

def save_products(products):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"products": products}, f, ensure_ascii=False, indent=2)

def parse_price(text):
    return float(text.replace("R$", "").replace(",", ".").strip())

def format_currency(value):
    return f"R$ {value:.2f}"

# ------------------------ Licença ------------------------
KEYS_URL = "https://gist.githubusercontent.com/magicogames0-tech/a24facbd2865b03780786ef5cf992bf7/raw/keys.json"
MINHA_KEY = "thcell1"

def validar_key(key: str):
    try:
        r = requests.get(KEYS_URL, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        for item in data.get("keys", []):
            if item.get("key", "").strip() == key:
                exp_str = item.get("valid_until", "").strip()
                if not exp_str:
                    return None
                exp = datetime.strptime(exp_str, "%Y-%m-%d").date()
                if datetime.now().date() > exp:
                    return None
                return exp
        return None
    except Exception as e:
        st.error("Erro na validação da chave: " + str(e))
        return None

validade = validar_key(MINHA_KEY)
if not validade:
    st.stop()
else:
    st.success(f"Sistema liberado até {validade.strftime('%d/%m/%Y')}")

# ------------------------ Login ------------------------
st.title("🔑 Sistema de Produtos")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if verify_login(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.experimental_rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# ------------------------ App Principal ------------------------
if st.session_state.logged_in:
    st.subheader(f"Bem-vindo, {st.session_state.username}")
    
    products = load_products()
    
    # Adicionar produto
    st.markdown("### ➕ Adicionar Produto")
    col1, col2, col3 = st.columns(3)
    name = col1.text_input("Nome do produto", key="new_name")
    cost = col2.text_input("Custo", key="new_cost")
    price = col3.text_input("Venda", key="new_price")
    if st.button("Adicionar Produto"):
        if name and cost and price:
            try:
                products.append({
                    "name": name,
                    "cost": parse_price(cost),
                    "price": parse_price(price)
                })
                save_products(products)
                st.success("Produto adicionado!")
            except:
                st.error("Valores inválidos.")
        else:
            st.warning("Preencha todos os campos.")

    # Pesquisa
    st.markdown("### 🔍 Pesquisar Produtos")
    search_term = st.text_input("Buscar por nome")
    filtered = [p for p in products if search_term.lower() in p["name"].lower()]

    # Lista de produtos
    st.markdown("### 📝 Produtos")
    for idx, p in enumerate(filtered):
        col1, col2, col3, col4 = st.columns([3,1,1,1])
        col1.write(p["name"])
        col2.write(format_currency(p["cost"]))
        col3.write(format_currency(p["price"]))
        if col4.button("Remover", key=f"rm_{idx}"):
            products.remove(p)
            save_products(products)
            st.experimental_rerun()

    # Totais
    total_cost = sum(p["cost"] for p in filtered)
    total_price = sum(p["price"] for p in filtered)
    lucro = total_price - total_cost
    st.markdown(f"**Itens:** {len(filtered)} | **Custo Total:** {format_currency(total_cost)} | **Venda Total:** {format_currency(total_price)} | **Lucro:** {format_currency(lucro)}")

    # Gerar cupom
    st.markdown("### 🧾 Gerar Cupom")
    st.write("Selecione produtos para gerar cupom:")
    cupom_cart = []
    for p in filtered:
        qty = st.number_input(f"{p['name']} (R$ {p['price']:.2f})", min_value=0, step=0, key=f"cupom_{p['name']}")
        if qty > 0:
            cupom_cart.append({"name": p["name"], "unit": p["price"], "qty": qty})
    frete = st.text_input("Frete (opcional)", value="0")
    if st.button("Gerar Cupom"):
        if cupom_cart:
            total = sum(item["unit"]*item["qty"] for item in cupom_cart)
            try:
                frete_val = parse_price(frete)
            except:
                frete_val = 0
            total_final = total + frete_val
            st.text_area("Cupom", value="\n".join([
                "-------- CUPOM --------",
                f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                "----------------------",
                *[f"{item['name']} x{item['qty']} {format_currency(item['unit'])} {format_currency(item['unit']*item['qty'])}" for item in cupom_cart],
                "----------------------",
                f"Frete: {format_currency(frete_val)}",
                f"TOTAL: {format_currency(total_final)}",
                "----------------------",
                "Documento sem valor fiscal",
                "Obrigado pela compra!"
            ]), height=300)
        else:
            st.warning("Adicione ao menos um item para gerar o cupom.")
