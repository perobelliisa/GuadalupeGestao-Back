import re
import sqlite3
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from flask import Flask, g

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auditoria import registrar_auditoria, filtros_consulta
from auditoria_contexto import registrar_contexto, aplicar_contexto
from migrar_auditoria import atualizar_trigger, base_generica


class Cursor:
    def __init__(self, db): self.cur = db.cursor()
    def execute(self, sql, params=()):
        sql = sql.replace(' CONTAINING ?', ' LIKE ?')
        if ' LIKE ?' in sql:
            params = ['%' + p + '%' if isinstance(p, str) else p for p in params]
        match = re.search(r'SELECT FIRST (\d+) SKIP (\d+)', sql)
        if match:
            sql = sql.replace(match[0], 'SELECT') + f' LIMIT {match[1]} OFFSET {match[2]}'
        self.cur.execute(sql, params)
    def fetchone(self): return self.cur.fetchone()
    def fetchall(self): return self.cur.fetchall()
    def close(self): self.cur.close()


class Conexao:
    def __init__(self, db): self.db = db
    def cursor(self): return Cursor(self.db)
    def close(self): pass


class AuditoriaTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript('''CREATE TABLE HISTORICO (ID_HISTORICO INTEGER, EMAIL TEXT, DISPOSITIVO TEXT,
            DATA_HORA TIMESTAMP, TABELA TEXT, CAMPO TEXT, ACAO TEXT, CAMPO_ANTIGO TEXT, CAMPO_NOVO TEXT,
            ID_USUARIO INTEGER, NOME_USUARIO TEXT, REGISTRO_ID TEXT);
            INSERT INTO HISTORICO VALUES (1, 'antigo@teste', '', NULL, 'DOACAO', 'DOADOR', 'INSERT', '', 'José', NULL, NULL, NULL);
            INSERT INTO HISTORICO VALUES (2, 'admin@teste', 'Guadalupe', NULL, 'USUARIO', 'NOME', 'UPDATE', 'Maria', 'Ana', 2, 'Rodrigo', '7');''')
        self.app = Flask(__name__)
        self.autorizado = True
        registrar_auditoria(self.app, lambda: self.autorizado, lambda: Conexao(self.db))
        self.client = self.app.test_client()

    def tearDown(self): self.db.close()

    def test_legado_nao_inventa_autoria_e_nome_e_snapshot(self):
        r = self.client.get('/logs').json
        self.assertEqual(r['total'], 2)
        self.assertEqual(r['logs'][0]['nome_usuario'], 'Rodrigo')
        self.assertEqual(r['logs'][0]['antes'], 'Maria')
        self.assertTrue(r['logs'][1]['identificacao_legada'])
        self.assertEqual(r['logs'][1]['nome_usuario'], 'Rodrigo')

    def test_acesso_restrito_a_administrador(self):
        self.autorizado = False
        self.assertEqual(self.client.get('/logs').status_code, 403)

    def test_paginacao_filtros_e_injecao(self):
        self.assertEqual(self.client.get('/logs?tamanho=1&pagina=2').json['logs'][0]['id'], 1)
        self.assertEqual(self.client.get('/logs?tabela=USUARIO&acao=UPDATE&registro=7').json['total'], 1)
        self.assertEqual(self.client.get('/logs?usuario=Rodrigo').json['total'], 2)
        self.assertEqual(self.client.get("/logs?tabela=' OR 1=1 --").json['total'], 0)

    def test_filtros_invalidos(self):
        for filtro in ['tamanho=10000', 'pagina=0', 'acao=DROP', 'inicio=2026-02-30', 'inicio=2026-10-27&fim=2026-10-26']:
            self.assertEqual(self.client.get('/logs?' + filtro).status_code, 400, filtro)

    def test_falha_nao_e_lista_vazia(self):
        self.db.close()
        with self.assertLogs(self.app.logger, level='ERROR'):
            self.assertEqual(self.client.get('/logs').status_code, 503)
        self.db = sqlite3.connect(':memory:')

    def test_limite_final_inclui_todo_dia(self):
        where, params = filtros_consulta({'fim': '2026-10-26'})
        self.assertIn('DATA_HORA < ?', where)
        self.assertEqual(str(params[0]), '2026-10-27 00:00:00')


class ContextoTest(unittest.TestCase):
    def test_contexto_nao_vaza_entre_requisicoes(self):
        app = Flask(__name__)
        contexto = {}
        class Cur:
            def execute(self, sql, params):
                self.select = 'SELECT ID_USUARIO' in sql
                if not self.select:
                    contexto[params[0]] = params[1]
            def fetchone(self): return (2, 'Rodrigo', 'r@teste') if self.select else (1,)
            def close(self): pass
        class Con:
            def cursor(self): return Cur()
        from flask import request
        registrar_contexto(app, Con(), lambda: 2 if request.path == '/autenticado' else None, lambda: {'nome': 'Chrome / Windows', 'ip': '192.0.2.10'})
        @app.get('/autenticado')
        @app.get('/anonimo')
        def estado(): return dict(contexto)
        client = app.test_client()
        self.assertEqual(client.get('/autenticado').json['GLOG_NOME'], 'Rodrigo')
        self.assertIsNone(contexto['GLOG_NOME'])
        self.assertIsNone(client.get('/anonimo').json['GLOG_NOME'])


class MigracaoTest(unittest.TestCase):
    def test_trigger_identifica_ator_e_preserva_conteudo(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {'DB_USER': 'SYSDBA', 'DB_PASSWORD': "p'ass"}):
            for sigla, acao in [('AI','INSERT'),('AU','UPDATE'),('AD','DELETE')]:
                sql = atualizar_trigger('TG_' + sigla + '_ARKHE_COBRANCA', 'ARKHE_COBRANCA', base_generica(['ID', 'VALOR'], acao), ['ID','VALOR'])
                self.assertIn("PASSWORD 'p''ass'", sql)
                self.assertIn('ID_USUARIO, NOME_USUARIO, REGISTRO_ID, EMAIL', sql)
                self.assertIn('V_AUD_ID', sql)
                self.assertIn('AFTER INSERT' if acao == 'INSERT' else 'BEFORE ' + acao, sql)
                self.assertIn('GLOG_DISPOSITIVO', sql)


if __name__ == '__main__': unittest.main()
