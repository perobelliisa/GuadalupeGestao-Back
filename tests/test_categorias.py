"""Testes de edição com conexão simulada; não acessam o banco real."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from flask import Flask


class CategoriasTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask('teste_categorias')
        self.app.logger.disabled = True
        self.con = Mock()
        self.cur = self.con.cursor.return_value
        self.cur.fetchone.side_effect = [('Original', 0, 0, 'Descrição'), None]
        self.helpers = types.ModuleType('function')
        self.helpers.abrir_conexao = Mock(return_value=self.con)
        self.helpers.id_usuario_logado = Mock(return_value=7)
        self.helpers.usuario_pode_gerenciar_doacoes = Mock(return_value=True)
        self.helpers.pegar_dispositivo = Mock(return_value={'nome': 'Servidor'})
        from flask import request
        self.helpers.dados_requisicao = lambda: request.get_json() if request.is_json else request.form
        main = types.ModuleType('main')
        main.app = self.app
        root = Path(__file__).resolve().parent
        path = root / 'categorias.py'
        if not path.exists():
            path = root.parent / 'categorias.py'
        with patch.dict(sys.modules, {'main': main, 'function': self.helpers}):
            spec = importlib.util.spec_from_file_location('categorias_teste', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.client = self.app.test_client()

    def test_atualizacao_com_auditoria_da_sessao(self):
        response = self.client.put('/categorias/2', json={'nome': 'Oferta', 'descricao': 'Recebimentos', 'id_usuario': 999, 'dispositivo': 'Falso'})
        self.assertEqual(response.status_code, 200)
        sql, values = self.cur.execute.call_args.args
        self.assertIn('UPDATE CATEGORIA', sql)
        self.assertEqual(values, ('Oferta', 'Recebimentos', 7, 'Servidor', 2))
        self.assertEqual(response.json['categoria']['tipo'], 0)
        self.con.commit.assert_called_once()
        self.con.close.assert_called_once()

    def test_sem_permissao_nao_abre_conexao(self):
        self.helpers.usuario_pode_gerenciar_doacoes.return_value = False
        self.assertEqual(self.client.put('/categorias/2', json={'nome': 'Oferta'}).status_code, 403)
        self.helpers.abrir_conexao.assert_not_called()

    def test_nome_invalido(self):
        self.assertEqual(self.client.put('/categorias/2', json={'nome': ' '}).status_code, 400)
        self.helpers.abrir_conexao.assert_not_called()

    def test_inexistente(self):
        self.cur.fetchone.side_effect = [None]
        self.assertEqual(self.client.put('/categorias/2', json={'nome': 'Oferta'}).status_code, 404)
        self.con.commit.assert_not_called()

    def test_duplicada(self):
        self.cur.fetchone.side_effect = [('Original', 0, 0, ''), (3,)]
        self.assertEqual(self.client.put('/categorias/2', json={'nome': 'Oferta'}).status_code, 409)
        self.con.commit.assert_not_called()

    def test_falha_trigger_desfaz_atualizacao(self):
        self.con.commit.side_effect = RuntimeError('Falha no histórico')
        self.assertEqual(self.client.put('/categorias/2', data={'nome': 'Oferta', 'descricao': 'Recebimentos'}).status_code, 500)
        self.con.rollback.assert_called_once()
        self.con.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
