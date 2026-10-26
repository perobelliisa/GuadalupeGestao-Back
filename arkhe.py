"""Integração servidor a servidor. Não inicia o Flask nem abre o banco ao importar.

Em palavras simples: este arquivo é o mensageiro entre o Guadalupe e a Arkhé.
O Guadalupe envia pedidos por HTTPS, recebe as respostas e guarda no Firebird
o histórico das cobranças para saber o que já foi criado ou pago.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request
from uuid import UUID

from flask import jsonify, request


class ErroArkhe(Exception):
    def __init__(self, mensagem, status=502, definitivo=False):
        super().__init__(mensagem)
        self.status = status
        self.definitivo = definitivo


def carregar_config(pasta):
    # Primeiro procura os dados de acesso no ambiente do servidor. O arquivo
    # local é uma alternativa para desenvolvimento; senhas não ficam no código.
    caminho = Path(pasta) / 'arkhe.local.json'
    local = json.loads(caminho.read_text(encoding='utf-8-sig')) if caminho.exists() else {}
    return {
        'url': os.getenv('ARKHE_API_URL', local.get('url', 'https://arkhe-backend.zbbquj.easypanel.host')).rstrip('/'),
        'client_id': os.getenv('ARKHE_CLIENT_ID', local.get('client_id', '')),
        'client_secret': os.getenv('ARKHE_CLIENT_SECRET', local.get('client_secret', '')),
    }


class ClienteArkhe:
    def __init__(self, config):
        self.config = config
        self.integracao = sha256(config['client_id'].encode()).hexdigest()

    def chamar(self, caminho, dados=None):
        # Todas as conversas com a API passam por aqui. Assim usamos sempre a
        # mesma URL segura, enviamos as credenciais e tratamos erros da Arkhé.
        config = self.config
        if not config['client_id'] or not config['client_secret']:
            raise ErroArkhe('A integração Arkhé ainda não foi configurada no servidor.', 503, True)
        destino = urlparse(config['url'])
        if destino.scheme != 'https' or not destino.netloc or destino.username or destino.password:
            raise ErroArkhe('Configure uma URL HTTPS válida para a Arkhé no servidor.', 503, True)
        req = Request(config['url'] + caminho,
                      data=json.dumps(dados).encode() if dados is not None else None,
                      headers={'X-Client-ID': config['client_id'],
                               'X-Client-Secret': config['client_secret'],
                               'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            # Não segue redirecionamentos: eles poderiam encaminhar as credenciais a outro host.
            from urllib.request import HTTPRedirectHandler, build_opener

            class SemRedirecionamento(HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None

            with build_opener(SemRedirecionamento).open(req, timeout=15) as resposta:
                retorno = json.load(resposta)
            if not isinstance(retorno, dict):
                raise ValueError('JSON inesperado')
            return retorno
        except HTTPError as erro:
            mensagens = {400: 'A Arkhé recusou os dados da cobrança.',
                         401: 'As credenciais da Arkhé são inválidas.',
                         403: 'A integração Arkhé está desativada ou sem permissão.',
                         404: 'A cobrança não foi encontrada na Arkhé.'}
            mensagem = mensagens.get(erro.code, 'A Arkhé não concluiu a solicitação.')
            if erro.code in (400, 422):
                try:
                    corpo = json.loads(erro.read(8192))
                    detalhe = next((corpo.get(k) for k in ('mensagem', 'message', 'detail') if isinstance(corpo.get(k), str)), '') if isinstance(corpo, dict) else ''
                    detalhe = ' '.join(detalhe.split())
                    for segredo in (config['client_id'], config['client_secret']):
                        if segredo: detalhe = detalhe.replace(segredo, '[oculto]')
                    if detalhe and len(detalhe) <= 250 and not any(k in detalhe.lower() for k in ('client_secret', 'authorization', 'password')):
                        mensagem = 'Arkhé: ' + detalhe
                except (ValueError, OSError, TypeError):
                    pass
            if erro.code == 404 and caminho == '/api/v1/cobrancas/pix/qrcode':
                mensagem = 'O endpoint de geração de QR Code não está disponível na Arkhé. Confira a integração com o responsável pela API.'
            definitivo = erro.code in (400, 401, 403, 404, 422)
            raise ErroArkhe(mensagem, 422 if definitivo else 502, definitivo) from None
        except (URLError, OSError, ValueError):
            raise ErroArkhe('Não foi possível obter uma resposta válida da Arkhé. Consulte novamente mais tarde.') from None


def preparar_tabela(conexao):
    # Cria no Firebird uma tabela para guardar cada cobrança Pix e seu estado.
    cur = conexao.cursor()
    try:
        cur.execute("SELECT RDB$RELATION_NAME FROM RDB$RELATIONS WHERE RDB$RELATION_NAME = 'ARKHE_COBRANCA'")
        if not cur.fetchone():
            cur.execute('''CREATE TABLE ARKHE_COBRANCA (
                ID VARCHAR(36) NOT NULL PRIMARY KEY,
                INTEGRACAO VARCHAR(64) NOT NULL,
                ID_EXTERNO BIGINT UNIQUE,
                DOADOR VARCHAR(100) NOT NULL,
                VALOR NUMERIC(15,2) NOT NULL,
                ID_PROJETO INTEGER,
                DESCRICAO VARCHAR(500),
                CODIGO VARCHAR(2048),
                SITUACAO VARCHAR(16) NOT NULL,
                ID_DOACAO INTEGER UNIQUE,
                CRIADO_EM TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PAGO_EM TIMESTAMP,
                VALOR_LIVRE SMALLINT DEFAULT 0 NOT NULL,
                ERRO VARCHAR(300),
                FOREIGN KEY (ID_PROJETO) REFERENCES PROJETO (ID_PROJETO),
                FOREIGN KEY (ID_DOACAO) REFERENCES DOACAO (ID_DOACAO)
            )''')
        conexao.commit()
        cur.execute("SELECT RDB$FIELD_NAME FROM RDB$RELATION_FIELDS WHERE RDB$RELATION_NAME = 'ARKHE_COBRANCA' AND RDB$FIELD_NAME = 'VALOR_LIVRE'")
        if not cur.fetchone():
            cur.execute('ALTER TABLE ARKHE_COBRANCA ADD VALOR_LIVRE SMALLINT DEFAULT 0 NOT NULL')
        conexao.commit()
        cur.execute("SELECT RDB$FIELD_NAME FROM RDB$RELATION_FIELDS WHERE RDB$RELATION_NAME = 'ARKHE_COBRANCA' AND RDB$FIELD_NAME = 'ERRO'")
        if not cur.fetchone():
            cur.execute('ALTER TABLE ARKHE_COBRANCA ADD ERRO VARCHAR(300)')
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        cur.close()


COLUNAS = 'ID, ID_EXTERNO, DOADOR, VALOR, ID_PROJETO, DESCRICAO, CODIGO, SITUACAO, ID_DOACAO, CRIADO_EM, PAGO_EM, VALOR_LIVRE, ERRO'
CHAVES = ['id', 'id_cobranca', 'doador', 'valor', 'id_projeto', 'descricao', 'codigo_pagamento', 'situacao', 'id_doacao', 'criado_em', 'pago_em', 'valor_livre', 'motivo']


def serializar(linha):
    dados = dict(zip(CHAVES, linha))
    dados['valor'] = float(dados['valor'])
    dados['valor_livre'] = bool(dados['valor_livre'])
    if dados['valor_livre'] and dados['situacao'] != 'pago':
        dados['valor'] = None
    for chave in ('criado_em', 'pago_em'):
        if dados[chave] is not None:
            dados[chave] = str(dados[chave])
    return dados


def quantia(valor):
    try:
        resultado = Decimal(str(valor))
        if not resultado.is_finite() or resultado <= 0 or resultado > Decimal('999999999.99') or resultado != resultado.quantize(Decimal('.01')):
            raise ValueError()
        return resultado
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError('Informe um valor positivo com até duas casas decimais.') from None


def validar_dados(dados):
    if not isinstance(dados, dict):
        raise ValueError('Envie os dados da cobrança em um objeto JSON.')
    try:
        identificador = str(UUID(str(dados.get('id', ''))))
        livre = dados.get('valor_livre', False)
        if type(livre) is not bool or (livre and dados.get('valor') not in (None, '')):
            raise ValueError()
        valor = Decimal('0') if livre else quantia(dados.get('valor'))
        projeto = dados.get('id_projeto')
        projeto = int(str(projeto)) if projeto not in (None, '') else None
        if projeto is not None and projeto <= 0:
            raise ValueError()
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError('Informe um identificador válido e um valor positivo com até duas casas decimais.') from None
    doador = str(dados.get('doador') or '').strip()
    descricao = str(dados.get('descricao') or '').strip()
    if not doador or len(doador) > 100 or len(descricao) > 200:
        raise ValueError('Informe o doador (até 100 caracteres) e uma descrição de até 200 caracteres.')
    return identificador, doador, valor, projeto, descricao, livre


def registrar_arkhe(app, abrir_conexao, autorizado, sincronizar_entrada, cliente=None, acompanhar=None):
    # Registra as rotas HTTP que o restante do sistema usa para falar com a
    # Arkhé. Também recebe funções do Guadalupe para validar acesso e gravar
    # uma doação quando o pagamento for confirmado.
    cliente = cliente or ClienteArkhe(carregar_config(app.root_path))

    @contextmanager
    def transacao():
        conexao = abrir_conexao()
        cur = conexao.cursor()
        try:
            yield cur
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            cur.close()
            conexao.close()

    def buscar(cur, identificador):
        cur.execute(f'SELECT {COLUNAS} FROM ARKHE_COBRANCA WHERE ID = ? AND INTEGRACAO = ?',
                    (identificador, cliente.integracao))
        linha = cur.fetchone()
        return serializar(linha) if linha else None

    def protegida(funcao):
        @wraps(funcao)
        def executar(*args, **kwargs):
            if not autorizado():
                return jsonify(sucesso=False, mensagem='Acesso não autorizado.'), 403
            try:
                return funcao(*args, **kwargs)
            except ErroArkhe as erro:
                return jsonify(sucesso=False, mensagem=str(erro)), erro.status
            except ValueError as erro:
                return jsonify(sucesso=False, mensagem=str(erro)), 400
            except Exception:
                app.logger.error('Falha na integração Arkhé; nenhuma credencial foi registrada.')
                return jsonify(sucesso=False, mensagem='Não foi possível concluir a operação. Atualize as cobranças antes de tentar novamente.'), 503
        return executar

    @app.get('/integracoes/arkhe/conta')
    @protegida
    def conta_arkhe():
        # Busca na Arkhé qual conta vai receber o dinheiro. Mostramos apenas
        # os dados necessários para a pessoa conferir o destinatário.
        conta = cliente.chamar('/api/v1/conta')
        # Expõe somente os dados públicos necessários para confirmar a conta vinculada.
        return jsonify(sucesso=True, conta={k: conta.get(k) for k in ('id_conta', 'nome', 'banco')})

    @app.get('/integracoes/arkhe/cobrancas')
    @protegida
    def listar_cobrancas_arkhe():
        with transacao() as cur:
            cur.execute(f'SELECT {COLUNAS} FROM ARKHE_COBRANCA WHERE INTEGRACAO = ? ORDER BY CRIADO_EM DESC', (cliente.integracao,))
            cobrancas = [serializar(linha) for linha in cur.fetchall()]
        if acompanhar:
            for cobranca in cobrancas:
                if cobranca['situacao'] == 'pendente': acompanhar(cobranca)
        return jsonify(sucesso=True, cobrancas=cobrancas)

    @app.post('/integracoes/arkhe/cobrancas')
    @protegida
    def criar_cobranca_arkhe():
        # Recebe um pedido de cobrança, confere os dados e salva uma reserva
        # antes de chamar a Arkhé. Isso ajuda a não criar duas cobranças iguais.
        identificador, doador, valor, projeto, descricao, livre = validar_dados(request.get_json(silent=True))
        with transacao() as cur:
            existente = buscar(cur, identificador)
            if existente:
                valor_existente = Decimal('0') if existente['valor_livre'] else Decimal(str(existente['valor']))
                if (existente['doador'], valor_existente, existente['id_projeto'], existente['descricao'], existente['valor_livre']) != (doador, valor, projeto, descricao, livre):
                    return jsonify(sucesso=False, mensagem='Este identificador já pertence a outra cobrança.'), 409
                return jsonify(sucesso=True, cobranca=existente), 200
            if projeto:
                cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (projeto,))
                if not cur.fetchone():
                    raise ValueError('Projeto não encontrado.')
            # Confirma a reserva ANTES do POST externo. Repetir o ID nunca repete a cobrança bancária.
            cur.execute('''INSERT INTO ARKHE_COBRANCA (ID, INTEGRACAO, DOADOR, VALOR, ID_PROJETO, DESCRICAO, SITUACAO, VALOR_LIVRE)
                           VALUES (?, ?, ?, ?, ?, ?, 'criando', ?)''',
                        (identificador, cliente.integracao, doador, str(valor), projeto, descricao, int(livre)))
        try:
            resposta = cliente.chamar('/api/v1/cobrancas/pix/qrcode', {'valor_livre': True} if livre else {'valor': float(valor)})
            externo = resposta.get('id_cobranca')
            codigo = resposta.get('codigo_pagamento')
            if type(externo) is not int or externo <= 0 or not isinstance(codigo, str) or not 1 <= len(codigo) <= 2048:
                raise ErroArkhe('A Arkhé retornou uma cobrança incompleta. Confira com o banco antes de criar outra.')
            try:
                valor_retornado = Decimal(str(resposta.get('valor')))
            except InvalidOperation:
                valor_retornado = None
            if (livre and (resposta.get('valor_livre') is not True or resposta.get('valor') is not None)) or (not livre and valor_retornado != valor):
                raise ErroArkhe('O valor retornado pela Arkhé diverge da solicitação. Confira com o banco.')
        except ErroArkhe as erro:
            with transacao() as cur:
                cur.execute('UPDATE ARKHE_COBRANCA SET SITUACAO = ?, ERRO = ? WHERE ID = ? AND INTEGRACAO = ?',
                            ('falhou' if erro.definitivo else 'verificar', str(erro)[:300], identificador, cliente.integracao))
            raise
        with transacao() as cur:
            cur.execute("UPDATE ARKHE_COBRANCA SET ID_EXTERNO = ?, CODIGO = ?, SITUACAO = 'pendente' WHERE ID = ? AND INTEGRACAO = ?",
                        (externo, codigo, identificador, cliente.integracao))
            cobranca = buscar(cur, identificador)
        # Mesmo se a criação informar status pago, a consulta autenticada confirma o recebimento.
        if acompanhar: acompanhar(cobranca)
        return jsonify(sucesso=True, cobranca=cobranca), 201

    def conferir_pagamento(cobranca):
        # Pergunta à Arkhé se a cobrança está pendente ou se já foi paga.
        if not cobranca['id_cobranca']:
            raise ErroArkhe('A criação não foi confirmada. Confira a cobrança com a Arkhé antes de gerar outra.', 409)
        resposta = cliente.chamar(f"/api/v1/cobrancas/pix/{cobranca['id_cobranca']}")
        try:
            valor_pago = quantia(resposta.get('valor')) if resposta.get('status') == 1 else None
            consistente = (type(resposta.get('id_cobranca')) is int
                           and resposta['id_cobranca'] == cobranca['id_cobranca']
                           and (cobranca['valor_livre'] or Decimal(str(resposta.get('valor'))) == Decimal(str(cobranca['valor'])))
                           and type(resposta.get('status')) is int and resposta['status'] in (0, 1))
        except (InvalidOperation, ValueError):
            consistente = False
        if not consistente:
            raise ErroArkhe('A resposta da Arkhé não corresponde à cobrança solicitada.')
        return resposta, valor_pago

    @app.get('/integracoes/arkhe/cobrancas/<uuid:identificador>/status')
    @protegida
    def status_cobranca_arkhe(identificador):
        # Consulta somente: não cria doação, lançamento nem altera a cobrança.
        with transacao() as cur:
            cobranca = buscar(cur, str(identificador))
        if not cobranca:
            return jsonify(sucesso=False, mensagem='Cobrança não encontrada.'), 404
        situacao_registrada = cobranca['situacao']
        if situacao_registrada != 'pago':
            resposta, valor_pago = conferir_pagamento(cobranca)
            cobranca = {**cobranca, 'situacao': 'pago' if resposta['status'] == 1 else 'pendente'}
            if valor_pago is not None: cobranca['valor'] = float(valor_pago)
        return jsonify(sucesso=True, cobranca=cobranca,
                       situacao_registrada=situacao_registrada,
                       recebimento_registrado=bool(cobranca['id_doacao']),
                       fonte='registro_confirmado' if situacao_registrada == 'pago' else 'consulta_arkhe',
                       consultado_em=datetime.now(timezone.utc).isoformat())

    @app.post('/integracoes/arkhe/cobrancas/<uuid:identificador>/consultar')
    @protegida
    def consultar_cobranca_arkhe(identificador):
        cobranca = consultar_recebimento(str(identificador))
        if acompanhar: acompanhar(cobranca)
        return jsonify(sucesso=True, cobranca=cobranca)

    def consultar_recebimento(identificador):
        # Quando a Arkhé confirma o pagamento, registra a doação e a entrada
        # financeira no mesmo processo. Se já existe uma doação ligada a essa
        # cobrança, não cria outra.
        identificador = str(identificador)
        with transacao() as cur:
            cobranca = buscar(cur, identificador)
        if not cobranca:
            raise ErroArkhe('Cobrança não encontrada.', 404, True)
        if cobranca['situacao'] == 'pago':
            return cobranca
        resposta, valor_pago = conferir_pagamento(cobranca)
        if resposta['status'] == 0:
            return cobranca
        with transacao() as cur:
            # Obtém trava de escrita antes de reler e lançar: confirmação e recibo são atômicos.
            cur.execute('UPDATE ARKHE_COBRANCA SET SITUACAO = SITUACAO WHERE ID = ? AND INTEGRACAO = ?',
                        (identificador, cliente.integracao))
            atual = buscar(cur, identificador)
            if atual['id_doacao'] is None:
                agora = datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)
                dia = agora.date()
                cur.execute('''INSERT INTO DOACAO (ID_PROJETO, DOADOR, DIA, TIPO, VALOR, QUANTIDADE, DESCRICAO)
                               VALUES (?, ?, ?, 0, ?, NULL, ?) RETURNING ID_DOACAO''',
                            (atual['id_projeto'], atual['doador'], dia, str(valor_pago), atual['descricao']))
                id_doacao = cur.fetchone()[0]
                sincronizar_entrada(cur, id_doacao, {'tipo': 0, 'id_projeto': atual['id_projeto'],
                                    'doador': atual['doador'], 'data': dia, 'valor': valor_pago})
                cur.execute("UPDATE ARKHE_COBRANCA SET SITUACAO = 'pago', ID_DOACAO = ?, PAGO_EM = ?, VALOR = ? WHERE ID = ? AND INTEGRACAO = ?",
                            (id_doacao, agora, str(valor_pago), identificador, cliente.integracao))
            cobranca = buscar(cur, identificador)
        return cobranca

    return consultar_recebimento
