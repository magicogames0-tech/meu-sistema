from flask import Flask, render_template_string, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# Banco de dados simples em memória (lista)
agendamentos = []

# HTML básico
template = """
<!DOCTYPE html>
<html>
<head>
    <title>Agenda Online</title>
    <style>
        body { font-family: Arial; background: #f5f5f5; padding: 20px; }
        .container { max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 10px; }
        input, select { width: 100%; padding: 8px; margin: 5px 0; }
        button { background: green; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer; }
        table { width: 100%; margin-top: 20px; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background: #eee; }
    </style>
</head>
<body>
<div class="container">
    <h2>📅 Sistema de Agendamento</h2>
    <form method="post">
        Nome: <input type="text" name="nome" required><br>
        Data: <input type="date" name="data" required><br>
        Hora: <input type="time" name="hora" required><br>
        <button type="submit">Agendar</button>
    </form>

    <h3>Agendamentos</h3>
    <table>
        <tr><th>Nome</th><th>Data</th><th>Hora</th></tr>
        {% for ag in agendamentos %}
        <tr>
            <td>{{ ag['nome'] }}</td>
            <td>{{ ag['data'] }}</td>
            <td>{{ ag['hora'] }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        nome = request.form["nome"]
        data = request.form["data"]
        hora = request.form["hora"]

        # salvar agendamento
        agendamentos.append({"nome": nome, "data": data, "hora": hora})

        return redirect(url_for("home"))
    return render_template_string(template, agendamentos=agendamentos)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
