"""Consulta paginada, exclusiva para administradores, do BancoLog."""
from contextlib import closing
from datetime import date, datetime, timedelta
import os
import fdb
from flask import jsonify, request


def abrir_bancolog(app):
    return fdb.connect(host=os.getenv('DB_LOG_HOST', app.config['DB_HOST']),
                       database=os.getenv('DB_LOG_NAME', '/var/lib/firebird/data/BANCOLOG.FDB'),
                       user=os.getenv('DB_LOG_USER', app.config['DB_USER']),
                       password=os.getenv('DB_LOG_PASSWORD', app.config['DB_PASSWORD']), charset='UTF8')


def filtros_consulta(args):
    clausulas, parametros = [], []
    for nome, coluna in [('tabela', 'TABELA'), ('acao', 'ACAO')]:
        valor = args.get(nome, '').strip()
        if valor:
            if nome == 'acao' and valor not in ('INSERT', 'UPDATE', 'DELETE'):
                raise ValueError('Ação inválida.')
            clausulas.append(coluna + ' = ?')
            parametros.append(valor[:63])
    inicio = args.get('inicio', '')
    fim = args.get('fim', '')
    if inicio and fim and date.fromisoformat(inicio) > date.fromisoformat(fim):
        raise ValueError('A data inicial deve ser anterior à final.')
    if inicio:
        clausulas.append('DATA_HORA >= ?')
        parametros.append(datetime.combine(date.fromisoformat(inicio), datetime.min.time()))
    if fim:
        clausulas.append('DATA_HORA < ?')
        parametros.append(datetime.combine(date.fromisoformat(fim) + timedelta(days=1), datetime.min.time()))
    usuario = args.get('usuario', '').strip()
    if usuario:
        clausulas.append("(COALESCE(NOME_USUARIO, 'Rodrigo') CONTAINING ? OR EMAIL CONTAINING ?)")
        parametros.extend([usuario[:254], usuario[:254]])
    registro = args.get('registro', '').strip()
    if registro:
        clausulas.append('REGISTRO_ID = ?')
        parametros.append(registro[:254])
    return (' WHERE ' + ' AND '.join(clausulas) if clausulas else ''), parametros


def texto(valor):
    if hasattr(valor, 'read'):
        valor = valor.read()
    return valor.strip() if isinstance(valor, str) else valor


def registrar_auditoria(app, administrador, conectar=None):
    conectar = conectar or (lambda: abrir_bancolog(app))

    @app.get('/logs')
    def listar_logs():
        if not administrador():
            return jsonify(sucesso=False, mensagem='Somente administradores podem consultar os logs.'), 403
        try:
            pagina = int(request.args.get('pagina', '1'))
            tamanho = int(request.args.get('tamanho', '25'))
            if pagina < 1 or pagina > 1000000 or tamanho < 1 or tamanho > 100:
                raise ValueError('Paginação inválida.')
            where, params = filtros_consulta(request.args)
        except (ValueError, OverflowError):
            return jsonify(sucesso=False, mensagem='Confira as datas e os filtros informados.'), 400
        try:
            with closing(conectar()) as con:
                with closing(con.cursor()) as cur:
                    cur.execute('SELECT COUNT(*) FROM HISTORICO' + where, params)
                    total = cur.fetchone()[0]
                    cur.execute(f'''SELECT FIRST {tamanho} SKIP {(pagina - 1) * tamanho}
                        ID_HISTORICO, EMAIL, DISPOSITIVO, DATA_HORA, TABELA, CAMPO, ACAO,
                        CAMPO_ANTIGO, CAMPO_NOVO, ID_USUARIO, NOME_USUARIO, REGISTRO_ID
                        FROM HISTORICO{where} ORDER BY DATA_HORA DESC, ID_HISTORICO DESC''', params)
                    colunas = ['id', 'email', 'dispositivo', 'data_hora', 'tabela', 'campos', 'acao',
                               'antes', 'depois', 'id_usuario', 'nome_usuario', 'registro_id']
                    itens = []
                    for linha in cur.fetchall():
                        item = {k: texto(v) for k, v in zip(colunas, linha)}
                        item['data_hora'] = item['data_hora'].isoformat() if item['data_hora'] else None
                        item['identificacao_legada'] = item['nome_usuario'] is None
                        item['nome_usuario'] = item['nome_usuario'] or 'Rodrigo'
                        itens.append(item)
                    cur.execute('SELECT DISTINCT TABELA FROM HISTORICO ORDER BY TABELA')
                    tabelas = [r[0].strip() for r in cur.fetchall()]
                    return jsonify(sucesso=True, logs=itens, total=total, pagina=pagina,
                                   tamanho=tamanho, paginas=max(1, (total + tamanho - 1) // tamanho), tabelas=tabelas)
        except Exception:
            app.logger.exception('Falha ao consultar o BancoLog.')
            return jsonify(sucesso=False, mensagem='Não foi possível consultar o histórico. Tente novamente.'), 503
