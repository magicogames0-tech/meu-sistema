from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# --------------------- BANCO DE DADOS ---------------------
def init_db():
    conn = sqlite3.connect("agenda.db")
    cur = conn.cursor()
    # tabela de clientes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT
        )
    """)
    # tabela de agendamentos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            status TEXT DEFAULT 'ativo',
            FOREIGN KEY(cliente_id) REFERENCES clientes(id)
        )
    """)
    conn.commit()
    conn.close()

def query(sql, params=(), fetch=False):
    conn = sqlite3.connect("agenda.db")
    cur = conn.cursor()
    cur.execute(sql, params)
    data = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

# --------------------- BASE TEMPLATE ---------------------
base_html = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('clientes') }}">📅 Agenda</a>
    <div>
      <a class="btn btn-outline-light btn-sm" href="{{ url_for('clientes') }}">👤 Clientes</a>
      <a class="btn btn-outline-light btn-sm" href="{{ url_for('agendamentos') }}">📅 Agendamentos</a>
      <a class="btn btn-outline-light btn-sm" href="{{ url_for('historico') }}">📂 Histórico</a>
    </div>
  </div>
</nav>
<div class="container">
    {% block content %}{% endblock %}
</div>
</body>
</html>
"""

# --------------------- TEMPLATES ---------------------
tpl_clientes = """
{% extends "base" %}
{% block content %}
<h2>👤 Cadastro de Clientes</h2>
<form method="post" class="card p-3 shadow-sm mb-4">
    <div class="mb-2">
        <label class="form-label">Nome</label>
        <input type="text" name="nome" class="form-control" required>
    </div>
    <div class="mb-2">
        <label class="form-label">Telefone</label>
        <input type="text" name="telefone" class="form-control">
    </div>
    <button type="submit" class="btn btn-success">Cadastrar</button>
</form>
<h3>Lista de Clientes</h3>
<table class="table table-striped table-bordered shadow-sm">
    <tr><th>Nome</th><th>Telefone</th></tr>
    {% for c in clientes %}
    <tr><td>{{ c[1] }}</td><td>{{ c[2] if c[2] else "-" }}</td></tr>
    {% endfor %}
</table>
{% endblock %}
"""

tpl_agendamentos = """
{% extends "base" %}
{% block content %}
<h2>📅 Agendamentos</h2>

<!-- Formulário de novo agendamento -->
<form method="post" class="card p-3 shadow-sm mb-4">
    <h5>Novo Agendamento</h5>
    <div class="mb-2">
        <label class="form-label">Cliente</label>
        <select name="cliente_id" class="form-select" required>
            {% for c in clientes %}
                <option value="{{ c[0] }}">{{ c[1] }}</option>
            {% endfor %}
        </select>
    </div>
    <div class="mb-2">
        <label class="form-label">Data</label>
        <input type="date" name="data" class="form-control" required>
    </div>
    <div class="mb-2">
        <label class="form-label">Hora</label>
        <input type="time" name="hora" class="form-control" required>
    </div>
    <button type="submit" class="btn btn-primary">Agendar</button>
</form>

<!-- Filtro de busca -->
<form method="get" class="card p-3 shadow-sm mb-4">
    <h5>🔎 Buscar Agendamentos</h5>
    <div class="row g-2">
        <div class="col-md-6">
            <input type="text" name="cliente" value="{{ request.args.get('cliente','') }}" placeholder="Nome do cliente" class="form-control">
        </div>
        <div class="col-md-4">
            <input type="date" name="data" value="{{ request.args.get('data','') }}" class="form-control">
        </div>
        <div class="col-md-2">
            <button type="submit" class="btn btn-dark w-100">Filtrar</button>
        </div>
    </div>
</form>

<!-- Lista de agendamentos -->
<h3>Agendamentos Ativos</h3>
<table class="table table-striped table-bordered shadow-sm">
    <tr><th>Cliente</th><th>Data</th><th>Hora</th><th>Ações</th></tr>
    {% for a in agendamentos %}
    <tr>
        <td>{{ a[1] }}</td>
        <td>{{ a[2] }}</td>
        <td>{{ a[3] }}</td>
        <td>
            <a href="{{ url_for('finalizar', ag_id=a[0]) }}" class="btn btn-sm btn-success">✅ Finalizar</a>
            <a href="{{ url_for('cancelar', ag_id=a[0]) }}" class="btn btn-sm btn-danger">❌ Cancelar</a>
        </td>
    </tr>
    {% endfor %}
    {% if not agendamentos %}
    <tr><td colspan="4">Nenhum agendamento encontrado</td></tr>
    {% endif %}
</table>
{% endblock %}
"""

tpl_historico = """
{% extends "base" %}
{% block content %}
<h2>📂 Histórico do Dia</h2>
<h3 class="text-success">✅ Finalizados</h3>
<ul class="list-group mb-3 shadow-sm">
    {% for f in finalizados %}
        <li class="list-group-item">{{ f[1] }} - {{ f[2] }} {{ f[3] }}</li>
    {% endfor %}
    {% if not finalizados %}<li class="list-group-item">Nenhum finalizado hoje</li>{% endif %}
</ul>

<h3 class="text-danger">❌ Cancelados</h3>
<ul class="list-group shadow-sm">
    {% for c in cancelados %}
        <li class="list-group-item">{{ c[1] }} - {{ c[2] }} {{ c[3] }}</li>
    {% endfor %}
    {% if not cancelados %}<li class="list-group-item">Nenhum cancelado hoje</li>{% endif %}
</ul>
{% endblock %}
"""

# --------------------- ROTAS ---------------------
@app.route("/")
def home():
    return redirect(url_for("clientes"))

@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form.get("telefone")
        query("INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (nome, telefone))
        return redirect(url_for("clientes"))
    clientes = query("SELECT * FROM clientes", fetch=True)
    return render_template_string(tpl_clientes, clientes=clientes, title="Clientes", base=base_html)

@app.route("/agendamentos", methods=["GET", "POST"])
def agendamentos():
    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        data = request.form["data"]
        hora = request.form["hora"]
        query("INSERT INTO agendamentos (cliente_id, data, hora) VALUES (?, ?, ?)", (cliente_id, data, hora))
        return redirect(url_for("agendamentos"))

    # Filtros da busca
    cliente_filtro = request.args.get("cliente", "").strip()
    data_filtro = request.args.get("data", "").strip()

    sql = """SELECT a.id, c.nome, a.data, a.hora 
             FROM agendamentos a
             JOIN clientes c ON c.id=a.cliente_id
             WHERE a.status='ativo' """
    params = []

    if cliente_filtro:
        sql += " AND c.nome LIKE ?"
        params.append(f"%{cliente_filtro}%")

    if data_filtro:
        sql += " AND a.data=?"
        params.append(data_filtro)

    sql += " ORDER BY a.data, a.hora"
    agendamentos = query(sql, tuple(params), fetch=True)

    clientes = query("SELECT * FROM clientes", fetch=True)
    return render_template_string(
        tpl_agendamentos,
        clientes=clientes,
        agendamentos=agendamentos,
        title="Agendamentos",
        base=base_html
    )

@app.route("/finalizar/<int:ag_id>")
def finalizar(ag_id):
    query("UPDATE agendamentos SET status='finalizado' WHERE id=?", (ag_id,))
    return redirect(url_for("agendamentos"))

@app.route("/cancelar/<int:ag_id>")
def cancelar(ag_id):
    query("UPDATE agendamentos SET status='cancelado' WHERE id=?", (ag_id,))
    return redirect(url_for("agendamentos"))

@app.route("/historico")
def historico():
    hoje = datetime.now().date().isoformat()
    finalizados = query("""SELECT a.id, c.nome, a.data, a.hora 
                           FROM agendamentos a 
                           JOIN clientes c ON c.id=a.cliente_id
                           WHERE a.status='finalizado' AND a.data=?""", (hoje,), fetch=True)
    cancelados = query("""SELECT a.id, c.nome, a.data, a.hora 
                           FROM agendamentos a 
                           JOIN clientes c ON c.id=a.cliente_id
                           WHERE a.status='cancelado' AND a.data=?""", (hoje,), fetch=True)
    return render_template_string(tpl_historico, finalizados=finalizados, cancelados=cancelados, title="Histórico", base=base_html)

# --------------------- MAIN ---------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
