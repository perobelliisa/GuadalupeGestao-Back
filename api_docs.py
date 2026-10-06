"""Swagger UI e inventário OpenAPI das rotas Flask, sem acessar o banco."""
import ast
import inspect
import re
import textwrap

from flask import jsonify, render_template_string, request, url_for


HTML = '''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guadalupe Gestão — API</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css">
</head><body style="margin:0"><div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: {{ spec_url|tojson }}, dom_id: '#swagger-ui',
deepLinking: true, filter: true, withCredentials: true, validatorUrl: null,
presets: [SwaggerUIBundle.presets.apis]});</script></body></html>'''


def _codigo(funcao):
    try:
        return ast.parse(textwrap.dedent(inspect.getsource(funcao)))
    except (OSError, TypeError, SyntaxError):
        return ast.Module(body=[], type_ignores=[])


def _literal(no):
    return no.value if isinstance(no, ast.Constant) else None


def _analisar(funcao):
    """Reconhece os acessos usados neste projeto, inclusive validadores auxiliares."""
    campos = {nome: {} for nome in ('args', 'form', 'files', 'json')}
    codigos, visitados = [], set()
    formatos = set()

    def visitar(atual):
        if atual in visitados:
            return
        visitados.add(atual)
        arvore = _codigo(atual)
        codigos.append(arvore)
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call):
                continue
            chamada = ast.unparse(no.func)
            if chamada == 'dados_requisicao':
                formatos.update(('json', 'form'))
            if chamada == 'request.get_json':
                formatos.add('json')
            if isinstance(no.func, ast.Name):
                auxiliar = atual.__globals__.get(no.func.id)
                if inspect.isfunction(auxiliar) and auxiliar.__module__ in {
                    'function', 'user', 'doacoes', 'emprestimos', 'livro_caixa', 'relatorios', 'documentos'
                }:
                    visitar(auxiliar)
            origem, nome = None, None
            if chamada.startswith('request.') and chamada.endswith(('.get', '.getlist')) and no.args:
                origem = chamada.split('.')[1]
                nome = _literal(no.args[0])
            elif chamada == 'valor' and len(no.args) > 1:
                origem, nome = 'json', _literal(no.args[1])
            elif chamada == 'dados.get' and no.args:
                origem, nome = 'json', _literal(no.args[0])
            elif chamada == 'ler_data' and no.args:
                origem, nome = 'args', _literal(no.args[0])
            if origem in campos and isinstance(nome, str):
                schema = {'type': 'string'}
                if origem == 'files':
                    schema['format'] = 'binary'
                elif chamada.endswith('.getlist'):
                    schema = {'type': 'array', 'items': {'type': 'string'}}
                campos[origem][nome] = schema
        # Acessos diretos a formulários/JSON também são documentados.
        for no in ast.walk(arvore):
            if isinstance(no, ast.Subscript):
                origem = {'request.form': 'form', 'request.args': 'args', 'dados': 'json'}.get(ast.unparse(no.value))
                nome = _literal(no.slice)
                if origem and isinstance(nome, str):
                    campos[origem][nome] = {'type': 'string'}

    visitar(funcao)
    respostas = {}
    for arvore in codigos[:1]:
        for no in ast.walk(arvore):
            if isinstance(no, ast.Return) and isinstance(no.value, ast.Tuple) and len(no.value.elts) > 1:
                status = _literal(no.value.elts[1])
                if isinstance(status, int) and 100 <= status <= 599:
                    respostas[str(status)] = {'description': {
                        200: 'Operação concluída.', 201: 'Registro criado.', 400: 'Dados inválidos.',
                        401: 'Autenticação necessária.', 403: 'Acesso não autorizado.',
                        404: 'Registro não encontrado.', 500: 'Erro interno.'
                    }.get(status, 'Resposta da operação.')}
    return campos, formatos, respostas


def gerar_especificacao(app):
    paths = {}
    for regra in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
        if regra.endpoint in {'static', 'api_documentacao', 'api_openapi'}:
            continue
        funcao = app.view_functions[regra.endpoint]
        campos, formatos, respostas = _analisar(funcao)
        caminho = re.sub(r'<(?:[^:<>]+:)?([^<>]+)>', r'{\1}', regra.rule)
        parametros = []
        for nome, conversor in sorted(regra._converters.items()):
            tipo = {'IntegerConverter': 'integer', 'FloatConverter': 'number'}.get(type(conversor).__name__, 'string')
            parametros.append({'name': nome, 'in': 'path', 'required': True, 'schema': {'type': tipo}})
        parametros.extend({'name': nome, 'in': 'query', 'schema': schema} for nome, schema in campos['args'].items())
        for metodo in sorted(regra.methods - {'HEAD', 'OPTIONS'}):
            operacao = {
                'tags': [funcao.__module__ if funcao.__module__ != 'main' else 'Arquivos'],
                'summary': funcao.__name__.replace('_', ' ').capitalize(),
                'operationId': regra.endpoint + '_' + metodo.lower() + '_' + re.sub(r'\W+', '_', caminho),
                'description': inspect.getdoc(funcao) or 'Campos identificados automaticamente no código. As validações e permissões são aplicadas pelo endpoint.',
                'responses': {'200': {'description': 'Operação concluída.'}, **respostas},
            }
            if parametros:
                operacao['parameters'] = parametros
            if regra.rule not in {'/login', '/arquivos/<path:nome_arquivo>'}:
                operacao['security'] = [{'BearerAuth': []}, {'CookieAuth': []}]
            if metodo in {'POST', 'PUT', 'PATCH'}:
                conteudo = {}
                if 'json' in formatos:
                    conteudo['application/json'] = {'schema': {'type': 'object', 'properties': campos['json']}}
                if campos['form'] or 'form' in formatos or campos['files']:
                    propriedades = dict(campos['json'] if 'form' in formatos else {})
                    propriedades.update(campos['form'])
                    if not campos['files']:
                        conteudo['application/x-www-form-urlencoded'] = {'schema': {'type': 'object', 'properties': propriedades}}
                    propriedades = dict(propriedades, **campos['files'])
                    conteudo['multipart/form-data'] = {'schema': {'type': 'object', 'properties': propriedades}}
                if conteudo:
                    operacao['requestBody'] = {'content': conteudo}
            paths.setdefault(caminho, {})[metodo.lower()] = operacao
    return {
        'openapi': '3.0.3',
        'info': {'title': 'Guadalupe Gestão — API', 'version': '1.0.0', 'description':
                 'API de usuários, projetos, doações, empréstimos, documentos, livro-caixa e relatórios. '
                 'Faça POST /login para autenticar por cookie ou informe o JWT em Authorize. '
                 'Os campos são inferidos do código; tipos e obrigatoriedade condicionais devem ser consultados nas validações. '
                 'Try it out executa operações reais no servidor.'},
        'servers': [{'url': request.script_root or '/'}],
        'paths': paths,
        'components': {'securitySchemes': {
            'BearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'},
            'CookieAuth': {'type': 'apiKey', 'in': 'cookie', 'name': 'access_token',
                           'description': 'Cookie recebido no login; enviado automaticamente pelo navegador.'}
        }},
    }


def registrar_documentacao(app):
    # O registro pode ser solicitado novamente durante a inicializacao.
    if app.extensions.get('guadalupe_api_docs'):
        return
    @app.get('/docs', endpoint='api_documentacao')
    def documentacao():
        return render_template_string(HTML, spec_url=url_for('api_openapi'))

    @app.get('/openapi.json', endpoint='api_openapi')
    def openapi():
        return jsonify(gerar_especificacao(app))

    app.extensions['guadalupe_api_docs'] = True
