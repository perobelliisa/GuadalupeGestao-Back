"""Identidade autenticada para as triggers; nunca usa o usuário enviado no formulário."""
from flask import g, has_request_context


def aplicar_contexto(conexao):
    ator = getattr(g, 'ator_auditoria', None) if has_request_context() else None
    valores = ator or {'ID': None, 'NOME': None, 'EMAIL': None, 'DISPOSITIVO': None}
    cur = conexao.cursor()
    try:
        for chave, valor in valores.items():
            cur.execute("SELECT RDB$SET_CONTEXT('USER_SESSION', ?, ?) FROM RDB$DATABASE",
                        ('GLOG_' + chave, str(valor) if valor is not None else None))
            cur.fetchone()
    finally:
        cur.close()


def registrar_contexto(app, conexao, identificar, dispositivo):
    @app.before_request
    def preparar_ator_auditoria():
        g.ator_auditoria = None
        identificador = identificar()
        if identificador:
            cur = conexao.cursor()
            try:
                cur.execute('SELECT ID_USUARIO, NOME, EMAIL FROM USUARIO WHERE ID_USUARIO = ?', (identificador,))
                usuario = cur.fetchone()
                if usuario:
                    cliente = dispositivo()
                    origem = f"{cliente['nome'][:50]} | IP: {cliente['ip']}"
                    g.ator_auditoria = {'ID': usuario[0], 'NOME': usuario[1].strip(),
                                         'EMAIL': (usuario[2] or '').strip(),
                                         'DISPOSITIVO': origem}
            finally:
                cur.close()
        aplicar_contexto(conexao)

    @app.teardown_request
    def limpar_ator_auditoria(erro):
        # O servidor atual usa uma thread. Limpa inclusive após falha de uma rota,
        # para não atribuir tarefas sem sessão ao usuário da requisição anterior.
        g.ator_auditoria = None
        try:
            aplicar_contexto(conexao)
        except Exception:
            app.logger.warning('Não foi possível limpar o contexto de auditoria da conexão.')
