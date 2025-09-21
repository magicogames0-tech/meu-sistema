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
# Executa a inicialização das tabelas sempre que o app inicia
# =====================================================
init_db()

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

    resultado = [{"id": cid, "nome": nome} for cid, nome in clientes]
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

    # Listar agendamentos ativos
    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora, ag.status
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    WHERE ag.status = 'ativo'
    ORDER BY ag.id DESC
    """)
    agendamentos = c.fetchall()

    # Listar todos os clientes (para fallback ou debug)
    c.execute("SELECT * FROM clientes ORDER BY id DESC")
    clientes = c.fetchall()
    conn.close()

    return render_template("agendamentos.html", agendamentos=agendamentos, clientes=clientes)

# =====================================================
# Finalizar / Desmarcar
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
