# Importa o módulo datetime para disponibilizar seus recursos.
import datetime
# Importa o módulo os para disponibilizar seus recursos.
import os
# Importa o módulo unicodedata para disponibilizar seus recursos.
import unicodedata
# Importa Decimal, InvalidOperation do módulo decimal para uso neste arquivo.
from decimal import Decimal, InvalidOperation

# Importa o módulo jwt para disponibilizar seus recursos.
import jwt
# Importa request do módulo flask para uso neste arquivo.
from flask import request
# Importa secure_filename do módulo werkzeug.utils para uso neste arquivo.
from werkzeug.utils import secure_filename

# Importa app, con do módulo main para uso neste arquivo.
from main import app, con


# Atribui a variável 'EXTENSOES_PERMITIDAS' o resultado da expressão '{'.pdf', '.jpg', '.jpeg', '.png'}'.
EXTENSOES_PERMITIDAS = {'.pdf', '.jpg', '.jpeg', '.png'}


# Define a função dados_requisicao, que obtém os dados enviados em JSON ou formulário.
def dados_requisicao():
    # Verifica se request.is_json.
    if request.is_json:
        # Converte os dados recebidos na requisição para um dicionário manipulável.
        dados = request.get_json()
        # Verifica se dados is None.
        if dados is None:
            # Retorna {}.
            return {}
        # Retorna dados.
        return dados
    # Retorna request.form.
    return request.form


# Define a função valor, que lê e normaliza um campo da requisição.
def valor(dados, nome, padrao=''):
    # Atribui a variável 'resposta' o resultado da expressão 'dados.get(nome)'.
    resposta = dados.get(nome)
    # Verifica se resposta is None.
    if resposta is None:
        # Atribui a variável 'resposta' o resultado da expressão 'padrao'.
        resposta = padrao
    # Verifica se resposta is None.
    if resposta is None:
        # Retorna ''.
        return ''
    # Retorna str(resposta).strip().
    return str(resposta).strip()


# Define a função texto_sem_acento, que remove acentos de um texto.
def texto_sem_acento(texto):
    # Converte o valor da expressão para texto e o armazena em 'texto'.
    texto = unicodedata.normalize('NFKD', str(texto))
    # Atribui a variável 'resultado' o resultado da expressão ''''.
    resultado = ''
    # Percorre letra in texto.
    for letra in texto:
        # Verifica se a condição unicodedata.combining(letra) é falsa.
        if not unicodedata.combining(letra):
            # Atribui a variável 'resultado +' o resultado da expressão 'letra'.
            resultado += letra
    # Retorna resultado.strip().lower().
    return resultado.strip().lower()


# Define a função converter_tipo, que converte o código numérico para o tipo textual correspondente.
def converter_tipo(tipo):
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Retorna int(tipo).
        return int(tipo)
    # Captura o erro (TypeError, ValueError) e permite tratá-lo.
    except (TypeError, ValueError):
        # Inicia o dicionário 'tipos' que armazenará os dados da resposta.
        tipos = {
            # Preenche o campo 'dinheiro' do objeto ou resposta que está sendo montado.
            'dinheiro': 0,
            # Preenche o campo 'produto' do objeto ou resposta que está sendo montado.
            'produto': 1,
            # Preenche o campo 'produtos' do objeto ou resposta que está sendo montado.
            'produtos': 1,
            # Preenche o campo 'servico' do objeto ou resposta que está sendo montado.
            'servico': 2,
            # Preenche o campo 'servicos' do objeto ou resposta que está sendo montado.
            'servicos': 2
        # Fecha o dicionário que está sendo montado.
        }
        # Retorna tipos.get(texto_sem_acento(tipo)).
        return tipos.get(texto_sem_acento(tipo))


# Define a função converter_valor, que converte um valor monetário em Decimal.
def converter_valor(numero):
    # Remove espaços extras das extremidades do texto.
    texto = str(numero).strip().replace('R$', '').replace(' ', '')
    # Verifica se ',' in texto.
    if ',' in texto:
        # Atribui a variável 'texto' o resultado da expressão 'texto.replace('.', '')'.
        texto = texto.replace('.', '')
        # Atribui a variável 'texto' o resultado da expressão 'texto.replace(',', '.')'.
        texto = texto.replace(',', '.')
    # Retorna Decimal(texto).
    return Decimal(texto)


# Define a função converter_data, que converte o texto recebido para uma data válida.
def converter_data(data):
    # Remove espaços extras das extremidades do texto.
    texto = str(data).strip()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Verifica se '-' in texto.
        if '-' in texto:
            # Atribui a variável 'partes' o resultado da expressão 'texto.split('-')'.
            partes = texto.split('-')
            # Converte o valor da expressão para inteiro e o armazena em 'ano'.
            ano = int(partes[0])
            # Converte o valor da expressão para inteiro e o armazena em 'mes'.
            mes = int(partes[1])
            # Converte o valor da expressão para inteiro e o armazena em 'dia'.
            dia = int(partes[2])
        # Executa este bloco quando nenhuma condição anterior foi satisfeita.
        else:
            # Atribui a variável 'partes' o resultado da expressão 'texto.split('/')'.
            partes = texto.split('/')
            # Converte o valor da expressão para inteiro e o armazena em 'dia'.
            dia = int(partes[0])
            # Converte o valor da expressão para inteiro e o armazena em 'mes'.
            mes = int(partes[1])
            # Converte o valor da expressão para inteiro e o armazena em 'ano'.
            ano = int(partes[2])
        # Retorna datetime.date(ano, mes, dia).
        return datetime.date(ano, mes, dia)
    # Captura o erro (TypeError, ValueError, IndexError) e permite tratá-lo.
    except (TypeError, ValueError, IndexError):
        # Interrompe a execução e informa ao chamador que os dados recebidos são inválidos.
        raise ValueError('Data inválida.')


# Define a função texto_json, que converte um valor textual para uma resposta JSON segura.
def texto_json(texto):
    # Verifica se texto is None.
    if texto is None:
        # Retorna ''.
        return ''
    # Retorna str(texto).strip().
    return str(texto).strip()


# Define a função data_json, que converte uma data para o formato usado pela API.
def data_json(data):
    # Verifica se data is None.
    if data is None:
        # Retorna None.
        return None
    # Retorna data.isoformat().
    return data.isoformat()


# Define a função numero_json, que converte um valor numérico para uma resposta JSON segura.
def numero_json(numero):
    # Verifica se numero is None.
    if numero is None:
        # Retorna None.
        return None
    # Retorna float(numero).
    return float(numero)


# Define a função ler_inteiro, que converte um texto em número inteiro.
def ler_inteiro(numero, padrao=None):
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Retorna int(numero).
        return int(numero)
    # Captura o erro (TypeError, ValueError) e permite tratá-lo.
    except (TypeError, ValueError):
        # Retorna padrao.
        return padrao


# Define a função salvar_anexo, que valida e salva um arquivo enviado.
def salvar_anexo(arquivo, pasta, prefixo, identificador):
    # Verifica se a condição arquivo or not arquivo.filename é falsa.
    if not arquivo or not arquivo.filename:
        # Retorna None.
        return None

    # Atribui a variável 'nome_original' o resultado da expressão 'secure_filename(arquivo.filename)'.
    nome_original = secure_filename(arquivo.filename)
    # Converte o texto para minúsculas para padronizar a comparação.
    extensao = os.path.splitext(nome_original)[1].lower()
    # Verifica se extensao not in EXTENSOES_PERMITIDAS.
    if extensao not in EXTENSOES_PERMITIDAS:
        # Interrompe a execução e informa ao chamador que os dados recebidos são inválidos.
        raise ValueError('Envie um arquivo PDF, JPG ou PNG.')

    # Atribui a variável 'destino' o resultado da expressão 'os.path.join(app.config['UPLOAD_FOLDER'], pasta)'.
    destino = os.path.join(app.config['UPLOAD_FOLDER'], pasta)
    # Atribui a variável 'os.makedirs(destino, exist_ok' o resultado da expressão 'True)'.
    os.makedirs(destino, exist_ok=True)
    # Atribui a variável 'nome_arquivo' o resultado da expressão 'f'{prefixo}_{identificador}{extensao}''.
    nome_arquivo = f'{prefixo}_{identificador}{extensao}'
    # Grava o arquivo recebido no caminho de destino calculado.
    arquivo.save(os.path.join(destino, nome_arquivo))
    # Retorna f'/arquivos/{pasta}/{nome_arquivo}'.
    return f'/arquivos/{pasta}/{nome_arquivo}'


# Define a função localizar_anexo, que localiza o anexo associado a um registro.
def localizar_anexo(pasta, prefixo, identificador):
    # Percorre extensao in EXTENSOES_PERMITIDAS.
    for extensao in EXTENSOES_PERMITIDAS:
        # Atribui a variável 'nome_arquivo' o resultado da expressão 'f'{prefixo}_{identificador}{extensao}''.
        nome_arquivo = f'{prefixo}_{identificador}{extensao}'
        # Atribui a variável 'caminho' o resultado da expressão 'os.path.join(app.config['UPLOAD_FOLDER'], pasta, nome_arquivo)'.
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], pasta, nome_arquivo)
        # Verifica se os.path.exists(caminho).
        if os.path.exists(caminho):
            # Retorna f'/arquivos/{pasta}/{nome_arquivo}'.
            return f'/arquivos/{pasta}/{nome_arquivo}'
    # Retorna ''.
    return ''


# Define a função verificar_senha, que valida a força mínima de uma senha.
def verificar_senha(senha):
    # Verifica se len(senha) < 10.
    if len(senha) < 10:
        # Retorna 'A senha deve ter no mínimo 10 caracteres'.
        return 'A senha deve ter no mínimo 10 caracteres'

    # Atribui a variável 'tem_maiuscula' o resultado da expressão 'False'.
    tem_maiuscula = False
    # Atribui a variável 'tem_minuscula' o resultado da expressão 'False'.
    tem_minuscula = False
    # Atribui a variável 'tem_numero' o resultado da expressão 'False'.
    tem_numero = False
    # Atribui a variável 'tem_simbolo' o resultado da expressão 'False'.
    tem_simbolo = False
    # Atribui a variável 'simbolos' o resultado da expressão ''!@'.
    simbolos = '!@#$%^&*()_+-=[]}{|;:,.<>?'

    # Percorre letra in senha.
    for letra in senha:
        # Verifica se letra.isupper().
        if letra.isupper():
            # Atribui a variável 'tem_maiuscula' o resultado da expressão 'True'.
            tem_maiuscula = True
        # Verifica a condição alternativa letra.islower().
        elif letra.islower():
            # Atribui a variável 'tem_minuscula' o resultado da expressão 'True'.
            tem_minuscula = True
        # Verifica a condição alternativa letra.isdigit().
        elif letra.isdigit():
            # Atribui a variável 'tem_numero' o resultado da expressão 'True'.
            tem_numero = True
        # Verifica a condição alternativa letra in simbolos.
        elif letra in simbolos:
            # Atribui a variável 'tem_simbolo' o resultado da expressão 'True'.
            tem_simbolo = True

    # Verifica se a condição tem_maiuscula é falsa.
    if not tem_maiuscula:
        # Retorna 'Falta uma letra maiúscula'.
        return 'Falta uma letra maiúscula'
    # Verifica se a condição tem_minuscula é falsa.
    if not tem_minuscula:
        # Retorna 'Falta uma letra minúscula'.
        return 'Falta uma letra minúscula'
    # Verifica se a condição tem_numero é falsa.
    if not tem_numero:
        # Retorna 'Falta um número'.
        return 'Falta um número'
    # Verifica se a condição tem_simbolo é falsa.
    if not tem_simbolo:
        # Retorna 'Falta um símbolo especial'.
        return 'Falta um símbolo especial'
    # Retorna None.
    return None


# Define a função gerar_token, que gera o token de autenticação do usuário.
def gerar_token(id_user):
    # Inicia o dicionário 'payload' que armazenará os dados da resposta.
    payload = {
        # Preenche o campo 'id_user' do objeto ou resposta que está sendo montado.
        'id_user': id_user,
        # Preenche o campo 'timestamp' do objeto ou resposta que está sendo montado.
        'timestamp': datetime.datetime.utcnow().isoformat(),
        # Preenche o campo 'exp' do objeto ou resposta que está sendo montado.
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5000)
    # Fecha o dicionário que está sendo montado.
    }
    # Retorna jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256').
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


# Define a função token_da_requisicao, que extrai o token de autenticação enviado na requisição.
def token_da_requisicao():
    # Atribui a variável 'token' o resultado da expressão 'request.cookies.get('access_token')'.
    token = request.cookies.get('access_token')
    # Verifica se token.
    if token:
        # Retorna token.
        return token

    # Atribui a variável 'autorizacao' o resultado da expressão 'request.headers.get('Authorization', '')'.
    autorizacao = request.headers.get('Authorization', '')
    # Verifica se autorizacao.startswith('Bearer ').
    if autorizacao.startswith('Bearer '):
        # Retorna autorizacao[7:].strip().
        return autorizacao[7:].strip()
    # Retorna None.
    return None


# Define a função id_usuario_logado, que identifica o usuário autenticado a partir do token.
def id_usuario_logado():
    # Atribui a variável 'token' o resultado da expressão 'token_da_requisicao()'.
    token = token_da_requisicao()
    # Verifica se a condição token é falsa.
    if not token:
        # Retorna None.
        return None
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Atribui a variável 'payload' o resultado da expressão 'jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])'.
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        # Retorna payload.get('id_user').
        return payload.get('id_user')
    # Captura o erro jwt.PyJWTError e permite tratá-lo.
    except jwt.PyJWTError:
        # Retorna None.
        return None


# Define a função usuario_e_administrador, que verifica se o usuário autenticado é administrador.
def usuario_e_administrador():
    # Atribui a variável 'id_usuario' o resultado da expressão 'id_usuario_logado()'.
    id_usuario = id_usuario_logado()
    # Verifica se a condição id_usuario é falsa.
    if not id_usuario:
        # Retorna False.
        return False
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Abre um cursor do banco e o armazena em 'cur'.
        cur = con.cursor()
        # Executa no banco a consulta SQL 'SELECT TIPO FROM USUARIO WHERE ID_USUARIO = ?'.
        cur.execute('SELECT TIPO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        # Obtém um valor do primeiro registro e o armazena em 'usuario'.
        usuario = cur.fetchone()
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()
        # Verifica se usuario and usuario[0] == 0.
        if usuario and usuario[0] == 0:
            # Retorna True.
            return True
        # Retorna False.
        return False
    # Captura o erro Exception e permite tratá-lo.
    except Exception:
        # Retorna False.
        return False


# Define a função usuario_pode_gerenciar_doacoes, que verifica se o usuário pode gerenciar os módulos protegidos.
def usuario_pode_gerenciar_doacoes():
    # Atribui a variável 'id_usuario' o resultado da expressão 'id_usuario_logado()'.
    id_usuario = id_usuario_logado()
    # Verifica se a condição id_usuario é falsa.
    if not id_usuario:
        # Retorna False.
        return False
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Abre um cursor do banco e o armazena em 'cur'.
        cur = con.cursor()
        # Executa no banco a consulta SQL 'SELECT TIPO FROM USUARIO WHERE ID_USUARIO = ?'.
        cur.execute('SELECT TIPO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        # Obtém um valor do primeiro registro e o armazena em 'usuario'.
        usuario = cur.fetchone()
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()
        # Verifica se usuario and usuario[0] in (0, 1).
        if usuario and usuario[0] in (0, 1):
            # Retorna True.
            return True
        # Retorna False.
        return False
    # Captura o erro Exception e permite tratá-lo.
    except Exception:
        # Retorna False.
        return False


# Define a função validar_doacao, que valida e normaliza os dados de uma doação.
def validar_doacao(dados, cur):
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Lê o campo solicitado da requisição e o armazena em 'id_projeto'.
        id_projeto = valor(dados, 'id_projeto')
        # Verifica se id_projeto.
        if id_projeto:
            # Converte o valor da expressão para inteiro e o armazena em 'id_projeto'.
            id_projeto = int(id_projeto)
        # Executa este bloco quando nenhuma condição anterior foi satisfeita.
        else:
            # Atribui a variável 'id_projeto' o resultado da expressão 'None'.
            id_projeto = None

        # Lê o campo solicitado da requisição e o armazena em 'doador'.
        doador = valor(dados, 'doador')
        # Lê o campo solicitado da requisição e o armazena em 'tipo'.
        tipo = converter_tipo(valor(dados, 'tipo'))
        # Lê o campo solicitado da requisição e o armazena em 'quantidade_texto'.
        quantidade_texto = valor(dados, 'quantidade')
        # Lê o campo solicitado da requisição e o armazena em 'valor_texto'.
        valor_texto = valor(dados, 'valor')
        # Atribui a variável 'quantidade' o resultado da expressão 'None'.
        quantidade = None
        # Atribui a variável 'valor_doacao' o resultado da expressão 'None'.
        valor_doacao = None
        # Verifica se quantidade_texto.
        if quantidade_texto:
            # Lê o campo solicitado da requisição e o armazena em 'quantidade'.
            quantidade = converter_valor(quantidade_texto)
        # Verifica se valor_texto.
        if valor_texto:
            # Lê o campo solicitado da requisição e o armazena em 'valor_doacao'.
            valor_doacao = converter_valor(valor_texto)

        # Lê o campo solicitado da requisição e o armazena em 'data_texto'.
        data_texto = valor(dados, 'data')
        # Verifica se a condição data_texto é falsa.
        if not data_texto:
            # Lê o campo solicitado da requisição e o armazena em 'data_texto'.
            data_texto = valor(dados, 'dia')
        # Atribui a variável 'data' o resultado da expressão 'converter_data(data_texto)'.
        data = converter_data(data_texto)
    # Captura o erro (TypeError, ValueError, InvalidOperation) e permite tratá-lo.
    except (TypeError, ValueError, InvalidOperation):
        # Retorna None, 'Doador, tipo, quantidade, valor e data devem ser válidos.'.
        return None, 'Doador, tipo, quantidade, valor e data devem ser válidos.'

    # Verifica se data >= datetime.date.today().
    if data >= datetime.date.today():
        # Retorna None, 'A data da doação deve ser anterior ao dia atual.'.
        return None, 'A data da doação deve ser anterior ao dia atual.'

    # Verifica se a condição doador é falsa.
    if not doador:
        # Retorna None, 'Doador é obrigatório.'.
        return None, 'Doador é obrigatório.'
    # Verifica se tipo not in (0, 1, 2, 3, 4).
    if tipo not in (0, 1, 2, 3, 4):
        # Retorna None, 'Tipo de doação inválido.'.
        return None, 'Tipo de doação inválido.'
    # Verifica se tipo == 0 and (valor_doacao is None or valor_doacao <= 0).
    if tipo == 0 and (valor_doacao is None or valor_doacao <= 0):
        # Retorna None, 'O valor da doação deve ser maior que zero.'.
        return None, 'O valor da doação deve ser maior que zero.'
    # Verifica se tipo in (1, 2, 3) and (quantidade is None or quantidade <= 0).
    if tipo in (1, 2, 3) and (quantidade is None or quantidade <= 0):
        # Retorna None, 'A quantidade da doação deve ser maior que zero.'.
        return None, 'A quantidade da doação deve ser maior que zero.'
    # Verifica se tipo == 4 and (quantidade is None or quantidade <= 0 or valor_doacao is None or valor_doacao <= 0).
    if tipo == 4 and (quantidade is None or quantidade <= 0 or valor_doacao is None or valor_doacao <= 0):
        # Retorna None, 'Quantidade e valor devem ser maiores que zero.'.
        return None, 'Quantidade e valor devem ser maiores que zero.'

    # Verifica se id_projeto is not None.
    if id_projeto is not None:
        # Executa no banco a consulta SQL 'SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?'.
        cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
        # Verifica se a condição cur.fetchone() é falsa.
        if not cur.fetchone():
            # Retorna None, 'Projeto não encontrado.'.
            return None, 'Projeto não encontrado.'

    # Inicia o dicionário 'doacao' que armazenará os dados da resposta.
    doacao = {
        # Preenche o campo 'id_projeto' do objeto ou resposta que está sendo montado.
        'id_projeto': id_projeto,
        # Preenche o campo 'doador' do objeto ou resposta que está sendo montado.
        'doador': doador,
        # Preenche o campo 'tipo' do objeto ou resposta que está sendo montado.
        'tipo': tipo,
        # Preenche o campo 'quantidade' do objeto ou resposta que está sendo montado.
        'quantidade': quantidade,
        # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
        'valor': valor_doacao,
        # Preenche o campo 'data' do objeto ou resposta que está sendo montado.
        'data': data,
        # Preenche o campo 'descricao' do objeto ou resposta que está sendo montado.
        'descricao': valor(dados, 'descricao')
    # Fecha o dicionário que está sendo montado.
    }
    # Retorna doacao, None.
    return doacao, None


# Define a função doacao_existe, que verifica se uma doação existe.
def doacao_existe(id_doacao, cur):
    # Executa no banco a consulta SQL 'SELECT ID_DOACAO FROM DOACAO WHERE ID_DOACAO = ?'.
    cur.execute('SELECT ID_DOACAO FROM DOACAO WHERE ID_DOACAO = ?', (id_doacao,))
    # Verifica se cur.fetchone().
    if cur.fetchone():
        # Retorna True.
        return True
    # Retorna False.
    return False


# Define a função produto_existe, que verifica se um produto existe.
def produto_existe(id_produto, cur):
    # Executa no banco a consulta SQL 'SELECT ID_PRODUTO FROM PRODUTO WHERE ID_PRODUTO = ?'.
    cur.execute('SELECT ID_PRODUTO FROM PRODUTO WHERE ID_PRODUTO = ?', (id_produto,))
    # Verifica se cur.fetchone().
    if cur.fetchone():
        # Retorna True.
        return True
    # Retorna False.
    return False


# Define a função validar_item_doacao, que valida os dados de um item de doação.
def validar_item_doacao(dados, cur):
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Lê o campo solicitado da requisição e o armazena em 'id_produto'.
        id_produto = int(valor(dados, 'id_produto'))
        # Lê o campo solicitado da requisição e o armazena em 'quantidade'.
        quantidade = int(valor(dados, 'quantidade'))
    # Captura o erro (TypeError, ValueError) e permite tratá-lo.
    except (TypeError, ValueError):
        # Retorna None, 'Produto e quantidade devem ser válidos.'.
        return None, 'Produto e quantidade devem ser válidos.'

    # Verifica se quantidade <= 0.
    if quantidade <= 0:
        # Retorna None, 'Quantidade deve ser maior que zero.'.
        return None, 'Quantidade deve ser maior que zero.'
    # Verifica se a condição produto_existe(id_produto, cur) é falsa.
    if not produto_existe(id_produto, cur):
        # Retorna None, 'Produto não encontrado.'.
        return None, 'Produto não encontrado.'
    # Retorna {'id_produto': id_produto, 'quantidade': quantidade}, None.
    return {'id_produto': id_produto, 'quantidade': quantidade}, None


# Define a função validar_emprestimo, que valida e normaliza os dados de um empréstimo.
def validar_emprestimo(dados, cur):
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Lê o campo solicitado da requisição e o armazena em 'id_projeto'.
        id_projeto = int(valor(dados, 'id_projeto'))
        # Lê o campo solicitado da requisição e o armazena em 'id_usuario_texto'.
        id_usuario_texto = valor(dados, 'id_usuario')
        # Atribui a variável 'id_usuario' o resultado da expressão 'None'.
        id_usuario = None
        # Verifica se id_usuario_texto.
        if id_usuario_texto:
            # Converte o valor da expressão para inteiro e o armazena em 'id_usuario'.
            id_usuario = int(id_usuario_texto)
        # Lê o campo solicitado da requisição e o armazena em 'finalidade'.
        finalidade = valor(dados, 'finalidade')
        # Lê o campo solicitado da requisição e o armazena em 'origem'.
        origem = valor(dados, 'origem')
        # Lê o campo solicitado da requisição e o armazena em 'valor_emprestimo'.
        valor_emprestimo = converter_valor(valor(dados, 'valor'))
        # Lê o campo solicitado da requisição e o armazena em 'parcelas'.
        parcelas = int(valor(dados, 'parcelas'))
        # Lê o campo solicitado da requisição e o armazena em 'data_texto'.
        data_texto = valor(dados, 'data')
        # Verifica se a condição data_texto é falsa.
        if not data_texto:
            # Lê o campo solicitado da requisição e o armazena em 'data_texto'.
            data_texto = valor(dados, 'dia')
        # Atribui a variável 'dia' o resultado da expressão 'converter_data(data_texto)'.
        dia = converter_data(data_texto)
        # Lê o campo solicitado da requisição e o armazena em 'devolucao'.
        devolucao = converter_data(valor(dados, 'devolucao'))
        # Lê o campo solicitado da requisição e o armazena em 'validade_texto'.
        validade_texto = valor(dados, 'validade')
        # Verifica se a condição validade_texto é falsa.
        if not validade_texto:
            # Lê o campo solicitado da requisição e o armazena em 'validade_texto'.
            validade_texto = valor(dados, 'vencimento')
        # Verifica se a condição validade_texto é falsa.
        if not validade_texto:
            # Lê o campo solicitado da requisição e o armazena em 'validade_texto'.
            validade_texto = valor(dados, 'devolucao')
        # Atribui a variável 'validade' o resultado da expressão 'converter_data(validade_texto)'.
        validade = converter_data(validade_texto)
    # Captura o erro (TypeError, ValueError, InvalidOperation) e permite tratá-lo.
    except (TypeError, ValueError, InvalidOperation):
        # Retorna None, 'Projeto, finalidade, origem, valor, parcelas e datas devem ser válidos.'.
        return None, 'Projeto, finalidade, origem, valor, parcelas e datas devem ser válidos.'

    # Atribui a variável 'hoje' o resultado da expressão 'datetime.date.today()'.
    hoje = datetime.date.today()
    # Verifica se dia > hoje.
    if dia > hoje:
        # Retorna None, 'A data do empréstimo não pode ser futura.'.
        return None, 'A data do empréstimo não pode ser futura.'
    # Verifica se devolucao < hoje.
    if devolucao < hoje:
        # Retorna None, 'A data de devolução não pode ser anterior ao dia atual.'.
        return None, 'A data de devolução não pode ser anterior ao dia atual.'
    # Verifica se a condição finalidade or not origem é falsa.
    if not finalidade or not origem:
        # Retorna None, 'Finalidade e origem são obrigatórias.'.
        return None, 'Finalidade e origem são obrigatórias.'
    # Verifica se valor_emprestimo <= 0 or parcelas <= 0.
    if valor_emprestimo <= 0 or parcelas <= 0:
        # Retorna None, 'Valor e parcelas devem ser maiores que zero.'.
        return None, 'Valor e parcelas devem ser maiores que zero.'
    # Verifica se validade < dia.
    if validade < dia:
        # Retorna None, 'A data de vencimento não pode ser anterior à data do empréstimo.'.
        return None, 'A data de vencimento não pode ser anterior à data do empréstimo.'

    # Executa no banco a consulta SQL 'SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?'.
    cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
    # Verifica se a condição cur.fetchone() é falsa.
    if not cur.fetchone():
        # Retorna None, 'Projeto não encontrado.'.
        return None, 'Projeto não encontrado.'
    # Verifica se id_usuario is not None.
    if id_usuario is not None:
        # Executa no banco a consulta SQL 'SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?'.
        cur.execute('SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        # Verifica se a condição cur.fetchone() é falsa.
        if not cur.fetchone():
            # Retorna None, 'Usuário não encontrado.'.
            return None, 'Usuário não encontrado.'

    # Inicia o dicionário 'emprestimo' que armazenará os dados da resposta.
    emprestimo = {
        # Preenche o campo 'id_projeto' do objeto ou resposta que está sendo montado.
        'id_projeto': id_projeto,
        # Preenche o campo 'id_usuario' do objeto ou resposta que está sendo montado.
        'id_usuario': id_usuario,
        # Preenche o campo 'finalidade' do objeto ou resposta que está sendo montado.
        'finalidade': finalidade,
        # Preenche o campo 'origem' do objeto ou resposta que está sendo montado.
        'origem': origem,
        # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
        'valor': valor_emprestimo,
        # Preenche o campo 'parcelas' do objeto ou resposta que está sendo montado.
        'parcelas': parcelas,
        # Preenche o campo 'dia' do objeto ou resposta que está sendo montado.
        'dia': dia,
        # Preenche o campo 'validade' do objeto ou resposta que está sendo montado.
        'validade': validade,
        # Preenche o campo 'devolucao' do objeto ou resposta que está sendo montado.
        'devolucao': devolucao
    # Fecha o dicionário que está sendo montado.
    }
    # Retorna emprestimo, None.
    return emprestimo, None


# Define a função emprestimo_existe, que verifica se um empréstimo existe.
def emprestimo_existe(id_emprestimo, cur):
    # Executa no banco a consulta SQL 'SELECT ID_EMPRESTIMO FROM EMPRESTIMO WHERE ID_EMPRESTIMO = ?'.
    cur.execute('SELECT ID_EMPRESTIMO FROM EMPRESTIMO WHERE ID_EMPRESTIMO = ?', (id_emprestimo,))
    # Verifica se cur.fetchone().
    if cur.fetchone():
        # Retorna True.
        return True
    # Retorna False.
    return False


# Define a função obter_categoria_lancamento, que localiza ou cria a categoria de um lançamento.
def obter_categoria_lancamento(dados, cur, tipo):
    # Lê o campo solicitado da requisição e o armazena em 'id_texto'.
    id_texto = valor(dados, 'id_categoria')
    # Lê o campo solicitado da requisição e o armazena em 'nome'.
    nome = valor(dados, 'categoria')

    # Verifica se id_texto.
    if id_texto:
        # Inicia um bloco protegido para capturar erros durante a operação.
        try:
            # Converte o valor da expressão para inteiro e o armazena em 'id_categoria'.
            id_categoria = int(id_texto)
        # Captura o erro (TypeError, ValueError) e permite tratá-lo.
        except (TypeError, ValueError):
            # Retorna None, 'Categoria inválida.'.
            return None, 'Categoria inválida.'
        # Executa no banco a consulta SQL 'SELECT ID_CATEGORIA FROM CATEGORIA WHERE ID_CATEGORIA = ? AND TIPO = ?'.
        cur.execute('SELECT ID_CATEGORIA FROM CATEGORIA WHERE ID_CATEGORIA = ? AND TIPO = ?', (id_categoria, tipo))
        # Verifica se a condição cur.fetchone() é falsa.
        if not cur.fetchone():
            # Retorna None, 'Categoria não encontrada.'.
            return None, 'Categoria não encontrada.'
        # Retorna id_categoria, None.
        return id_categoria, None

    # Verifica se a condição nome é falsa.
    if not nome:
        # Retorna None, None.
        return None, None
    # Verifica se tipo not in (0, 1).
    if tipo not in (0, 1):
        # Retorna None, 'Tipo de movimentação inválido.'.
        return None, 'Tipo de movimentação inválido.'

    # Inicia a execução da consulta ou comando SQL no banco de dados.
    cur.execute('''
        SELECT ID_CATEGORIA -- Inicia a seleção dos campos solicitados.
        FROM CATEGORIA -- Define a tabela CATEGORIA da consulta.
        WHERE UPPER(TRIM(NOME)) = UPPER(?) AND TIPO = ? -- Filtra os registros conforme a condição informada.
    ''', (nome, tipo))  # Fecha a string SQL usada pela consulta.
    # Obtém um valor do primeiro registro e o armazena em 'categoria'.
    categoria = cur.fetchone()
    # Verifica se categoria.
    if categoria:
        # Retorna categoria[0], None.
        return categoria[0], None

    # Inicia a execução da consulta ou comando SQL no banco de dados.
    cur.execute('''
        INSERT INTO CATEGORIA (NOME, STATUS, TIPO, DESCRICAO) -- Inicia a inclusão de um novo registro.
        VALUES (?, 0, ?, ?) -- Define os valores que serão gravados.
        RETURNING ID_CATEGORIA -- Solicita ao banco o identificador gerado.
    ''', (nome, tipo, 'Categoria criada pelo cadastro de movimentação.'))  # Fecha a string SQL usada pela consulta.
    # Retorna cur.fetchone()[0], None.
    return cur.fetchone()[0], None


# Define a função validar_lancamento, que valida e normaliza os dados de um lançamento financeiro.
def validar_lancamento(dados, cur, tipo=None):
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Atribui a variável 'id_categoria' o resultado da expressão 'None'.
        id_categoria = None
        # Lê o campo solicitado da requisição e o armazena em 'descricao'.
        descricao = valor(dados, 'descricao')
        # Lê o campo solicitado da requisição e o armazena em 'valor_lancamento'.
        valor_lancamento = converter_valor(valor(dados, 'valor'))
        # Lê o campo solicitado da requisição e o armazena em 'data_texto'.
        data_texto = valor(dados, 'data')
        # Verifica se a condição data_texto é falsa.
        if not data_texto:
            # Lê o campo solicitado da requisição e o armazena em 'data_texto'.
            data_texto = valor(dados, 'dia')
        # Atribui a variável 'data' o resultado da expressão 'converter_data(data_texto)'.
        data = converter_data(data_texto)

        # Atribui a variável 'vencimento' o resultado da expressão 'None'.
        vencimento = None
        # Verifica se valor(dados, 'vencimento').
        if valor(dados, 'vencimento'):
            # Lê o campo solicitado da requisição e o armazena em 'vencimento'.
            vencimento = converter_data(valor(dados, 'vencimento'))
        # Atribui a variável 'dia_inicio' o resultado da expressão 'None'.
        dia_inicio = None
        # Verifica se valor(dados, 'dia_inicio').
        if valor(dados, 'dia_inicio'):
            # Lê o campo solicitado da requisição e o armazena em 'dia_inicio'.
            dia_inicio = converter_data(valor(dados, 'dia_inicio'))
        # Atribui a variável 'dia_fim' o resultado da expressão 'None'.
        dia_fim = None
        # Verifica se valor(dados, 'dia_fim').
        if valor(dados, 'dia_fim'):
            # Lê o campo solicitado da requisição e o armazena em 'dia_fim'.
            dia_fim = converter_data(valor(dados, 'dia_fim'))

        # Atribui a variável 'conta' o resultado da expressão 'None'.
        conta = None
        # Verifica se valor(dados, 'conta').
        if valor(dados, 'conta'):
            # Lê o campo solicitado da requisição e o armazena em 'conta'.
            conta = int(valor(dados, 'conta'))
        # Verifica a condição alternativa tipo in (0, 1).
        elif tipo in (0, 1):
            # Atribui a variável 'conta' o resultado da expressão '0'.
            conta = 0
        # Verifica se conta not in (None, 0).
        if conta not in (None, 0):
            # Executa no banco a consulta SQL 'SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?'.
            cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (conta,))
            # Verifica se a condição cur.fetchone() é falsa.
            if not cur.fetchone():
                # Retorna None, 'Projeto ou local do valor inválido.'.
                return None, 'Projeto ou local do valor inválido.'
        # Lê o campo solicitado da requisição e o armazena em 'status'.
        status = int(valor(dados, 'status', '0') or '0')
        # Lê o campo solicitado da requisição e o armazena em 'recorrencia'.
        recorrencia = int(valor(dados, 'recorrencia', '0') or '0')
        # Atribui a variável 'intervalos_recorrencia' o resultado da expressão '{1: 15, 2: 30, 3: 1, 4: 7}'.
        intervalos_recorrencia = {1: 15, 2: 30, 3: 1, 4: 7}
        # Verifica se recorrencia != 0 and recorrencia not in intervalos_recorrencia.
        if recorrencia != 0 and recorrencia not in intervalos_recorrencia:
            # Retorna None, 'Recorrência inválida.'.
            return None, 'Recorrência inválida.'
        # Verifica se recorrencia != 0 and (dia_inicio is None or dia_fim is None).
        if recorrencia != 0 and (dia_inicio is None or dia_fim is None):
            # Retorna None, 'Informe as datas de início e fim para essa recorrência.'.
            return None, 'Informe as datas de início e fim para essa recorrência.'
        # Verifica se (dia_inicio is None) != (dia_fim is None).
        if (dia_inicio is None) != (dia_fim is None):
            # Retorna None, 'Informe as duas datas da recorrência.'.
            return None, 'Informe as duas datas da recorrência.'
        # Verifica se dia_inicio is not None and dia_fim is not None.
        if dia_inicio is not None and dia_fim is not None:
            # Atribui a variável 'diferenca_dias' o resultado da expressão '(dia_fim - dia_inicio).days'.
            diferenca_dias = (dia_fim - dia_inicio).days
            # Verifica se diferenca_dias <= 0.
            if diferenca_dias <= 0:
                # Retorna None, 'A data de fim deve ser posterior à data de início.'.
                return None, 'A data de fim deve ser posterior à data de início.'
            # Atribui a variável 'intervalo' o resultado da expressão 'intervalos_recorrencia.get(recorrencia, 0)'.
            intervalo = intervalos_recorrencia.get(recorrencia, 0)
            # Verifica se intervalo and diferenca_dias < intervalo.
            if intervalo and diferenca_dias < intervalo:
                # Retorna None, f'A data de fim deve respeitar pelo menos {intervalo} dias de recorrência.'.
                return None, f'A data de fim deve respeitar pelo menos {intervalo} dias de recorrência.'
        # Lê o campo solicitado da requisição e o armazena em 'forma_texto'.
        forma_texto = valor(dados, 'forma_pagamento')
        # Verifica se a condição forma_texto é falsa.
        if not forma_texto:
            # Retorna None, 'Forma de pagamento é obrigatória.'.
            return None, 'Forma de pagamento é obrigatória.'
        # Converte o valor da expressão para inteiro e o armazena em 'forma_pagamento'.
        forma_pagamento = int(forma_texto)
    # Captura o erro (TypeError, ValueError, InvalidOperation) e permite tratá-lo.
    except (TypeError, ValueError, InvalidOperation):
        # Retorna None, 'Descrição, valor e data devem ser válidos.'.
        return None, 'Descrição, valor e data devem ser válidos.'

    # Verifica se a condição descricao é falsa.
    if not descricao:
        # Retorna None, 'Descrição é obrigatória.'.
        return None, 'Descrição é obrigatória.'
    # Verifica se valor_lancamento <= 0.
    if valor_lancamento <= 0:
        # Retorna None, 'Valor deve ser maior que zero.'.
        return None, 'Valor deve ser maior que zero.'
    # Verifica se data > datetime.date.today().
    if data > datetime.date.today():
        # Retorna None, 'A data da movimentação não pode ser futura.'.
        return None, 'A data da movimentação não pode ser futura.'

    # Atribui a variável 'id_categoria, erro_categoria' o resultado da expressão 'obter_categoria_lancamento(dados, cur, tipo)'.
    id_categoria, erro_categoria = obter_categoria_lancamento(dados, cur, tipo)
    # Verifica se a validação retornou uma mensagem de erro.
    if erro_categoria:
        # Retorna None, erro_categoria.
        return None, erro_categoria

    # Inicia o dicionário 'lancamento' que armazenará os dados da resposta.
    lancamento = {
        # Preenche o campo 'id_categoria' do objeto ou resposta que está sendo montado.
        'id_categoria': id_categoria,
        # Preenche o campo 'descricao' do objeto ou resposta que está sendo montado.
        'descricao': descricao,
        # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
        'valor': valor_lancamento,
        # Preenche o campo 'data' do objeto ou resposta que está sendo montado.
        'data': data,
        # Preenche o campo 'vencimento' do objeto ou resposta que está sendo montado.
        'vencimento': vencimento,
        # Preenche o campo 'dia_inicio' do objeto ou resposta que está sendo montado.
        'dia_inicio': dia_inicio,
        # Preenche o campo 'dia_fim' do objeto ou resposta que está sendo montado.
        'dia_fim': dia_fim,
        # Preenche o campo 'conta' do objeto ou resposta que está sendo montado.
        'conta': conta,
        # Preenche o campo 'fornecedor' do objeto ou resposta que está sendo montado.
        'fornecedor': valor(dados, 'fornecedor'),
        # Preenche o campo 'status' do objeto ou resposta que está sendo montado.
        'status': status,
        # Preenche o campo 'recorrencia' do objeto ou resposta que está sendo montado.
        'recorrencia': recorrencia,
        # Preenche o campo 'origem' do objeto ou resposta que está sendo montado.
        'origem': valor(dados, 'origem'),
        # Preenche o campo 'forma_pagamento' do objeto ou resposta que está sendo montado.
        'forma_pagamento': forma_pagamento,
        # Preenche o campo 'observacao' do objeto ou resposta que está sendo montado.
        'observacao': valor(dados, 'observacao')
    # Fecha o dicionário que está sendo montado.
    }
    # Retorna lancamento, None.
    return lancamento, None


# Define a função listar_lancamentos, que consulta e organiza os lançamentos financeiros.
def listar_lancamentos(cur, tipo=None):
    # Atribui a variável 'sql' o resultado da expressão '''''.
    sql = '''
        SELECT L.ID_LIVRO_CAIXA, L.ID_CATEGORIA, C.NOME, L.DESCRICAO, -- Inicia a seleção dos campos solicitados.
               L.TIPO, L.VALOR, L.DIA, L.VENCIMENTO, L.FORNECEDOR, -- Continua a instrução SQL com os campos ou condições restantes.
               L.STATUS, L.RECORRENCIA, L.DIA_INICIO, L.DIA_FIM, -- Continua a instrução SQL com os campos ou condições restantes.
               L.CONTA, L.ORIGEM, L.FORMA_PAGAMENTO, L.OBSERVACAO -- Continua a instrução SQL com os campos ou condições restantes.
        FROM LIVRO_CAIXA L -- Define a tabela LIVRO_CAIXA da consulta.
        LEFT JOIN CATEGORIA C ON C.ID_CATEGORIA = L.ID_CATEGORIA -- Relaciona registros preservando também os que não possuem correspondência.
    '''  # Fecha a string SQL usada pela consulta.
    # Atribui a variável 'parametros' o resultado da expressão '()'.
    parametros = ()
    # Verifica se tipo is not None.
    if tipo is not None:
        # Atribui a variável 'sql +' o resultado da expressão '' WHERE L.TIPO = ?''.
        sql += ' WHERE L.TIPO = ?'
        # Atribui a variável 'parametros' o resultado da expressão '(tipo,)'.
        parametros = (tipo,)
    # Atribui a variável 'sql +' o resultado da expressão '' ORDER BY L.DIA DESC, L.ID_LIVRO_CAIXA DESC''.
    sql += ' ORDER BY L.DIA DESC, L.ID_LIVRO_CAIXA DESC'
    # Inicia a execução da consulta ou comando SQL no banco de dados.
    cur.execute(sql, parametros)

    # Inicializa a lista 'lancamentos' vazia.
    lancamentos = []
    # Percorre item in cur.fetchall().
    for item in cur.fetchall():
        # Inicia o dicionário 'lancamento' que armazenará os dados da resposta.
        lancamento = {
            # Preenche o campo 'id_livro_caixa' do objeto ou resposta que está sendo montado.
            'id_livro_caixa': item[0],
            # Preenche o campo 'id_categoria' do objeto ou resposta que está sendo montado.
            'id_categoria': item[1],
            # Preenche o campo 'categoria' do objeto ou resposta que está sendo montado.
            'categoria': texto_json(item[2]),
            # Preenche o campo 'descricao' do objeto ou resposta que está sendo montado.
            'descricao': texto_json(item[3]),
            # Preenche o campo 'tipo' do objeto ou resposta que está sendo montado.
            'tipo': item[4],
            # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
            'valor': numero_json(item[5]),
            # Preenche o campo 'data' do objeto ou resposta que está sendo montado.
            'data': data_json(item[6]),
            # Preenche o campo 'dia' do objeto ou resposta que está sendo montado.
            'dia': data_json(item[6]),
            # Preenche o campo 'vencimento' do objeto ou resposta que está sendo montado.
            'vencimento': data_json(item[7]),
            # Preenche o campo 'fornecedor' do objeto ou resposta que está sendo montado.
            'fornecedor': texto_json(item[8]),
            # Preenche o campo 'status' do objeto ou resposta que está sendo montado.
            'status': item[9],
            # Preenche o campo 'recorrencia' do objeto ou resposta que está sendo montado.
            'recorrencia': item[10],
            # Preenche o campo 'dia_inicio' do objeto ou resposta que está sendo montado.
            'dia_inicio': data_json(item[11]),
            # Preenche o campo 'dia_fim' do objeto ou resposta que está sendo montado.
            'dia_fim': data_json(item[12]),
            # Preenche o campo 'conta' do objeto ou resposta que está sendo montado.
            'conta': item[13],
            # Preenche o campo 'origem' do objeto ou resposta que está sendo montado.
            'origem': texto_json(item[14]),
            # Preenche o campo 'forma_pagamento' do objeto ou resposta que está sendo montado.
            'forma_pagamento': item[15],
            # Preenche o campo 'observacao' do objeto ou resposta que está sendo montado.
            'observacao': texto_json(item[16])
        # Fecha o dicionário que está sendo montado.
        }
        # Adiciona o item atual à lista acumulada.
        lancamentos.append(lancamento)
    # Retorna lancamentos.
    return lancamentos


# Define a função inserir_lancamento, que insere um lançamento no banco de dados.
def inserir_lancamento(cur, lancamento, tipo):
    # Inicia a execução da consulta ou comando SQL no banco de dados.
    cur.execute('''
        INSERT INTO LIVRO_CAIXA -- Inicia a inclusão de um novo registro.
            (ID_CATEGORIA, DESCRICAO, TIPO, VALOR, DIA, VENCIMENTO, -- Continua a instrução SQL com os campos ou condições restantes.
             FORNECEDOR, STATUS, RECORRENCIA, DIA_INICIO, DIA_FIM, CONTA, -- Continua a instrução SQL com os campos ou condições restantes.
             ORIGEM, FORMA_PAGAMENTO, OBSERVACAO) -- Continua a instrução SQL com os campos ou condições restantes.
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) -- Define os valores que serão gravados.
        RETURNING ID_LIVRO_CAIXA -- Solicita ao banco o identificador gerado.
    ''', (lancamento['id_categoria'], lancamento['descricao'], tipo,  # Fecha a string SQL usada pela consulta.
          # Passa o valor 'lancamento['valor'], lancamento['data'], lancamento['vencimento']' como argumento da operação atual.
          lancamento['valor'], lancamento['data'], lancamento['vencimento'],
          # Passa o valor 'lancamento['fornecedor'], lancamento['status'], lancamento['recorrencia']' como argumento da operação atual.
          lancamento['fornecedor'], lancamento['status'], lancamento['recorrencia'],
          # Passa o valor 'lancamento['dia_inicio'], lancamento['dia_fim'], lancamento['conta']' como argumento da operação atual.
          lancamento['dia_inicio'], lancamento['dia_fim'], lancamento['conta'],
          # Conclui a chamada anterior enviando os valores preparados para o banco.
          lancamento['origem'], lancamento['forma_pagamento'], lancamento['observacao']))
    # Retorna cur.fetchone()[0].
    return cur.fetchone()[0]


# Define a função inserir_entrada_automatica, que cria uma entrada gerada por doação ou empréstimo.
def inserir_entrada_automatica(cur, descricao, valor, data, vencimento, origem, observacao='Entrada criada automaticamente.', conta=0):
    if valor is None:
        valor = Decimal('0')
    lancamento = {
        'id_categoria': None,
        'descricao': descricao,
        'valor': valor,
        'data': data,
        'vencimento': vencimento,
        'fornecedor': '',
        'status': 1,
        'recorrencia': 0,
        'dia_inicio': None,
        'dia_fim': None,
        'conta': conta or 0,
        'origem': origem,
        'forma_pagamento': 0,
        'observacao': observacao
    }
    return inserir_lancamento(cur, lancamento, 0)


def sincronizar_entrada_doacao(cur, id_doacao, doacao, doacao_antiga=None):
    observacao = f'DOACAO:{id_doacao}'
    if doacao['tipo'] == 0:
        cur.execute('SELECT ID_LIVRO_CAIXA FROM LIVRO_CAIXA WHERE TIPO = 0 AND OBSERVACAO = ?', (observacao,))
        registro = cur.fetchone()
        if not registro and doacao_antiga:
            cur.execute('''
                SELECT ID_LIVRO_CAIXA
                FROM LIVRO_CAIXA
                WHERE TIPO = 0 AND DESCRICAO = 'Doação'
                  AND ORIGEM = ? AND DIA = ?
                  AND OBSERVACAO = 'Entrada criada automaticamente.'
            ''', (doacao_antiga[0], doacao_antiga[1]))
            registro = cur.fetchone()
        if registro:
            cur.execute('''
                UPDATE LIVRO_CAIXA
                SET VALOR = ?, DIA = ?, ORIGEM = ?, CONTA = ?, DESCRICAO = 'Doação'
                WHERE ID_LIVRO_CAIXA = ?
            ''', (doacao['valor'], doacao['data'], doacao['doador'], doacao['id_projeto'] or 0, registro[0]))
            return registro[0]
        return inserir_entrada_automatica(
            cur, 'Doação', doacao['valor'], doacao['data'], None,
            doacao['doador'], observacao, doacao['id_projeto'])

    cur.execute('DELETE FROM LIVRO_CAIXA WHERE TIPO = 0 AND OBSERVACAO = ?', (observacao,))
    return None


# Define a função editar_lancamento, que atualiza um lançamento existente.
def editar_lancamento(cur, id_lancamento, lancamento, tipo):
    # Inicia a execução da consulta ou comando SQL no banco de dados.
    cur.execute('''
        UPDATE LIVRO_CAIXA -- Inicia a atualização de um registro existente.
        SET ID_CATEGORIA = ?, DESCRICAO = ?, VALOR = ?, DIA = ?, VENCIMENTO = ?, -- Define os campos que receberão os novos valores.
            FORNECEDOR = ?, STATUS = ?, RECORRENCIA = ?, DIA_INICIO = ?, -- Continua a instrução SQL com os campos ou condições restantes.
            DIA_FIM = ?, CONTA = ?, ORIGEM = ?, FORMA_PAGAMENTO = ?, OBSERVACAO = ? -- Continua a instrução SQL com os campos ou condições restantes.
        WHERE ID_LIVRO_CAIXA = ? AND TIPO = ? -- Filtra os registros conforme a condição informada.
    ''', (lancamento['id_categoria'], lancamento['descricao'], lancamento['valor'],  # Fecha a string SQL usada pela consulta.
          # Passa o valor 'lancamento['data'], lancamento['vencimento'], lancamento['fornecedor']' como argumento da operação atual.
          lancamento['data'], lancamento['vencimento'], lancamento['fornecedor'],
          # Passa o valor 'lancamento['status'], lancamento['recorrencia'], lancamento['dia_inicio']' como argumento da operação atual.
          lancamento['status'], lancamento['recorrencia'], lancamento['dia_inicio'],
          # Passa o valor 'lancamento['dia_fim'], lancamento['conta'], lancamento['origem']' como argumento da operação atual.
          lancamento['dia_fim'], lancamento['conta'], lancamento['origem'],
          # Conclui a chamada anterior enviando os valores preparados para o banco.
          lancamento['forma_pagamento'], lancamento['observacao'], id_lancamento, tipo))


# Define a função excluir_lancamento, que remove um lançamento existente.
def excluir_lancamento(cur, id_lancamento, tipo):
    # Executa no banco a consulta SQL 'DELETE FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ? AND TIPO = ?'.
    cur.execute('DELETE FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ? AND TIPO = ?',
                # Conclui a chamada anterior enviando os valores preparados para o banco.
                (id_lancamento, tipo))


# Define a função tipo_lancamento, que consulta o tipo de um lançamento financeiro.
def tipo_lancamento(id_lancamento, cur):
    # Executa no banco a consulta SQL 'SELECT TIPO FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ?'.
    cur.execute('SELECT TIPO FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ?', (id_lancamento,))
    # Obtém um valor do primeiro registro e o armazena em 'registro'.
    registro = cur.fetchone()
    # Verifica se registro.
    if registro:
        # Retorna registro[0].
        return registro[0]
    # Retorna None.
    return None
