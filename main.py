from flask import Flask
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
