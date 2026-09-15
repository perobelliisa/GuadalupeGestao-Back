# Importa Flask, send_from_directory do módulo flask para uso neste arquivo.
from flask import Flask, send_from_directory
# Importa o módulo fdb para disponibilizar seus recursos.
import fdb
# Importa CORS do módulo flask_cors para uso neste arquivo.
from flask_cors import CORS

# Atribui a variável 'app' o resultado da expressão 'Flask(__name__)'.
app= Flask(__name__)

# Carrega as configurações da aplicação a partir do arquivo indicado.
app.config.from_pyfile('config.py')

# Atribui a variável 'host' o resultado da expressão 'app.config['DB_HOST']'.
host= app.config['DB_HOST']

# Atribui a variável 'database' o resultado da expressão 'app.config['DB_NAME']'.
database= app.config['DB_NAME']

# Atribui a variável 'user' o resultado da expressão 'app.config['DB_USER']'.
user= app.config['DB_USER']

# Atribui a variável 'password' o resultado da expressão 'app.config['DB_PASSWORD']'.
password= app.config['DB_PASSWORD']

# Configura quais origens podem acessar a API.
CORS(
    # Disponibiliza o recurso app para as funções deste módulo.
    app,
    # Atribui a variável 'origins' o resultado da expressão '["http://localhost:5173", "http://127.0.0.1:5173"],'.
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    # Atribui a variável 'supports_credentials' o resultado da expressão 'True'.
    supports_credentials=True
# Fecha a chamada ou a lista de argumentos iniciada anteriormente.
)


# Registra o endpoint '/arquivos/<path:nome_arquivo>', associando a URL aos métodos HTTP informados.
@app.route('/arquivos/<path:nome_arquivo>')
# Define a função servir_arquivo, que envia um arquivo existente na pasta de uploads.
def servir_arquivo(nome_arquivo):
    # Retorna send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo).
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo)

# Inicia um bloco protegido para capturar erros durante a operação.
try:
    # Abre a conexão com o banco de dados usando as credenciais configuradas.
    con= fdb.connect(host= host, database=database, user=user, password=password)
    # Exibe esta mensagem no console para informar o resultado da operação.
    print('Banco conectado com sucesso!')
# Captura o erro Exception as e e permite tratá-lo.
except Exception as e:
    # Exibe esta mensagem no console para informar o resultado da operação.
    print('Erro de conexão com o banco de dados')

# Importa * do módulo user para uso neste arquivo.
from user import *
# Importa * do módulo doacoes para uso neste arquivo.
from doacoes import *
# Importa * do módulo emprestimos para uso neste arquivo.
from emprestimos import *
# Importa * do módulo livro_caixa para uso neste arquivo.
from livro_caixa import *


# Verifica se __name__ == '__main__'.
if __name__ == '__main__':
    # Inicia o servidor Flask na interface e porta configuradas.
    app.run(host='0.0.0.0', port=5000)
