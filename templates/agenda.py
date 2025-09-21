import os
import sqlite3

# Caminho absoluto para o banco na pasta do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "agenda.db")
