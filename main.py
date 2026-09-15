from flask import Flask, send_from_directory
import fdb
from flask_cors import CORS

app= Flask(__name__)

app.config.from_pyfile('config.py')

host= app.config['DB_HOST']

database= app.config['DB_NAME']

user= app.config['DB_USER']

password= app.config['DB_PASSWORD']

CORS(
    app,
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    supports_credentials=True
)


@app.route('/arquivos/<path:nome_arquivo>')
def servir_arquivo(nome_arquivo):
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo)

try:
    con= fdb.connect(host= host, database=database, user=user, password=password)
    print('Banco conectado com sucesso!')
except Exception as e:
    print('Erro de conexão com o banco de dados')

from user import *
from doacoes import *
from emprestimos import *
from livro_caixa import *


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
