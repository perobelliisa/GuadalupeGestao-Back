from flask import jsonify, request

from main import app, con
from function import (
    dados_requisicao,
    doacao_existe,
    salvar_anexo,
    texto_json,
    numero_json,
    data_json,
    localizar_anexo,
    usuario_pode_gerenciar_doacoes,
    validar_doacao,
    validar_item_doacao,
    valor
)


@app.route('/doacoes', methods=['GET'])
def listar_doacoes():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute('''
            SELECT D.ID_DOACAO, D.ID_PROJETO, P.NOME, D.DOADOR, D.DIA,
                   D.TIPO, D.VALOR, D.QUANTIDADE, D.DESCRICAO
            FROM DOACAO D
            LEFT JOIN PROJETO P ON P.ID_PROJETO = D.ID_PROJETO
            ORDER BY D.DIA DESC, D.ID_DOACAO DESC
        ''')
        doacoes = []
        for item in cur.fetchall():
            projeto = texto_json(item[2])
            doacao = {
                'id_doacao': item[0],
                'id_projeto': item[1],
                'projeto': projeto,
                'projeto_nome': projeto,
                'doador': texto_json(item[3]),
                'data': data_json(item[4]),
                'dia': data_json(item[4]),
                'tipo': item[5],
                'valor': numero_json(item[6]),
                'quantidade': numero_json(item[7]),
                'descricao': texto_json(item[8]),
                'anexo': localizar_anexo('doacoes', 'doacao', item[0])
            }
            doacoes.append(doacao)
        return jsonify({'sucesso': True, 'doacoes': doacoes}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar doações: {erro}'}), 500
    finally:
        cur.close()


@app.route('/doacoes', methods=['POST'])
@app.route('/cadastro_doacao', methods=['POST'])
def cadastrar_doacao():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        doacao, erro = validar_doacao(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        cur.execute('''
            INSERT INTO DOACAO (ID_PROJETO, DOADOR, DIA, TIPO, VALOR, QUANTIDADE, DESCRICAO)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING ID_DOACAO
        ''', (doacao['id_projeto'], doacao['doador'], doacao['data'], doacao['tipo'],
              doacao['valor'], doacao['quantidade'], doacao['descricao']))
        id_doacao = cur.fetchone()[0]
        anexo = salvar_anexo(request.files.get('anexo'), 'doacoes', 'doacao', id_doacao)
        con.commit()
        return jsonify({'sucesso': True, 'id_doacao': id_doacao, 'anexo': anexo,
                        'mensagem': 'Doação cadastrada com sucesso!'}), 201
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar doação: {erro}'}), 500
    finally:
        cur.close()


@app.route('/doacoes/<int:id_doacao>', methods=['PUT'])
def editar_doacao(id_doacao):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if not doacao_existe(id_doacao, cur):
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404

        doacao, erro = validar_doacao(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        cur.execute('''
            UPDATE DOACAO
            SET ID_PROJETO = ?, DOADOR = ?, DIA = ?, TIPO = ?, VALOR = ?,
                QUANTIDADE = ?, DESCRICAO = ?
            WHERE ID_DOACAO = ?
        ''', (doacao['id_projeto'], doacao['doador'], doacao['data'], doacao['tipo'],
              doacao['valor'], doacao['quantidade'], doacao['descricao'], id_doacao))
        anexo = salvar_anexo(request.files.get('anexo'), 'doacoes', 'doacao', id_doacao)
        if not anexo:
            anexo = localizar_anexo('doacoes', 'doacao', id_doacao)
        con.commit()
        return jsonify({'sucesso': True, 'anexo': anexo,
                        'mensagem': 'Doação atualizada com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar doação: {erro}'}), 500
    finally:
        cur.close()


@app.route('/doacoes/<int:id_doacao>', methods=['DELETE'])
def excluir_doacao(id_doacao):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if not doacao_existe(id_doacao, cur):
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404
        cur.execute('DELETE FROM ITEM_DOACAO WHERE ID_DOACAO = ?', (id_doacao,))
        cur.execute('DELETE FROM DOACAO WHERE ID_DOACAO = ?', (id_doacao,))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Doação excluída com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir doação: {erro}'}), 500
    finally:
        cur.close()


@app.route('/doacoes/<int:id_doacao>/itens', methods=['GET'])
def listar_itens_doacao(id_doacao):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if not doacao_existe(id_doacao, cur):
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404
        cur.execute('''
            SELECT I.ID_ITEM_DOACAO, I.ID_PRODUTO, P.NOME, I.QUANTIDADE
            FROM ITEM_DOACAO I
            INNER JOIN PRODUTO P ON P.ID_PRODUTO = I.ID_PRODUTO
            WHERE I.ID_DOACAO = ?
            ORDER BY I.ID_ITEM_DOACAO
        ''', (id_doacao,))
        itens = []
        for row in cur.fetchall():
            itens.append({
                'id_item_doacao': row[0],
                'id_produto': row[1],
                'produto': texto_json(row[2]),
                'quantidade': numero_json(row[3])
            })
        return jsonify({'sucesso': True, 'itens': itens}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar itens: {erro}'}), 500
    finally:
        cur.close()


@app.route('/doacoes/<int:id_doacao>/itens', methods=['POST'])
def cadastrar_item_doacao(id_doacao):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if not doacao_existe(id_doacao, cur):
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404

        item, erro = validar_item_doacao(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        cur.execute('''
            INSERT INTO ITEM_DOACAO (ID_DOACAO, ID_PRODUTO, QUANTIDADE)
            VALUES (?, ?, ?) RETURNING ID_ITEM_DOACAO
        ''', (id_doacao, item['id_produto'], item['quantidade']))
        id_item = cur.fetchone()[0]
        con.commit()
        return jsonify({'sucesso': True, 'id_item_doacao': id_item,
                        'mensagem': 'Item adicionado com sucesso!'}), 201
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar item: {erro}'}), 500
    finally:
        cur.close()


@app.route('/doacoes/itens/<int:id_item_doacao>', methods=['PUT', 'DELETE'])
def gerenciar_item_doacao(id_item_doacao):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute('SELECT ID_ITEM_DOACAO FROM ITEM_DOACAO WHERE ID_ITEM_DOACAO = ?', (id_item_doacao,))
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Item não encontrado.'}), 404

        if request.method == 'DELETE':
            cur.execute('DELETE FROM ITEM_DOACAO WHERE ID_ITEM_DOACAO = ?', (id_item_doacao,))
            con.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Item excluído com sucesso!'}), 200

        item, erro = validar_item_doacao(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        cur.execute('''
            UPDATE ITEM_DOACAO SET ID_PRODUTO = ?, QUANTIDADE = ?
            WHERE ID_ITEM_DOACAO = ?
        ''', (item['id_produto'], item['quantidade'], id_item_doacao))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Item atualizado com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao gerenciar item: {erro}'}), 500
    finally:
        cur.close()
