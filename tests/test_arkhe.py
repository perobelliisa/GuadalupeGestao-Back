"""Usa SQLite temporário e uma Arkhé falsa; nunca acessa contas ou bancos reais."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
import json
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from urllib.error import HTTPError, URLError

from flask import Flask
from arkhe import ClienteArkhe, ErroArkhe, registrar_arkhe, validar_dados

sqlite3.register_adapter(date, lambda valor: valor.isoformat())
sqlite3.register_adapter(datetime, lambda valor: valor.isoformat())


class BancoFalso:
    integracao = 'integracao-teste'

    def __init__(self):
        self.chamadas = []
        self.pago = False
        self.erro = None
        self.valor = 25.5
        self.livre = False

    def chamar(self, caminho, dados=None):
        self.chamadas.append((caminho, dados))
        if self.erro:
            raise self.erro
        if caminho.endswith('/conta'):
            return {'id_conta': 9, 'nome': 'Conta teste', 'banco': 'Arkhé', 'client_secret': 'nao-expor'}
        if dados is not None:
            self.livre = dados.get('valor_livre', False)
        return {'id_cobranca': 123, 'valor': None if self.livre and not self.pago else self.valor,
                'valor_livre': self.livre, 'codigo_pagamento': 'ARKHEPIX:TESTE', 'status': int(self.pago)}


class ArkheTest(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / 'teste.sqlite'
        with closing(self.abrir()) as db:
            db.executescript('''
                CREATE TABLE PROJETO (ID_PROJETO INTEGER PRIMARY KEY);
                INSERT INTO PROJETO VALUES (1);
                CREATE TABLE DOACAO (ID_DOACAO INTEGER PRIMARY KEY, ID_PROJETO INTEGER, DOADOR TEXT,
                    DIA DATE, TIPO INTEGER, VALOR NUMERIC, QUANTIDADE NUMERIC, DESCRICAO TEXT);
                CREATE TABLE LIVRO_CAIXA (ID_LIVRO_CAIXA INTEGER PRIMARY KEY, ID_DOACAO INTEGER UNIQUE, VALOR NUMERIC);
                CREATE TABLE ARKHE_COBRANCA (ID TEXT PRIMARY KEY, INTEGRACAO TEXT, ID_EXTERNO INTEGER UNIQUE,
                    DOADOR TEXT, VALOR NUMERIC, ID_PROJETO INTEGER, DESCRICAO TEXT, CODIGO TEXT,
                    SITUACAO TEXT, ID_DOACAO INTEGER UNIQUE, CRIADO_EM TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PAGO_EM TIMESTAMP,
                    VALOR_LIVRE INTEGER NOT NULL DEFAULT 0, ERRO TEXT);
            ''')
        self.banco = BancoFalso()
        self.permitido = True
        self.falhar_livro = False
        self.payload = {'id': str(uuid4()), 'doador': 'Doador de teste', 'valor': 25.5, 'id_projeto': 1, 'descricao': 'Campanha'}
        self.app = Flask(__name__)
        registrar_arkhe(self.app, self.abrir, lambda: self.permitido, self.lancar, self.banco)
        self.client = self.app.test_client()

    def tearDown(self):
        self.pasta.cleanup()

    def abrir(self):
        return sqlite3.connect(self.caminho, timeout=10)

    def lancar(self, cur, id_doacao, dados):
        if self.falhar_livro:
            raise RuntimeError('Falha simulada')
        cur.execute('INSERT INTO LIVRO_CAIXA (ID_DOACAO, VALOR) VALUES (?, ?)', (id_doacao, str(dados['valor'])))

    def criar(self, dados=None):
        return self.client.post('/integracoes/arkhe/cobrancas', json=self.payload if dados is None else dados)

    def consultar(self, client=None):
        return (client or self.client).post(f"/integracoes/arkhe/cobrancas/{self.payload['id']}/consultar")

    def contagens(self):
        with closing(self.abrir()) as db:
            return tuple(db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('DOACAO', 'LIVRO_CAIXA'))

    def test_pendente_nao_lanca_e_pagamento_lanca_uma_vez(self):
        self.assertEqual(self.criar().status_code, 201)
        self.assertEqual(self.consultar().json['cobranca']['situacao'], 'pendente')
        self.assertEqual(self.contagens(), (0, 0))
        self.banco.pago = True
        self.assertEqual(self.consultar().json['cobranca']['situacao'], 'pago')
        self.assertEqual(self.consultar().status_code, 200)
        self.assertEqual(self.contagens(), (1, 1))
        with closing(self.abrir()) as db:
            self.assertEqual(db.execute('SELECT DOADOR, ID_PROJETO, VALOR FROM DOACAO').fetchone(), ('Doador de teste', 1, 25.5))

    def test_repetir_criacao_nao_repete_post_externo(self):
        self.criar()
        self.assertEqual(self.criar().status_code, 200)
        self.assertEqual(len(self.banco.chamadas), 1)
        self.assertEqual(self.criar({**self.payload, 'valor': 99}).status_code, 409)

    def test_timeout_nao_repete_cobranca_bancaria(self):
        self.banco.erro = ErroArkhe('Timeout')
        self.assertEqual(self.criar().status_code, 502)
        self.assertEqual(self.criar().json['cobranca']['situacao'], 'verificar')
        self.assertEqual(len(self.banco.chamadas), 1)
        self.assertEqual(self.consultar().status_code, 409)
        self.assertEqual(self.contagens(), (0, 0))

    def test_recusa_definitiva(self):
        self.banco.erro = ErroArkhe('Credenciais inválidas', definitivo=True)
        self.criar()
        self.assertEqual(self.criar().json['cobranca']['situacao'], 'falhou')
        self.assertEqual(self.criar().json['cobranca']['motivo'], 'Credenciais inválidas')

    def test_valor_divergente_nao_lanca(self):
        self.criar()
        self.banco.pago, self.banco.valor = True, 100
        self.assertEqual(self.consultar().status_code, 502)
        self.assertEqual(self.contagens(), (0, 0))

    def usar_valor_livre(self):
        self.payload.pop('valor', None)
        self.payload['valor_livre'] = True

    def test_valor_livre_so_registra_quantia_efetivamente_paga(self):
        self.usar_valor_livre()
        resposta = self.criar()
        self.assertEqual(resposta.status_code, 201)
        self.assertTrue(resposta.json['cobranca']['valor_livre'])
        self.assertIsNone(resposta.json['cobranca']['valor'])
        self.assertEqual(self.banco.chamadas[-1], ('/api/v1/cobrancas/pix/qrcode', {'valor_livre': True}))
        self.assertIsNone(self.consultar().json['cobranca']['valor'])
        self.assertEqual(self.contagens(), (0, 0))
        self.banco.pago, self.banco.valor = True, 73.49
        self.assertEqual(self.consultar().json['cobranca']['valor'], 73.49)
        self.assertEqual(self.consultar().status_code, 200)
        with closing(self.abrir()) as db:
            self.assertEqual(db.execute('SELECT VALOR FROM DOACAO').fetchone()[0], 73.49)
            self.assertEqual(db.execute('SELECT VALOR FROM LIVRO_CAIXA').fetchone()[0], 73.49)
        self.assertEqual(self.contagens(), (1, 1))
        # Mesmo após preencher a quantia recebida, recuperar o pedido não cria outra cobrança.
        self.assertEqual(self.criar().json['cobranca']['valor'], 73.49)
        self.assertEqual(sum(dados is not None for _, dados in self.banco.chamadas), 1)

    def test_valor_livre_recusa_quantia_paga_invalida(self):
        self.usar_valor_livre()
        self.criar()
        self.banco.pago = True
        for quantia in (None, 0, -1, 'NaN', 'Infinity', '10.001'):
            self.banco.valor = quantia
            self.assertEqual(self.consultar().status_code, 502)
            self.assertEqual(self.contagens(), (0, 0))

    def test_modos_inconsistentes_nao_criam_cobranca(self):
        self.assertEqual(self.criar({**self.payload, 'valor_livre': True}).status_code, 400)
        self.assertEqual(self.criar({**self.payload, 'valor_livre': 'true'}).status_code, 400)
        self.assertEqual(self.banco.chamadas, [])

    def test_modo_nao_pode_mudar_ao_repetir_identificador(self):
        self.criar()
        self.usar_valor_livre()
        self.assertEqual(self.criar().status_code, 409)
        self.assertEqual(len(self.banco.chamadas), 1)

    def test_resposta_invalida_na_criacao_fica_para_verificar(self):
        self.banco.valor = None
        self.assertEqual(self.criar().status_code, 502)
        self.assertEqual(self.criar().json['cobranca']['situacao'], 'verificar')

    def test_falha_no_livro_reverte_doacao_e_permite_reconsultar(self):
        self.criar()
        self.banco.pago, self.falhar_livro = True, True
        self.assertEqual(self.consultar().status_code, 503)
        self.assertEqual(self.contagens(), (0, 0))
        self.falhar_livro = False
        self.assertEqual(self.consultar().status_code, 200)
        self.assertEqual(self.contagens(), (1, 1))

    def test_persistencia_ao_reabrir_e_consultas_simultaneas(self):
        self.criar()
        self.banco.pago = True
        with ThreadPoolExecutor(max_workers=2) as pool:
            respostas = list(pool.map(lambda _: self.consultar(self.app.test_client()).status_code, range(2)))
        self.assertTrue(all(c in (200, 503) for c in respostas))
        self.assertEqual(self.contagens(), (1, 1))
        novo_app = Flask('reaberto')
        registrar_arkhe(novo_app, self.abrir, lambda: True, self.lancar, self.banco)
        self.assertEqual(novo_app.test_client().get('/integracoes/arkhe/cobrancas').json['cobrancas'][0]['situacao'], 'pago')

    def test_rotas_exigem_permissao(self):
        self.permitido = False
        self.assertEqual(self.criar().status_code, 403)
        self.assertEqual(self.consultar().status_code, 403)
        self.assertEqual(self.client.get('/integracoes/arkhe/cobrancas').status_code, 403)
        self.assertEqual(self.client.get('/integracoes/arkhe/conta').status_code, 403)
        self.assertEqual(self.banco.chamadas, [])

    def test_dados_invalidos_e_projeto_inexistente(self):
        for valor in (0, -1, 'NaN', 'Infinity', '0.001', '1000000000'):
            self.assertEqual(self.criar({**self.payload, 'valor': valor}).status_code, 400)
        self.assertEqual(self.criar({**self.payload, 'id_projeto': 999}).status_code, 400)
        self.assertEqual(self.criar({**self.payload, 'doador': ''}).status_code, 400)
        self.assertEqual(self.criar({**self.payload, 'descricao': 'x' * 201}).status_code, 400)
        self.assertEqual(self.criar([]).status_code, 400)
        self.assertEqual(self.banco.chamadas, [])

    def test_outra_integracao_nao_acessa_cobrancas(self):
        self.criar()
        self.banco.integracao = 'outra'
        self.assertEqual(self.client.get('/integracoes/arkhe/cobrancas').json['cobrancas'], [])
        self.assertEqual(self.consultar().status_code, 404)

    def test_conta_nao_expoe_segredos(self):
        retorno = self.client.get('/integracoes/arkhe/conta')
        self.assertEqual(retorno.status_code, 200)
        self.assertNotIn('secret', json.dumps(retorno.json))

    def test_cliente_sem_configuracao_nao_acessa_rede(self):
        with self.assertRaises(ErroArkhe) as erro:
            ClienteArkhe({'url': 'https://example.com', 'client_id': '', 'client_secret': ''}).chamar('/api/v1/conta')
        self.assertEqual(erro.exception.status, 503)

    def test_cliente_headers_timeout_e_erros_sem_segredos(self):
        cliente = ClienteArkhe({'url': 'https://banco.example', 'client_id': 'id-teste', 'client_secret': 'secret-teste'})
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = io.BytesIO(b'{"saldo": 10}')
            self.assertEqual(cliente.chamar('/api/v1/saldo'), {'saldo': 10})
            req = opener.return_value.open.call_args.args[0]
            self.assertEqual(req.get_header('X-client-secret'), 'secret-teste')
            self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 15)
        for codigo in (400, 401, 403, 404, 500):
            with patch('urllib.request.build_opener') as opener:
                opener.return_value.open.side_effect = HTTPError('https://banco.example', codigo, 'secret-teste', {}, None)
                with self.assertRaises(ErroArkhe) as erro:
                    cliente.chamar('/api/v1/conta')
                self.assertNotIn('secret-teste', str(erro.exception))
                self.assertEqual(erro.exception.definitivo, codigo != 500)

    def test_cliente_bloqueia_redirecionamento(self):
        cliente = ClienteArkhe({'url': 'https://banco.example', 'client_id': 'id', 'client_secret': 'secret'})
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError('https://banco.example', 302, 'Redirect', {}, None)
            with self.assertRaises(ErroArkhe):
                cliente.chamar('/api/v1/conta')
            handler = opener.call_args.args[0]()
            self.assertIsNone(handler.redirect_request(None, None, None, None, None, 'https://outro.example'))

    def test_motivo_do_provedor_e_preservado_sem_credenciais(self):
        cliente = ClienteArkhe({'url':'https://banco.example','client_id':'id-teste','client_secret':'segredo-teste'})
        for status in (400,422):
            corpo = json.dumps({'mensagem':'Valor livre não permitido. segredo-teste'}).encode()
            erro = HTTPError('https://banco.example',status,'erro',{},io.BytesIO(corpo))
            with patch('urllib.request.build_opener') as opener:
                opener.return_value.open.side_effect = erro
                with self.assertRaises(ErroArkhe) as resultado: cliente.chamar('/api/v1/cobrancas/pix/qrcode', {'valor_livre':True})
            self.assertIn('Valor livre não permitido',str(resultado.exception))
            self.assertNotIn('segredo-teste',str(resultado.exception))
            self.assertTrue(resultado.exception.definitivo)

    def test_recuperacao_de_falha_nao_repete_criacao_e_preserva_motivo(self):
        self.banco.erro = ErroArkhe('Arkhé: integração sem permissão.',422,True)
        self.criar()
        recuperada = self.criar()
        self.assertEqual(recuperada.json['cobranca']['motivo'],'Arkhé: integração sem permissão.')
        self.assertEqual(len(self.banco.chamadas),1)

    def test_status_somente_consulta_nao_registra_recebimento(self):
        self.criar()
        self.banco.pago = True
        resposta = self.client.get(f"/integracoes/arkhe/cobrancas/{self.payload['id']}/status")
        self.assertEqual(resposta.status_code,200)
        self.assertEqual(resposta.json['cobranca']['situacao'],'pago')
        self.assertEqual(resposta.json['situacao_registrada'],'pendente')
        self.assertFalse(resposta.json['recebimento_registrado'])
        self.assertEqual(self.contagens(),(0,0))
        local = self.client.get('/integracoes/arkhe/cobrancas').json['cobrancas'][0]
        self.assertEqual(local['situacao'],'pendente')
        self.assertEqual(self.consultar().status_code,200)
        self.assertEqual(self.contagens(),(1,1))

    def test_status_respeita_permissoes_e_integracao(self):
        self.criar()
        url = f"/integracoes/arkhe/cobrancas/{self.payload['id']}/status"
        self.permitido = False
        chamadas = len(self.banco.chamadas)
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(len(self.banco.chamadas),chamadas)
        self.permitido = True
        self.banco.integracao = 'outra'
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.contagens(),(0,0))

    def test_status_recusa_dados_bancarios_inconsistentes(self):
        self.criar()
        self.banco.pago = True
        self.banco.valor = 99
        resposta = self.client.get(f"/integracoes/arkhe/cobrancas/{self.payload['id']}/status")
        self.assertEqual(resposta.status_code,502)
        self.assertEqual(self.contagens(),(0,0))

    def test_status_de_valor_livre_retorna_quantia_recebida_sem_lancar(self):
        self.criar({**self.payload,'valor':None,'valor_livre':True})
        self.banco.pago = True
        self.banco.valor = 77.5
        resposta = self.client.get(f"/integracoes/arkhe/cobrancas/{self.payload['id']}/status")
        self.assertEqual(resposta.json['cobranca']['valor'],77.5)
        self.assertEqual(self.contagens(),(0,0))


if __name__ == '__main__':
    unittest.main()
