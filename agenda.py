from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# =====================================================
# Configuração do Banco
# =====================================================
DATABASE_URL = os.environ.get("DATABASE_URL")  # Pega do environment do Render

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# =====================================================
# Inicializar banco de dados
# =====================================================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Tabela de clientes
    c.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        telefone TEXT
    )
    """)

    # Tabela de agendamentos
    c.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER REFERENCES clientes(id),
        data TEXT,
        hora TEXT,
        status TEXT DEFAULT 'ativo'
    )
    """)

    conn.commit()
    conn.close()

# =====================================================
# Autocomplete de clientes
# =====================================================
@app.route("/buscar_clientes")
def buscar_clientes():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, nome FROM clientes WHERE nome ILIKE %s", ('%' + q + '%',))
    clientes = c.fetchall()
    conn.close()

    resultado = [{"id": c["id"], "nome": c["nome"]} for c in clientes]
    return jsonify(resultado)

# =====================================================
# Rotas de Clientes
# =====================================================
@app.route("/clientes", methods=["GET", "POST"])
def clientes_view():
    conn = get_conn()
    c = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form.get("telefone", "")
        c.execute("INSERT INTO clientes (nome, telefone) VALUES (%s, %s)", (nome, telefone))
        conn.commit()
        conn.close()
        return redirect(url_for("clientes_view"))

    c.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = c.fetchall()
    conn.close()
    return render_template("clientes.html", clientes=clientes)

@app.route("/clientes/excluir/<int:cliente_id>")
def excluir_cliente(cliente_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM agendamentos WHERE cliente_id=%s", (cliente_id,))
    c.execute("DELETE FROM clientes WHERE id=%s", (cliente_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("clientes_view"))

# =====================================================
# Rotas de Agendamentos
# =====================================================
@app.route("/agendamentos", methods=["GET", "POST"])
def agendamentos_view():
    conn = get_conn()
    c = conn.cursor()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        data = request.form.get("data")
        hora = request.form.get("hora")

        if not cliente_id:
            return "Erro: selecione um cliente válido.", 400

        c.execute(
            "INSERT INTO agendamentos (cliente_id, data, hora) VALUES (%s, %s, %s)",
            (cliente_id, data, hora)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("agendamentos_view"))

    # Lista de agendamentos com nomes dos clientes
    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora, ag.status
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    ORDER BY ag.id DESC
    """)
    agendamentos = c.fetchall()

    conn.close()
    return render_template("agendamentos.html", agendamentos=agendamentos)

@app.route("/agendamentos/excluir/<int:agendamento_id>")
def excluir_agendamento(agendamento_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM agendamentos WHERE id=%s", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos_view"))

@app.route("/finalizar/<int:agendamento_id>")
def finalizar(agendamento_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE agendamentos SET status='finalizado' WHERE id=%s", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos_view"))

@app.route("/desmarcar/<int:agendamento_id>")
def desmarcar(agendamento_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE agendamentos SET status='desmarcado' WHERE id=%s", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos_view"))

# =====================================================
# Home
# =====================================================
@app.route("/")
def home():
    return redirect(url_for("agendamentos_view"))

# =====================================================
# Inicialização
# =====================================================
if __name__ == "__main__":
    init_db()
    # app.run()  # Não é necessário no Render
