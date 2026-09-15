from flask import jsonify, request

from main import app, con
from function import (
    dados_requisicao,
    editar_lancamento,
    excluir_lancamento,
    inserir_lancamento,
    listar_lancamentos,
    usuario_pode_gerenciar_doacoes,
    validar_lancamento,
    texto_json,
    tipo_lancamento
)


@app.route('/categorias', methods=['GET'])
def listar_categorias():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute('''
            SELECT ID_CATEGORIA, NOME, STATUS, TIPO, DESCRICAO
            FROM CATEGORIA
            ORDER BY NOME
        ''')
        categorias = []
        for item in cur.fetchall():
            categoria = {
                'id_categoria': item[0],
                'id': item[0],
                'valor': item[0],
                'nome': texto_json(item[1]),
                'status': item[2],
                'tipo': item[3],
                'descricao': texto_json(item[4])
            }
            categorias.append(categoria)
        return jsonify({'sucesso': True, 'categorias': categorias}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar categorias: {erro}'}), 500
    finally:
        cur.close()


@app.route('/livro-caixa', methods=['GET'])
def listar_livro_caixa():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        movimentacoes = listar_lancamentos(cur)
        return jsonify({'sucesso': True, 'movimentacoes': movimentacoes}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar livro-caixa: {erro}'}), 500
    finally:
        cur.close()


@app.route('/entradas', methods=['POST'])
def cadastrar_entrada():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        lancamento, erro = validar_lancamento(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        id_lancamento = inserir_lancamento(cur, lancamento, 0)
        con.commit()
        return jsonify({'sucesso': True, 'id_livro_caixa': id_lancamento,
                        'mensagem': 'Entrada cadastrada com sucesso!'}), 201
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar entrada: {erro}'}), 500
    finally:
        cur.close()


@app.route('/livro-caixa/<int:id_lancamento>', methods=['PUT', 'DELETE'])
def gerenciar_livro_caixa(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        tipo = tipo_lancamento(id_lancamento, cur)
        if tipo is None:
            return jsonify({'sucesso': False, 'mensagem': 'Lançamento não encontrado.'}), 404

        if request.method == 'DELETE':
            excluir_lancamento(cur, id_lancamento, tipo)
            con.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Lançamento excluído com sucesso!'}), 200

        lancamento, erro = validar_lancamento(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        editar_lancamento(cur, id_lancamento, lancamento, tipo)
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Lançamento atualizado com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao gerenciar lançamento: {erro}'}), 500
    finally:
        cur.close()


@app.route('/receitas', methods=['GET'])
def listar_receitas():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        receitas = listar_lancamentos(cur, 0)
        return jsonify({'sucesso': True, 'receitas': receitas, 'lancamentos': receitas}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar receitas: {erro}'}), 500
    finally:
        cur.close()


@app.route('/receitas', methods=['POST'])
def cadastrar_receita():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        lancamento, erro = validar_lancamento(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        id_lancamento = inserir_lancamento(cur, lancamento, 0)
        con.commit()
        return jsonify({'sucesso': True, 'id_livro_caixa': id_lancamento,
                        'id_receita': id_lancamento,
                        'mensagem': 'Receita cadastrada com sucesso!'}), 201
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar receita: {erro}'}), 500
    finally:
        cur.close()


@app.route('/receitas/<int:id_lancamento>', methods=['PUT'])
def editar_receita(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        lancamento, erro = validar_lancamento(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        editar_lancamento(cur, id_lancamento, lancamento, 0)
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Receita atualizada com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar receita: {erro}'}), 500
    finally:
        cur.close()


@app.route('/receitas/<int:id_lancamento>', methods=['DELETE'])
def excluir_receita(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        excluir_lancamento(cur, id_lancamento, 0)
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Receita excluída com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir receita: {erro}'}), 500
    finally:
        cur.close()


@app.route('/despesas', methods=['GET'])
def listar_despesas():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        despesas = listar_lancamentos(cur, 1)
        return jsonify({'sucesso': True, 'despesas': despesas, 'lancamentos': despesas}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar despesas: {erro}'}), 500
    finally:
        cur.close()


@app.route('/despesas', methods=['POST'])
def cadastrar_despesa():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        lancamento, erro = validar_lancamento(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        id_lancamento = inserir_lancamento(cur, lancamento, 1)
        con.commit()
        return jsonify({'sucesso': True, 'id_livro_caixa': id_lancamento,
                        'id_despesa': id_lancamento,
                        'mensagem': 'Despesa cadastrada com sucesso!'}), 201
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar despesa: {erro}'}), 500
    finally:
        cur.close()


@app.route('/despesas/<int:id_lancamento>', methods=['PUT'])
def editar_despesa(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        lancamento, erro = validar_lancamento(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        editar_lancamento(cur, id_lancamento, lancamento, 1)
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Despesa atualizada com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar despesa: {erro}'}), 500
    finally:
        cur.close()


@app.route('/despesas/<int:id_lancamento>', methods=['DELETE'])
def excluir_despesa(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        excluir_lancamento(cur, id_lancamento, 1)
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Despesa excluída com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir despesa: {erro}'}), 500
    finally:
        cur.close()
