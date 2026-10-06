"""Edição de categorias com os dados de auditoria usados pela trigger."""
from flask import jsonify, request
from main import app
from function import abrir_conexao, dados_requisicao, id_usuario_logado, pegar_dispositivo, usuario_pode_gerenciar_doacoes


@app.route('/categorias/<int:id_categoria>', methods=['PUT'])
def editar_categoria(id_categoria):
    """Atualiza nome e descrição da categoria, preservando seu tipo e status."""
    id_usuario = id_usuario_logado()
    if not id_usuario or not usuario_pode_gerenciar_doacoes():
        return jsonify(sucesso=False, mensagem='Acesso não autorizado.'), 403
    dados = dados_requisicao()
    if not hasattr(dados, 'get'):
        return jsonify(sucesso=False, mensagem='Dados inválidos.'), 400
    nome = dados.get('nome')
    descricao = dados.get('descricao', '')
    if not isinstance(nome, str) or not nome.strip() or not isinstance(descricao, str):
        return jsonify(sucesso=False, mensagem='Informe um nome válido e uma descrição em texto.'), 400
    nome, descricao = nome.strip(), descricao.strip()
    conexao, cur = None, None
    try:
        conexao = abrir_conexao()
        cur = conexao.cursor()
        cur.execute('SELECT NOME, STATUS, TIPO, DESCRICAO FROM CATEGORIA WHERE ID_CATEGORIA = ?', (id_categoria,))
        atual = cur.fetchone()
        if not atual:
            return jsonify(sucesso=False, mensagem='Categoria não encontrada.'), 404
        cur.execute('SELECT ID_CATEGORIA FROM CATEGORIA WHERE UPPER(TRIM(NOME)) = UPPER(?) AND TIPO = ? AND ID_CATEGORIA <> ?', (nome, atual[2], id_categoria))
        if cur.fetchone():
            return jsonify(sucesso=False, mensagem='Já existe uma categoria desse tipo com esse nome.'), 409
        cur.execute('''UPDATE CATEGORIA SET NOME = ?, DESCRICAO = ?, ID_USUARIO = ?, DISPOSITIVO = ?
                       WHERE ID_CATEGORIA = ?''', (nome, descricao, id_usuario, pegar_dispositivo()['nome'], id_categoria))
        conexao.commit()
        return jsonify(sucesso=True, categoria={
            'id_categoria': id_categoria, 'id': id_categoria, 'valor': id_categoria,
            'nome': nome, 'descricao': descricao, 'status': atual[1], 'tipo': atual[2]
        }), 200
    except Exception:
        if conexao:
            conexao.rollback()
        app.logger.exception('Erro ao atualizar categoria %s', id_categoria)
        return jsonify(sucesso=False, mensagem='Não foi possível atualizar a categoria. Verifique também o banco de histórico configurado na trigger.'), 500
    finally:
        if cur:
            cur.close()
        if conexao:
            conexao.close()
