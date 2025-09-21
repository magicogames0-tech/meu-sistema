from flask import Flask, render_template_string, request, redirect, url_for
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
# Template base
# =====================================================
template = """
<!DOCTYPE html>
<html>
<head>
    <title>Agenda Online</title>
    <style>
        body { font-family: Arial; background: #f5f5f5; margin: 0; padding: 0; }
        .navbar { background: #333; padding: 10px; text-align: center; }
        .navbar a { color: white; margin: 0 15px; text-decoration: none; font-weight: bold; }
        .container { max-width: 800px; margin: 30px auto; background: white; padding: 20px; border-radius: 10px; }
        h2 { text-align: center; }
        input, select { width: 100%; padding: 8px; margin: 5px 0; }
        button { background: green; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer; }
        table { width: 100%; margin-top: 20px; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background: #eee; }
        .btn { padding: 5px 10px; border: none; border-radius: 5px; cursor: pointer; }
        .btn-red { background: red; color: white; }
        .btn-blue { background: blue; color: white; }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="{{ url_for('clientes') }}">👤 Clientes</a>
        <a href="{{ url_for('agendamentos') }}">📅 Agendamentos</a>
        <a href="{{ url_for('finalizados') }}">✅ Finalizados</a>
        <a href="{{ url_for('desmarcados') }}">❌ Desmarcados</a>
    </div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

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

    return render_template_string(template + """
    {% block content %}
    <h2>👤 Cadastro de Clientes</h2>
    <form method="post">
        Nome: <input type="text" name="nome" required><br>
        Telefone: <input type="text" name="telefone"><br>
        <button type="submit">Cadastrar</button>
    </form>
    <h3>Lista de Clientes</h3>
    <table>
        <tr><th>ID</th><th>Nome</th><th>Telefone</th></tr>
        {% for c in clientes %}
        <tr>
            <td>{{ c[0] }}</td>
            <td>{{ c[1] }}</td>
            <td>{{ c[2] }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endblock %}
    """, clientes=clientes)

# =====================================================
# Rotas de Agendamento
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

    return render_template_string(template + """
    {% block content %}
    <h2>📅 Agendamentos</h2>
    <form method="post">
        Cliente:
        <select name="cliente_id" required>
            {% for c in clientes %}
            <option value="{{ c[0] }}">{{ c[1] }}</option>
            {% endfor %}
        </select><br>
        Data: <input type="date" name="data" required><br>
        Hora: <input type="time" name="hora" required><br>
        <button type="submit">Agendar</button>
    </form>
    <h3>Lista de Agendamentos</h3>
    <table>
        <tr><th>ID</th><th>Cliente</th><th>Data</th><th>Hora</th><th>Ações</th></tr>
        {% for ag in agendamentos %}
        <tr>
            <td>{{ ag[0] }}</td>
            <td>{{ ag[1] }}</td>
            <td>{{ ag[2] }}</td>
            <td>{{ ag[3] }}</td>
            <td>
                <a href="{{ url_for('finalizar', agendamento_id=ag[0]) }}"><button class="btn btn-blue">Finalizar</button></a>
                <a href="{{ url_for('desmarcar', agendamento_id=ag[0]) }}"><button class="btn btn-red">Desmarcar</button></a>
            </td>
        </tr>
        {% endfor %}
    </table>
    {% endblock %}
    """, agendamentos=agendamentos, clientes=clientes)

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

    return render_template_string(template + """
    {% block content %}
    <h2>✅ Agendamentos Finalizados</h2>
    <table>
        <tr><th>ID</th><th>Cliente</th><th>Data</th><th>Hora</th></tr>
        {% for ag in finalizados %}
        <tr>
            <td>{{ ag[0] }}</td>
            <td>{{ ag[1] }}</td>
            <td>{{ ag[2] }}</td>
            <td>{{ ag[3] }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endblock %}
    """, finalizados=finalizados)

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

    return render_template_string(template + """
    {% block content %}
    <h2>❌ Agendamentos Desmarcados</h2>
    <table>
        <tr><th>ID</th><th>Cliente</th><th>Data</th><th>Hora</th></tr>
        {% for ag in desmarcados %}
        <tr>
            <td>{{ ag[0] }}</td>
            <td>{{ ag[1] }}</td>
            <td>{{ ag[2] }}</td>
            <td>{{ ag[3] }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endblock %}
    """, desmarcados=desmarcados)

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
