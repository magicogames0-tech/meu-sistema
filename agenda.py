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
# Rota de busca de clientes para autocomplete
# =====================================================
@app.route("/buscar_clientes")
def buscar_clientes():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, nome FROM clientes WHERE nome ILIKE %s", ('%' + query + '%',))
    clientes = c.fetchall()
    conn.close()

    resultado = [{"id": cliente["id"], "nome": cliente["nome"]} for cliente in clientes]
    return jsonify(resultado)

# =====================================================
# Rotas de Clientes
# =====================================================
@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    conn = get_conn()
    c = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        c.execute("INSERT INTO clientes (nome, telefone) VALUES (%s, %s)", (nome, telefone))
        conn.commit()
        return redirect(url_for("clientes"))

    c.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = c.fetchall()
    conn.close()

    return render_template("clientes.html", clientes=clientes)

@app.route("/clientes/editar/<int:cliente_id>", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    conn = get_conn()
    c = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        c.execute("UPDATE clientes SET nome=%s, telefone=%s WHERE id=%s", (nome, telefone, cliente_id))
        conn.commit()
        conn.close()
        return redirect(url_for("clientes"))

    c.execute("SELECT * FROM clientes WHERE id=%s", (cliente_id,))
    cliente = c.fetchone()
    conn.close()

    return render_template("editar_cliente.html", cliente=cliente)

@app.route("/clientes/excluir/<int:cliente_id>")
def excluir_cliente(cliente_id):
    conn = get_conn()
    c = conn.cursor()
    # Primeiro exclui os agendamentos do cliente
    c.execute("DELETE FROM agendamentos WHERE cliente_id=%s", (cliente_id,))
    # Depois exclui o cliente
    c.execute("DELETE FROM clientes WHERE id=%s", (cliente_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("clientes"))

# =====================================================
# Rotas de Agendamentos
# =====================================================
@app.route("/agendamentos", methods=["GET", "POST"])
def agendamentos():
    conn = get_conn()
    c = conn.cursor()

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        data = request.form["data"]
        hora = request.form["hora"]
        c.execute(
            "INSERT INTO agendamentos (cliente_id, data, hora) VALUES (%s, %s, %s)",
            (cliente_id, data, hora)
        )
        conn.commit()
        return redirect(url_for("agendamentos"))

    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora, ag.status
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    ORDER BY ag.id DESC
    """)
    agendamentos = c.fetchall()

    c.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = c.fetchall()
    conn.close()

    return render_template("agendamentos.html", agendamentos=agendamentos, clientes=clientes)

@app.route("/agendamentos/editar/<int:agendamento_id>", methods=["GET", "POST"])
def editar_agendamento(agendamento_id):
    conn = get_conn()
    c = conn.cursor()

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        data = request.form["data"]
        hora = request.form["hora"]
        status = request.form.get("status", "ativo")
        c.execute(
            "UPDATE agendamentos SET cliente_id=%s, data=%s, hora=%s, status=%s WHERE id=%s",
            (cliente_id, data, hora, status, agendamento_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("agendamentos"))

    c.execute("SELECT * FROM agendamentos WHERE id=%s", (agendamento_id,))
    agendamento = c.fetchone()
    c.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = c.fetchall()
    conn.close()

    return render_template("editar_agendamento.html", agendamento=agendamento, clientes=clientes)

@app.route("/agendamentos/excluir/<int:agendamento_id>")
def excluir_agendamento(agendamento_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM agendamentos WHERE id=%s", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos"))

# =====================================================
# Alterar status do agendamento
# =====================================================
@app.route("/finalizar/<int:agendamento_id>")
def finalizar(agendamento_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE agendamentos SET status='finalizado' WHERE id=%s", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos"))

@app.route("/desmarcar/<int:agendamento_id>")
def desmarcar(agendamento_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE agendamentos SET status='desmarcado' WHERE id=%s", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos"))

# =====================================================
# Listas de Finalizados e Desmarcados
# =====================================================
@app.route("/finalizados")
def finalizados():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora 
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    WHERE ag.status = 'finalizado'
    ORDER BY ag.id DESC
    """)
    finalizados = c.fetchall()
    conn.close()
    return render_template("finalizados.html", finalizados=finalizados)

@app.route("/desmarcados")
def desmarcados():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora 
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    WHERE ag.status = 'desmarcado'
    ORDER BY ag.id DESC
    """)
    desmarcados = c.fetchall()
    conn.close()
    return render_template("desmarcados.html", desmarcados=desmarcados)

# =====================================================
# Home
# =====================================================
@app.route("/")
def home():
    return redirect(url_for("agendamentos"))

# =====================================================
# Inicialização
# =====================================================
if __name__ == "__main__":
    init_db()
    # app.run() não é necessário no Render
