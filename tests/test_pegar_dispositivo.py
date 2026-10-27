import ast
from pathlib import Path
import unittest
from flask import Flask

codigo = ast.parse((Path(__file__).resolve().parents[1] / 'function.py').read_text())
funcao = next(n for n in codigo.body if isinstance(n, ast.FunctionDef) and n.name == 'pegar_dispositivo')
ambiente = {}
exec(compile(ast.Module(body=[funcao], type_ignores=[]), 'function.py', 'exec'), ambiente)
pegar_dispositivo = ambiente['pegar_dispositivo']

class DispositivoTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['GLOG_TRUSTED_PROXY_CIDRS'] = '10.0.0.0/8,172.16.0.0/12'
    def test_ip_direto(self):
        with self.app.test_request_context(environ_base={'REMOTE_ADDR': '8.8.4.4'}):
            self.assertEqual(pegar_dispositivo()['ip'], '8.8.4.4')
    def test_proxies_e_header_falso_a_esquerda(self):
        with self.app.test_request_context(headers={'X-Forwarded-For': '1.1.1.1, 8.8.4.4, 172.18.0.1', 'User-Agent': 'Mozilla Windows Chrome/130 Safari/537.36'}, environ_base={'REMOTE_ADDR': '10.0.0.2'}):
            self.assertEqual(pegar_dispositivo(), {'nome': 'Chrome / Windows', 'ip': '8.8.4.4'})
    def test_header_nao_confiavel_ignorado(self):
        with self.app.test_request_context(headers={'X-Forwarded-For': '1.1.1.1'}, environ_base={'REMOTE_ADDR': '8.8.4.4'}):
            self.assertEqual(pegar_dispositivo()['ip'], '8.8.4.4')
    def test_ip_interno_ou_header_invalido_nao_vira_cliente(self):
        for header in ['', 'texto-invalido', '172.18.0.3']:
            with self.app.test_request_context(headers={'X-Forwarded-For': header}, environ_base={'REMOTE_ADDR': '10.0.0.2'}):
                self.assertEqual(pegar_dispositivo()['ip'], 'Não informado')
    def test_sem_proxy_configurado(self):
        self.app.config['GLOG_TRUSTED_PROXY_CIDRS'] = ''
        with self.app.test_request_context(headers={'X-Forwarded-For': '1.1.1.1'}, environ_base={'REMOTE_ADDR': '10.0.0.2'}):
            self.assertEqual(pegar_dispositivo()['ip'], 'Não informado')
    def test_ipv6(self):
        with self.app.test_request_context(environ_base={'REMOTE_ADDR': '2606:4700:4700::1111'}):
            self.assertEqual(pegar_dispositivo()['ip'], '2606:4700:4700::1111')
    def test_sem_requisicao_nao_identifica_servidor(self):
        self.assertEqual(pegar_dispositivo(), {'nome': 'Processo interno', 'ip': 'Não informado'})

if __name__ == '__main__': unittest.main()
