"""Regressao da inicializacao e registro da documentacao, sem banco real."""
import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

BACKEND = Path(__file__).resolve().parent.parent
if not (BACKEND / 'api_docs.py').exists():
    BACKEND = Path(r'C:\Users\Aluno\Desktop\GuadalupeGestao-Back')
sys.path.insert(0, str(BACKEND))
from api_docs import registrar_documentacao


class DocumentacaoTest(unittest.TestCase):
    def test_registro_repetido(self):
        app = Flask('teste_docs')
        registrar_documentacao(app)
        registrar_documentacao(app)
        client = app.test_client()
        self.assertEqual(client.get('/docs').status_code, 200)
        self.assertEqual(client.get('/openapi.json').status_code, 200)
        rules = list(app.url_map.iter_rules())
        self.assertEqual(sum(r.rule == '/docs' for r in rules), 1)
        self.assertEqual(sum(r.rule == '/openapi.json' for r in rules), 1)

    def test_execucao_direta_compartilha_main(self):
        entry = types.ModuleType('__main__')
        entry.__file__ = str(BACKEND / 'main.py')
        fake_fdb = types.ModuleType('fdb')
        def connect(**kwargs):
            self.assertIs(importlib.import_module('main'), entry)
            return object()
        fake_fdb.connect = connect
        fake_cors = types.ModuleType('flask_cors')
        fake_cors.CORS = lambda *a, **k: None
        mocks = {'__main__': entry, 'fdb': fake_fdb, 'flask_cors': fake_cors}
        for name in ('user', 'doacoes', 'emprestimos', 'livro_caixa', 'documentos', 'relatorios', 'function', 'categorias'):
            mocks[name] = types.ModuleType(name)
        mocks['function'].preparar_tabela_pendencias = lambda: None
        with patch.dict(sys.modules, mocks), patch.object(Flask, 'run') as run, patch.object(Flask.config_class, 'from_pyfile'):
            entry_code = (BACKEND / 'main.py').read_text(encoding='utf-8')
            # Configuracao ficticia: nunca le credenciais ou abre banco real.
            with patch.object(Flask, 'config_class', type('TestConfig', (Flask.config_class,), {
                'from_pyfile': lambda config, *a, **k: config.update(DB_HOST='', DB_NAME='', DB_USER='', DB_PASSWORD='')
            })):
                exec(compile(entry_code, entry.__file__, 'exec'), entry.__dict__)
            run.assert_called_once_with(host='0.0.0.0', port=5000)
            self.assertEqual(entry.app.test_client().get('/docs').status_code, 200)
            self.assertEqual(entry.app.test_client().get('/openapi.json').status_code, 200)


if __name__ == '__main__':
    unittest.main()

