from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# =====================================================
# Inicializar banco de dados
# =====================================================
def init_db():
    conn = sqlite3.connect("agenda.db")
    c = conn.cursor()

    # Tabela de clientes
    c.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT
    )
    """)

    # Tabela de agendamentos
    c.execute("""
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        data TEXT,
        hora TEXT,
        status TEXT DEFAULT 'ativo',
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
    )
    """)

    conn.commit()
    conn.close()

# =====================================================
# Rotas de Clientes
# =====================================================
@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    conn = sqlite3.connect("agenda.db")
    c = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        c.execute("INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (nome, telefone))
        conn.commit()
        return redirect(url_for("clientes"))

    c.execute("SELECT * FROM clientes")
    clientes = c.fetchall()
    conn.close()

    return render_template("clientes.html", clientes=clientes)

# =====================================================
# Rotas de Agendamentos
# =====================================================
@app.route("/agendamentos", methods=["GET", "POST"])
def agendamentos():
    conn = sqlite3.connect("agenda.db")
    c = conn.cursor()

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        data = request.form["data"]
        hora = request.form["hora"]
        c.execute("INSERT INTO agendamentos (cliente_id, data, hora) VALUES (?, ?, ?)", (cliente_id, data, hora))
        conn.commit()
        return redirect(url_for("agendamentos"))

    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora, ag.status
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    WHERE ag.status = 'ativo'
    """)
    agendamentos = c.fetchall()

    c.execute("SELECT * FROM clientes")
    clientes = c.fetchall()
    conn.close()

    return render_template("agendamentos.html", agendamentos=agendamentos, clientes=clientes)

# =====================================================
# Finalizar / Desmarcar
# =====================================================
@app.route("/finalizar/<int:agendamento_id>")
def finalizar(agendamento_id):
    conn = sqlite3.connect("agenda.db")
    c = conn.cursor()
    c.execute("UPDATE agendamentos SET status='finalizado' WHERE id=?", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos"))

@app.route("/desmarcar/<int:agendamento_id>")
def desmarcar(agendamento_id):
    conn = sqlite3.connect("agenda.db")
    c = conn.cursor()
    c.execute("UPDATE agendamentos SET status='desmarcado' WHERE id=?", (agendamento_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("agendamentos"))

# =====================================================
# Listas de Finalizados e Desmarcados
# =====================================================
@app.route("/finalizados")
def finalizados():
    conn = sqlite3.connect("agenda.db")
    c = conn.cursor()
    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora 
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    WHERE ag.status = 'finalizado'
    """)
    finalizados = c.fetchall()
    conn.close()

    return render_template("finalizados.html", finalizados=finalizados)

@app.route("/desmarcados")
def desmarcados():
    conn = sqlite3.connect("agenda.db")
    c = conn.cursor()
    c.execute("""
    SELECT ag.id, cl.nome, ag.data, ag.hora 
    FROM agendamentos ag
    JOIN clientes cl ON ag.cliente_id = cl.id
    WHERE ag.status = 'desmarcado'
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
    app.run(host="0.0.0.0", port=5000)
else:
    with app.app_context():
        init_db()
