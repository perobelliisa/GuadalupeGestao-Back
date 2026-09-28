"""Testes isolados: não acessam o banco de produção nem os usuários reais."""
import ast
import fdb
from calendar import monthrange
from threading import RLock
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from unittest.mock import patch
from flask import Flask

# Carrega somente as funcoes testadas, sem iniciar o servidor ou abrir o banco real.
BACKEND = Path(__file__).resolve().parent.parent
REGRAS = ['data_civil', 'prioridade', 'proxima_conta', 'proxima_parcela']
AJUDANTES = ['abrir_conexao', 'carregar_pendencias']


def carregar_codigo(arquivo, nomes, ambiente):
    arvore = ast.parse((BACKEND / arquivo).read_text(encoding='utf-8'))
    selecionados = []
    for no in arvore.body:
        if isinstance(no, ast.FunctionDef) and no.name in nomes:
            selecionados.append(no)
    exec(compile(ast.Module(body=selecionados, type_ignores=[]), arquivo, 'exec'), ambiente)


ambiente_regras = dict(date=date, timedelta=timedelta, monthrange=monthrange,
                      Decimal=Decimal, ROUND_HALF_UP=ROUND_HALF_UP,
                      INTERVALOS_PENDENCIAS={1: 15, 2: 30, 3: 1, 4: 7})
carregar_codigo('function.py', REGRAS, ambiente_regras)
prioridade = ambiente_regras['prioridade']
proxima_conta = ambiente_regras['proxima_conta']
proxima_parcela = ambiente_regras['proxima_parcela']


sqlite3.register_adapter(date, lambda valor: valor.isoformat())


class CalendarioTest(unittest.TestCase):
    def test_limites_prioridades(self):
        for dias, esperado in [(-20, 'Alta'), (0, 'Alta'), (1, 'Alta'), (2, 'Alta'),
                               (3, 'Média'), (7, 'Média'), (8, 'Média'), (13, 'Média'), (14, 'Baixa'), (60, 'Baixa')]:
            with self.subTest(dias=dias):
                self.assertEqual(prioridade(dias), esperado)

    def test_intervalos_e_pagamento_inicial(self):
        for codigo, esperado in [(1, '2026-01-16'), (2, '2026-01-31'), (3, '2026-01-02'), (4, '2026-01-08')]:
            item = dict(recorrencia=codigo, dia_inicio='2026-01-01', dia_fim='2026-03-01', status='1')
            self.assertEqual(proxima_conta(item, []).isoformat(), esperado)

    def test_fim_da_recorrencia_inclusivo(self):
        item = dict(recorrencia=4, dia_inicio='2026-01-01', dia_fim='2026-01-15', status=1)
        self.assertEqual(proxima_conta(item, ['2026-01-08']), date(2026, 1, 15))
        self.assertIsNone(proxima_conta(item, ['2026-01-08', '2026-01-15']))

    def test_nao_pula_atrasadas(self):
        item = dict(recorrencia=2, dia_inicio='2020-01-01', dia_fim='2020-03-01', status=0)
        self.assertEqual(proxima_conta(item, []), date(2020, 1, 1))

    def test_nao_recorrente_e_datas_invalidas(self):
        self.assertIsNone(proxima_conta(dict(recorrencia=0), []))
        with self.assertRaises(ValueError):
            proxima_conta(dict(recorrencia=1, dia_inicio='2026-02-30', dia_fim='2026-03-30'), [])

    def test_parcelas_fim_de_mes_e_bissexto(self):
        item = dict(dia='2024-01-31', parcelas=3, parcelas_pagas=0, valor=100)
        self.assertEqual(proxima_parcela(item), (date(2024, 2, 29), 1, Decimal('33.33')))
        item['parcelas_pagas'] = 1
        self.assertEqual(proxima_parcela(item)[0], date(2024, 3, 31))
        item['parcelas_pagas'] = 2
        self.assertEqual(proxima_parcela(item), (date(2024, 4, 30), 3, Decimal('33.34')))

    def test_emprestimo_quitado_ou_avista_nao_aparece(self):
        self.assertIsNone(proxima_parcela(dict(parcelas=1)))
        self.assertIsNone(proxima_parcela(dict(parcelas=3, parcelas_pagas=3)))
        with self.assertRaises(ValueError):
            proxima_parcela(dict(parcelas=3, parcelas_pagas=-1))


class APItest(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.caminho = Path(self.pasta.name) / 'teste.sqlite'
        self.db = sqlite3.connect(self.caminho)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            PRAGMA foreign_keys=ON;
            CREATE TABLE LIVRO_CAIXA (ID_LIVRO_CAIXA INTEGER PRIMARY KEY, ID_CATEGORIA INTEGER,
                DESCRICAO TEXT, TIPO INTEGER, VALOR NUMERIC, DIA TEXT, VENCIMENTO TEXT,
                FORNECEDOR TEXT, STATUS INTEGER, RECORRENCIA INTEGER, DIA_INICIO TEXT,
                DIA_FIM TEXT, CONTA INTEGER, ORIGEM TEXT, FORMA_PAGAMENTO INTEGER, OBSERVACAO TEXT);
            CREATE TABLE EMPRESTIMO (ID_EMPRESTIMO INTEGER PRIMARY KEY, FINALIDADE TEXT, ID_PROJETO INTEGER,
                VALOR NUMERIC, DIA TEXT, PARCELAS INTEGER, PARCELAS_PAGAS INTEGER);
            CREATE TABLE PAGAMENTO_RECORRENCIA (ID_ORIGEM INTEGER, VENCIMENTO DATE, ID_PAGAMENTO INTEGER,
                PRIMARY KEY (ID_ORIGEM, VENCIMENTO), FOREIGN KEY(ID_PAGAMENTO) REFERENCES LIVRO_CAIXA(ID_LIVRO_CAIXA));
            INSERT INTO LIVRO_CAIXA (ID_LIVRO_CAIXA, DESCRICAO, TIPO, VALOR, DIA, STATUS, RECORRENCIA, DIA_INICIO, DIA_FIM, CONTA)
                VALUES (1, 'Conta semanal', 1, 50, '2026-01-01', 0, 4, '2026-01-01', '2026-01-15', 0);
            INSERT INTO EMPRESTIMO VALUES (1, 'Parcelado', 1, 100, '2024-01-31', 3, 0);
        ''')
        app = Flask(__name__)
        app.testing = True

        def listar(cur, tipo):
            cur.execute('SELECT * FROM LIVRO_CAIXA WHERE TIPO = ?', (tipo,))
            return [{chave.lower(): linha[chave] for chave in linha.keys()} for linha in cur.fetchall()]

        def inserir(cur, item, tipo):
            cur.execute('''INSERT INTO LIVRO_CAIXA (DESCRICAO, TIPO, VALOR, DIA, VENCIMENTO, STATUS, RECORRENCIA, CONTA)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (item['descricao'], tipo, item['valor'], str(item['data']),
                str(item['vencimento']), item['status'], item['recorrencia'], item['conta']))
            return cur.lastrowid

        from flask import jsonify, request
        self.api = types.ModuleType('api_financeiro_teste')
        self.api.__dict__.update(ambiente_regras)
        self.api.__dict__.update(app=app, con=self.db, fdb=fdb, jsonify=jsonify, request=request,
                                 trava_pagamento_pendencias=RLock(), listar_lancamentos=listar,
                                 inserir_lancamento=inserir, usuario_pode_gerenciar_doacoes=lambda: True)
        carregar_codigo('function.py', REGRAS + AJUDANTES, self.api.__dict__)
        carregar_codigo('livro_caixa.py', ['listar_pendencias', 'pagar_pendencia'], self.api.__dict__)
        self.api.abrir_conexao = lambda: types.SimpleNamespace(cursor=self.db.cursor, commit=self.db.commit,
                                                              rollback=self.db.rollback, close=lambda: None)
        self.client = app.test_client()

    def tearDown(self):
        self.db.close()
        self.pasta.cleanup()

    def lista(self):
        resposta = self.client.get('/pendencias')
        self.assertEqual(resposta.status_code, 200)
        return resposta.json['pendencias']

    def pagar(self, tipo, vencimento):
        return self.client.post(f'/pendencias/{tipo}/1/pagar', json={'vencimento': vencimento})

    def test_pagamento_some_apos_nova_consulta_e_preserva_proximo(self):
        primeira = next(item for item in self.lista() if item['tipo'] == 'despesa')
        self.assertEqual(self.pagar('despesa', primeira['vencimento']).status_code, 200)
        depois = self.lista()
        self.assertNotIn(primeira['chave'], [item['chave'] for item in depois])
        self.assertEqual(next(item for item in depois if item['tipo'] == 'despesa')['vencimento'], '2026-01-08')

    def test_repetir_pagamento_nao_paga_proxima(self):
        self.assertEqual(self.pagar('despesa', '2026-01-01').status_code, 200)
        self.assertEqual(self.pagar('despesa', '2026-01-01').status_code, 409)
        self.assertEqual(self.pagar('emprestimo', '2024-02-29').status_code, 200)
        self.assertEqual(self.pagar('emprestimo', '2024-02-29').status_code, 409)
        self.assertEqual(next(item for item in self.lista() if item['tipo'] == 'emprestimo')['parcela'], 2)

    def test_todas_ocorrencias_pagas_sem_duplicar_valor(self):
        for dia in ('2026-01-01', '2026-01-08', '2026-01-15'):
            self.assertEqual(self.pagar('despesa', dia).status_code, 200)
        self.assertFalse(any(item['tipo'] == 'despesa' for item in self.lista()))
        self.assertEqual(self.db.execute('SELECT SUM(VALOR) FROM LIVRO_CAIXA WHERE STATUS=1').fetchone()[0], 150)
        self.assertEqual(self.pagar('despesa', '2026-01-15').status_code, 409)

    def test_quitacao_emprestimo(self):
        for dia in ('2024-02-29', '2024-03-31', '2024-04-30'):
            self.assertEqual(self.pagar('emprestimo', dia).status_code, 200)
        self.assertFalse(any(item['tipo'] == 'emprestimo' for item in self.lista()))

    def test_data_forjada_e_parcela_fora_de_ordem(self):
        self.assertEqual(self.pagar('despesa', '2026-01-03').status_code, 409)
        self.assertEqual(self.pagar('emprestimo', '2024-03-31').status_code, 409)
        self.assertEqual(self.pagar('despesa', 'invalida').status_code, 400)

    def test_falha_salvamento_nao_remove_pendencia(self):
        self.pagar('despesa', '2026-01-01')
        with patch.object(self.api, 'inserir_lancamento', side_effect=RuntimeError('Falha simulada')):
            with self.assertLogs(self.api.app.logger, level='ERROR'):
                self.assertEqual(self.pagar('despesa', '2026-01-08').status_code, 409)
        self.assertEqual(next(item for item in self.lista() if item['tipo'] == 'despesa')['vencimento'], '2026-01-08')

    def test_sem_autenticacao(self):
        self.api.usuario_pode_gerenciar_doacoes = lambda: False
        self.assertEqual(self.client.get('/pendencias').status_code, 403)
        self.assertEqual(self.pagar('despesa', '2026-01-01').status_code, 403)

    def test_dados_invalidos_avisam_sem_ocultar_validos(self):
        self.db.execute("UPDATE LIVRO_CAIXA SET DIA_INICIO = '2026-02-30'")
        self.db.commit()
        resposta = self.client.get('/pendencias')
        self.assertEqual(len(resposta.json['avisos']), 1)
        self.assertEqual(len(resposta.json['pendencias']), 1)

    def test_reverter_pagamento_reabre_sem_duplicar(self):
        self.pagar('despesa', '2026-01-01')
        self.pagar('despesa', '2026-01-08')
        self.db.execute('UPDATE LIVRO_CAIXA SET STATUS=0 WHERE ID_LIVRO_CAIXA=2')
        self.db.commit()
        self.assertEqual(next(item for item in self.lista() if item['tipo'] == 'despesa')['vencimento'], '2026-01-08')
        self.assertEqual(self.pagar('despesa', '2026-01-08').status_code, 200)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM LIVRO_CAIXA').fetchone()[0], 2)

    def test_pagamento_persiste_apos_reabrir_banco(self):
        self.pagar('despesa', '2026-01-01')
        self.pagar('despesa', '2026-01-08')
        self.pagar('emprestimo', '2024-02-29')
        self.db.close()
        self.db = sqlite3.connect(self.caminho)
        self.db.row_factory = sqlite3.Row
        lista = self.lista()
        self.assertEqual(next(item for item in lista if item['tipo'] == 'despesa')['vencimento'], '2026-01-15')
        self.assertEqual(next(item for item in lista if item['tipo'] == 'emprestimo')['parcela'], 2)

    def test_falha_apos_inserir_despesa_desfaz_toda_transacao(self):
        self.pagar('despesa', '2026-01-01')
        self.db.execute("CREATE TRIGGER falhar BEFORE INSERT ON PAGAMENTO_RECORRENCIA BEGIN SELECT RAISE(ABORT, 'falha simulada'); END")
        self.db.commit()
        with self.assertLogs(self.api.app.logger, level='ERROR'):
            self.assertEqual(self.pagar('despesa', '2026-01-08').status_code, 409)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM LIVRO_CAIXA').fetchone()[0], 1)
        self.assertEqual(next(item for item in self.lista() if item['tipo'] == 'despesa')['vencimento'], '2026-01-08')


if __name__ == '__main__':
    unittest.main()
