import streamlit as st
import hashlib
from datetime import datetime

# ==================== LOGIN CONFIG ====================
USER = "bk"
PASS_HASH = hashlib.sha256("64920169".encode()).hexdigest()

def login_screen():
    st.title("🔑 Acesso ao Sistema")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u == USER and hashlib.sha256(p.encode()).hexdigest() == PASS_HASH:
            st.session_state.logged = True
            st.session_state.user = u
            st.success("✅ Login realizado!")
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")

# ==================== APP PRINCIPAL ====================
def app_screen():
    st.sidebar.success(f"Usuário: {st.session_state.user}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    st.title("📦 Sistema de Produtos")

    # -------- Cliente --------
    st.subheader("👤 Cliente")
    cliente = st.text_input("Nome", key="cliente")
    endereco = st.text_input("Endereço", key="endereco")
    frete = st.text_input("Frete (opcional)", key="frete")

    # -------- Adicionar Produto --------
    st.subheader("➕ Cadastro de Produto")
    nome = st.text_input("Produto", key="nome")
    custo = st.text_input("Custo", key="custo")
    venda = st.text_input("Venda", key="venda")

    if st.button("Salvar Produto"):
        if nome and custo and venda:
            try:
                custo_val = float(custo.replace(",", "."))
                venda_val = float(venda.replace(",", "."))
                st.session_state.produtos.append({"name": nome, "cost": custo_val, "price": venda_val})
                st.success("✅ Produto adicionado!")
                st.session_state.nome = ""
                st.session_state.custo = ""
                st.session_state.venda = ""
            except:
                st.error("❌ Valores inválidos.")
        else:
            st.warning("⚠️ Preencha todos os campos.")

    # -------- Pesquisar Produto --------
    st.subheader("🔍 Pesquisar Produto")
    termo = st.text_input("Buscar", key="busca")
    if termo:
        filtrados = [p for p in st.session_state.produtos if termo.lower() in p["name"].lower()]
    else:
        filtrados = st.session_state.produtos

    # -------- Lista de Produtos --------
    st.subheader("📋 Lista de Produtos")
    if filtrados:
        for i, p in enumerate(filtrados):
            st.write(f"{i} - {p['name']} | Custo: R$ {p['cost']:.2f} | Venda: R$ {p['price']:.2f}")
    else:
        st.info("Nenhum produto encontrado.")

    # -------- Totais --------
    total_custo = sum(p["cost"] for p in st.session_state.produtos)
    total_venda = sum(p["price"] for p in st.session_state.produtos)
    lucro = total_venda - total_custo
    st.write(f"📊 Custo: R$ {total_custo:.2f} | Venda: R$ {total_venda:.2f} | Lucro: R$ {lucro:.2f}")

    # -------- Carrinho --------
    st.subheader("🛒 Carrinho")
    if st.session_state.produtos:
        nomes = [p["name"] for p in st.session_state.produtos]
        prod_sel = st.selectbox("Produto", nomes)
        qtd = st.number_input("Quantidade", min_value=1, value=1, step=1)
        if st.button("Adicionar ao Carrinho"):
            prod = next(p for p in st.session_state.produtos if p["name"] == prod_sel)
            for item in st.session_state.carrinho:
                if item["name"] == prod["name"]:
                    item["qty"] += qtd
                    break
            else:
                st.session_state.carrinho.append({"name": prod["name"], "unit": prod["price"], "qty": qtd})
            st.success(f"✅ {qtd}x {prod['name']} adicionado!")

    if st.session_state.carrinho:
        for item in st.session_state.carrinho:
            st.write(f"{item['name']} - x{item['qty']} | Unit: R$ {item['unit']:.2f} | Subtotal: R$ {item['qty']*item['unit']:.2f}")
        if st.button("Remover Último Item"):
            st.session_state.carrinho.pop()
            st.info("Item removido.")

    # -------- Cupom --------
    st.code(cupom_texto, language="text")
    if st.button("Gerar Cupom"):
        if not cliente or not endereco:
            st.error("⚠️ Preencha nome e endereço.")
        elif not st.session_state.carrinho:
            st.error("⚠️ Adicione itens ao carrinho.")
        else:
            total = sum(item["unit"] * item["qty"] for item in st.session_state.carrinho)
            try:
                frete_val = float(frete.replace(",", ".")) if frete else 0.0
            except:
                frete_val = 0.0
            total_final = total + frete_val

            lines = []
            lines.append("       DGCELL TAQUARA")
            lines.append("----------------------------")
            lines.append(f"Cliente: {cliente}")
            lines.append(f"Endereço: {endereco}")
            lines.append("Data/Hora: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            lines.append("----------------------------")
            for item in st.session_state.carrinho:
                nome = item["name"]
                qty = item["qty"]
                unit = item["unit"]
                subtotal = unit * qty
                lines.append(f"{nome:<20} x{qty:<3} R$ {unit:>6.2f} R$ {subtotal:>7.2f}")
            lines.append("----------------------------")
            lines.append(f"Subtotal: R$ {total:.2f}")
            lines.append(f"Frete:    R$ {frete_val:.2f}")
            lines.append(f"TOTAL:    R$ {total_final:.2f}")
            lines.append("----------------------------")
            lines.append("Documento sem valor fiscal")
            lines.append("Obrigado pela compra!")

            cupom_texto = "\n".join(lines)
            st.text_area("Cupom", value=cupom_texto, height=400, font="Courier New")

            # Botão de imprimir via navegador
            st.markdown(
                """
                <script>
                function printPage() { window.print(); }
                </script>
                <button onclick="printPage()">🖨️ Imprimir Cupom</button>
                """,
                unsafe_allow_html=True
            )

# ==================== MAIN ====================
if "logged" not in st.session_state:
    st.session_state.logged = False
if "produtos" not in st.session_state:
    st.session_state.produtos = []
if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

if not st.session_state.logged:
    login_screen()
else:
    app_screen()
