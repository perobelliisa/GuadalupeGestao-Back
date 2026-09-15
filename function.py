import datetime
import os
import unicodedata
from decimal import Decimal, InvalidOperation

import jwt
from flask import request
from werkzeug.utils import secure_filename

from main import app, con


EXTENSOES_PERMITIDAS = {'.pdf', '.jpg', '.jpeg', '.png'}


def dados_requisicao():
    if request.is_json:
        dados = request.get_json()
        if dados is None:
            return {}
        return dados
    return request.form


def valor(dados, nome, padrao=''):
    resposta = dados.get(nome)
    if resposta is None:
        resposta = padrao
    if resposta is None:
        return ''
    return str(resposta).strip()


def texto_sem_acento(texto):
    texto = unicodedata.normalize('NFKD', str(texto))
    resultado = ''
    for letra in texto:
        if not unicodedata.combining(letra):
            resultado += letra
    return resultado.strip().lower()


def converter_tipo(tipo):
    try:
        return int(tipo)
    except (TypeError, ValueError):
        tipos = {
            'dinheiro': 0,
            'produto': 1,
            'produtos': 1,
            'servico': 2,
            'servicos': 2
        }
        return tipos.get(texto_sem_acento(tipo))


def converter_valor(numero):
    texto = str(numero).strip().replace('R$', '').replace(' ', '')
    if ',' in texto:
        texto = texto.replace('.', '')
        texto = texto.replace(',', '.')
    return Decimal(texto)


def converter_data(data):
    texto = str(data).strip()
    try:
        if '-' in texto:
            partes = texto.split('-')
            ano = int(partes[0])
            mes = int(partes[1])
            dia = int(partes[2])
        else:
            partes = texto.split('/')
            dia = int(partes[0])
            mes = int(partes[1])
            ano = int(partes[2])
        return datetime.date(ano, mes, dia)
    except (TypeError, ValueError, IndexError):
        raise ValueError('Data inválida.')


def texto_json(texto):
    if texto is None:
        return ''
    return str(texto).strip()


def data_json(data):
    if data is None:
        return None
    return data.isoformat()


def numero_json(numero):
    if numero is None:
        return None
    return float(numero)


def ler_inteiro(numero, padrao=None):
    try:
        return int(numero)
    except (TypeError, ValueError):
        return padrao


def salvar_anexo(arquivo, pasta, prefixo, identificador):
    if not arquivo or not arquivo.filename:
        return None

    nome_original = secure_filename(arquivo.filename)
    extensao = os.path.splitext(nome_original)[1].lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise ValueError('Envie um arquivo PDF, JPG ou PNG.')

    destino = os.path.join(app.config['UPLOAD_FOLDER'], pasta)
    os.makedirs(destino, exist_ok=True)
    nome_arquivo = f'{prefixo}_{identificador}{extensao}'
    arquivo.save(os.path.join(destino, nome_arquivo))
    return f'/arquivos/{pasta}/{nome_arquivo}'


def localizar_anexo(pasta, prefixo, identificador):
    for extensao in EXTENSOES_PERMITIDAS:
        nome_arquivo = f'{prefixo}_{identificador}{extensao}'
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], pasta, nome_arquivo)
        if os.path.exists(caminho):
            return f'/arquivos/{pasta}/{nome_arquivo}'
    return ''


def verificar_senha(senha):
    if len(senha) < 10:
        return 'A senha deve ter no mínimo 10 caracteres'

    tem_maiuscula = False
    tem_minuscula = False
    tem_numero = False
    tem_simbolo = False
    simbolos = '!@#$%^&*()_+-=[]}{|;:,.<>?'

    for letra in senha:
        if letra.isupper():
            tem_maiuscula = True
        elif letra.islower():
            tem_minuscula = True
        elif letra.isdigit():
            tem_numero = True
        elif letra in simbolos:
            tem_simbolo = True

    if not tem_maiuscula:
        return 'Falta uma letra maiúscula'
    if not tem_minuscula:
        return 'Falta uma letra minúscula'
    if not tem_numero:
        return 'Falta um número'
    if not tem_simbolo:
        return 'Falta um símbolo especial'
    return None


def gerar_token(id_user):
    payload = {
        'id_user': id_user,
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=5000)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def token_da_requisicao():
    token = request.cookies.get('access_token')
    if token:
        return token

    autorizacao = request.headers.get('Authorization', '')
    if autorizacao.startswith('Bearer '):
        return autorizacao[7:].strip()
    return None


def id_usuario_logado():
    token = token_da_requisicao()
    if not token:
        return None
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload.get('id_user')
    except jwt.PyJWTError:
        return None


def usuario_e_administrador():
    id_usuario = id_usuario_logado()
    if not id_usuario:
        return False
    try:
        cur = con.cursor()
        cur.execute('SELECT TIPO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        usuario = cur.fetchone()
        cur.close()
        if usuario and usuario[0] == 0:
            return True
        return False
    except Exception:
        return False


def usuario_pode_gerenciar_doacoes():
    id_usuario = id_usuario_logado()
    if not id_usuario:
        return False
    try:
        cur = con.cursor()
        cur.execute('SELECT TIPO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        usuario = cur.fetchone()
        cur.close()
        if usuario and usuario[0] in (0, 1):
            return True
        return False
    except Exception:
        return False


def validar_doacao(dados, cur):
    try:
        id_projeto = valor(dados, 'id_projeto')
        if id_projeto:
            id_projeto = int(id_projeto)
        else:
            id_projeto = None

        doador = valor(dados, 'doador')
        tipo = converter_tipo(valor(dados, 'tipo'))
        quantidade_texto = valor(dados, 'quantidade')
        valor_texto = valor(dados, 'valor')
        quantidade = None
        valor_doacao = None
        if quantidade_texto:
            quantidade = converter_valor(quantidade_texto)
        if valor_texto:
            valor_doacao = converter_valor(valor_texto)

        data_texto = valor(dados, 'data')
        if not data_texto:
            data_texto = valor(dados, 'dia')
        data = converter_data(data_texto)
    except (TypeError, ValueError, InvalidOperation):
        return None, 'Doador, tipo, quantidade, valor e data devem ser válidos.'

    if data >= datetime.date.today():
        return None, 'A data da doação deve ser anterior ao dia atual.'

    if not doador:
        return None, 'Doador é obrigatório.'
    if tipo not in (0, 1, 2, 3, 4):
        return None, 'Tipo de doação inválido.'
    if tipo == 0 and (valor_doacao is None or valor_doacao <= 0):
        return None, 'O valor da doação deve ser maior que zero.'
    if tipo in (1, 2, 3) and (quantidade is None or quantidade <= 0):
        return None, 'A quantidade da doação deve ser maior que zero.'
    if tipo == 4 and (quantidade is None or quantidade <= 0 or valor_doacao is None or valor_doacao <= 0):
        return None, 'Quantidade e valor devem ser maiores que zero.'

    if id_projeto is not None:
        cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
        if not cur.fetchone():
            return None, 'Projeto não encontrado.'

    doacao = {
        'id_projeto': id_projeto,
        'doador': doador,
        'tipo': tipo,
        'quantidade': quantidade,
        'valor': valor_doacao,
        'data': data,
        'descricao': valor(dados, 'descricao')
    }
    return doacao, None


def doacao_existe(id_doacao, cur):
    cur.execute('SELECT ID_DOACAO FROM DOACAO WHERE ID_DOACAO = ?', (id_doacao,))
    if cur.fetchone():
        return True
    return False


def produto_existe(id_produto, cur):
    cur.execute('SELECT ID_PRODUTO FROM PRODUTO WHERE ID_PRODUTO = ?', (id_produto,))
    if cur.fetchone():
        return True
    return False


def validar_item_doacao(dados, cur):
    try:
        id_produto = int(valor(dados, 'id_produto'))
        quantidade = int(valor(dados, 'quantidade'))
    except (TypeError, ValueError):
        return None, 'Produto e quantidade devem ser válidos.'

    if quantidade <= 0:
        return None, 'Quantidade deve ser maior que zero.'
    if not produto_existe(id_produto, cur):
        return None, 'Produto não encontrado.'
    return {'id_produto': id_produto, 'quantidade': quantidade}, None


def validar_emprestimo(dados, cur):
    try:
        id_projeto = int(valor(dados, 'id_projeto'))
        id_usuario_texto = valor(dados, 'id_usuario')
        id_usuario = None
        if id_usuario_texto:
            id_usuario = int(id_usuario_texto)
        finalidade = valor(dados, 'finalidade')
        origem = valor(dados, 'origem')
        valor_emprestimo = converter_valor(valor(dados, 'valor'))
        parcelas = int(valor(dados, 'parcelas'))
        data_texto = valor(dados, 'data')
        if not data_texto:
            data_texto = valor(dados, 'dia')
        dia = converter_data(data_texto)
        devolucao = converter_data(valor(dados, 'devolucao'))
        validade_texto = valor(dados, 'validade')
        if not validade_texto:
            validade_texto = valor(dados, 'vencimento')
        if not validade_texto:
            validade_texto = valor(dados, 'devolucao')
        validade = converter_data(validade_texto)
    except (TypeError, ValueError, InvalidOperation):
        return None, 'Projeto, finalidade, origem, valor, parcelas e datas devem ser válidos.'

    hoje = datetime.date.today()
    if dia > hoje:
        return None, 'A data do empréstimo não pode ser futura.'
    if devolucao < hoje:
        return None, 'A data de devolução não pode ser anterior ao dia atual.'
    if not finalidade or not origem:
        return None, 'Finalidade e origem são obrigatórias.'
    if valor_emprestimo <= 0 or parcelas <= 0:
        return None, 'Valor e parcelas devem ser maiores que zero.'
    if validade < dia:
        return None, 'A data de vencimento não pode ser anterior à data do empréstimo.'

    cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
    if not cur.fetchone():
        return None, 'Projeto não encontrado.'
    if id_usuario is not None:
        cur.execute('SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
        if not cur.fetchone():
            return None, 'Usuário não encontrado.'

    emprestimo = {
        'id_projeto': id_projeto,
        'id_usuario': id_usuario,
        'finalidade': finalidade,
        'origem': origem,
        'valor': valor_emprestimo,
        'parcelas': parcelas,
        'dia': dia,
        'validade': validade,
        'devolucao': devolucao
    }
    return emprestimo, None


def emprestimo_existe(id_emprestimo, cur):
    cur.execute('SELECT ID_EMPRESTIMO FROM EMPRESTIMO WHERE ID_EMPRESTIMO = ?', (id_emprestimo,))
    if cur.fetchone():
        return True
    return False


def validar_lancamento(dados, cur):
    try:
        id_categoria = None
        if valor(dados, 'id_categoria'):
            id_categoria = int(valor(dados, 'id_categoria'))
        descricao = valor(dados, 'descricao')
        valor_lancamento = converter_valor(valor(dados, 'valor'))
        data_texto = valor(dados, 'data')
        if not data_texto:
            data_texto = valor(dados, 'dia')
        data = converter_data(data_texto)

        vencimento = None
        if valor(dados, 'vencimento'):
            vencimento = converter_data(valor(dados, 'vencimento'))
        dia_inicio = None
        if valor(dados, 'dia_inicio'):
            dia_inicio = converter_data(valor(dados, 'dia_inicio'))
        dia_fim = None
        if valor(dados, 'dia_fim'):
            dia_fim = converter_data(valor(dados, 'dia_fim'))

        conta = None
        if valor(dados, 'conta'):
            conta = int(valor(dados, 'conta'))
        status = int(valor(dados, 'status', '0'))
        recorrencia = int(valor(dados, 'recorrencia', '0'))
        forma_pagamento = int(valor(dados, 'forma_pagamento', '0'))
    except (TypeError, ValueError, InvalidOperation):
        return None, 'Descrição, valor e data devem ser válidos.'

    if not descricao:
        return None, 'Descrição é obrigatória.'
    if valor_lancamento <= 0:
        return None, 'Valor deve ser maior que zero.'

    lancamento = {
        'id_categoria': id_categoria,
        'descricao': descricao,
        'valor': valor_lancamento,
        'data': data,
        'vencimento': vencimento,
        'dia_inicio': dia_inicio,
        'dia_fim': dia_fim,
        'conta': conta,
        'fornecedor': valor(dados, 'fornecedor'),
        'status': status,
        'recorrencia': recorrencia,
        'origem': valor(dados, 'origem'),
        'forma_pagamento': forma_pagamento,
        'observacao': valor(dados, 'observacao')
    }
    return lancamento, None


def listar_lancamentos(cur, tipo=None):
    sql = '''
        SELECT L.ID_LIVRO_CAIXA, L.ID_CATEGORIA, C.NOME, L.DESCRICAO,
               L.TIPO, L.VALOR, L.DIA, L.VENCIMENTO, L.FORNECEDOR,
               L.STATUS, L.RECORRENCIA, L.DIA_INICIO, L.DIA_FIM,
               L.CONTA, L.ORIGEM, L.FORMA_PAGAMENTO, L.OBSERVACAO
        FROM LIVRO_CAIXA L
        LEFT JOIN CATEGORIA C ON C.ID_CATEGORIA = L.ID_CATEGORIA
    '''
    parametros = ()
    if tipo is not None:
        sql += ' WHERE L.TIPO = ?'
        parametros = (tipo,)
    sql += ' ORDER BY L.DIA DESC, L.ID_LIVRO_CAIXA DESC'
    cur.execute(sql, parametros)

    lancamentos = []
    for item in cur.fetchall():
        lancamento = {
            'id_livro_caixa': item[0],
            'id_categoria': item[1],
            'categoria': texto_json(item[2]),
            'descricao': texto_json(item[3]),
            'tipo': item[4],
            'valor': numero_json(item[5]),
            'data': data_json(item[6]),
            'dia': data_json(item[6]),
            'vencimento': data_json(item[7]),
            'fornecedor': texto_json(item[8]),
            'status': item[9],
            'recorrencia': item[10],
            'dia_inicio': data_json(item[11]),
            'dia_fim': data_json(item[12]),
            'conta': item[13],
            'origem': texto_json(item[14]),
            'forma_pagamento': item[15],
            'observacao': texto_json(item[16])
        }
        lancamentos.append(lancamento)
    return lancamentos


def inserir_lancamento(cur, lancamento, tipo):
    cur.execute('''
        INSERT INTO LIVRO_CAIXA
            (ID_CATEGORIA, DESCRICAO, TIPO, VALOR, DIA, VENCIMENTO,
             FORNECEDOR, STATUS, RECORRENCIA, DIA_INICIO, DIA_FIM, CONTA,
             ORIGEM, FORMA_PAGAMENTO, OBSERVACAO)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING ID_LIVRO_CAIXA
    ''', (lancamento['id_categoria'], lancamento['descricao'], tipo,
          lancamento['valor'], lancamento['data'], lancamento['vencimento'],
          lancamento['fornecedor'], lancamento['status'], lancamento['recorrencia'],
          lancamento['dia_inicio'], lancamento['dia_fim'], lancamento['conta'],
          lancamento['origem'], lancamento['forma_pagamento'], lancamento['observacao']))
    return cur.fetchone()[0]


def editar_lancamento(cur, id_lancamento, lancamento, tipo):
    cur.execute('''
        UPDATE LIVRO_CAIXA
        SET ID_CATEGORIA = ?, DESCRICAO = ?, VALOR = ?, DIA = ?, VENCIMENTO = ?,
            FORNECEDOR = ?, STATUS = ?, RECORRENCIA = ?, DIA_INICIO = ?,
            DIA_FIM = ?, CONTA = ?, ORIGEM = ?, FORMA_PAGAMENTO = ?, OBSERVACAO = ?
        WHERE ID_LIVRO_CAIXA = ? AND TIPO = ?
    ''', (lancamento['id_categoria'], lancamento['descricao'], lancamento['valor'],
          lancamento['data'], lancamento['vencimento'], lancamento['fornecedor'],
          lancamento['status'], lancamento['recorrencia'], lancamento['dia_inicio'],
          lancamento['dia_fim'], lancamento['conta'], lancamento['origem'],
          lancamento['forma_pagamento'], lancamento['observacao'], id_lancamento, tipo))


def excluir_lancamento(cur, id_lancamento, tipo):
    cur.execute('DELETE FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ? AND TIPO = ?',
                (id_lancamento, tipo))


def tipo_lancamento(id_lancamento, cur):
    cur.execute('SELECT TIPO FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ?', (id_lancamento,))
    registro = cur.fetchone()
    if registro:
        return registro[0]
    return None
