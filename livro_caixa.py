from flask import jsonify
from decimal import InvalidOperation

from main import app, con
from doacoes import dados_requisicao, valor, converter_valor, converter_data
from function import usuario_pode_gerenciar_doacoes


def validar_lancamento(dados, cur, tipo):
    try:
        id_categoria = int(valor(dados, 'id_categoria'))
        descricao = valor(dados, 'descricao')
        valor_lancamento = converter_valor(valor(dados, 'valor'))
        data = converter_data(valor(dados, 'data', valor(dados, 'dia')))
    except (TypeError, ValueError, InvalidOperation):
        return None, 'Categoria, descrição, valor e data devem ser válidos.'

    if not descricao:
        return None, 'Descrição é obrigatória.'
    if valor_lancamento <= 0:
        return None, 'Valor deve ser maior que zero.'

    cur.execute('SELECT ID_CATEGORIA FROM CATEGORIA WHERE ID_CATEGORIA = ?', (id_categoria,))
    if not cur.fetchone():
        return None, 'Categoria não encontrada.'

    return {
        'id_categoria': id_categoria,
        'descricao': descricao,
        'valor': valor_lancamento,
        'data': data,
        'vencimento': converter_data(valor(dados, 'vencimento')) if valor(dados, 'vencimento') else None,
        'fornecedor': valor(dados, 'fornecedor', ''),
        'status': int(valor(dados, 'status', 0) or 0),
        'recorrencia': int(valor(dados, 'recorrencia', 0) or 0),
        'origem': valor(dados, 'origem', ''),
        'forma_pagamento': int(valor(dados, 'forma_pagamento', 0) or 0),
        'observacao': valor(dados, 'observacao', '')
    }, None


def listar_lancamentos(tipo, nome):
    cur = con.cursor()
    try:
        cur.execute('''
            SELECT L.ID_LIVRO_CAIXA, L.ID_CATEGORIA, C.NOME, L.DESCRICAO,
                   L.TIPO, L.VALOR, L.DIA, L.VENCIMENTO, L.FORNECEDOR,
                   L.STATUS, L.RECORRENCIA, L.ORIGEM, L.FORMA_PAGAMENTO,
                   L.OBSERVACAO
            FROM LIVRO_CAIXA L
            INNER JOIN CATEGORIA C ON C.ID_CATEGORIA = L.ID_CATEGORIA
            WHERE L.TIPO = ?
            ORDER BY L.DIA DESC, L.ID_LIVRO_CAIXA DESC
        ''', (tipo,))
        lancamentos = []
        for item in cur.fetchall():
            lancamento = {
                'id_livro_caixa': item[0],
                'id_categoria': item[1],
                'categoria': item[2].strip(),
                'descricao': item[3].strip() if item[3] else '',
                'tipo': item[4],
                'valor': float(item[5]) if item[5] is not None else None,
                'data': item[6].isoformat() if item[6] else None,
                'dia': item[6].isoformat() if item[6] else None,
                'vencimento': item[7].isoformat() if item[7] else None,
                'fornecedor': item[8].strip() if item[8] else '',
                'status': item[9],
                'recorrencia': item[10],
                'origem': item[11].strip() if item[11] else '',
                'forma_pagamento': item[12],
                'observacao': item[13].strip() if item[13] else ''
            }
            if tipo == 0:
                lancamento['id_receita'] = item[0]
            else:
                lancamento['id_despesa'] = item[0]
            lancamentos.append(lancamento)
        return jsonify({'sucesso': True, nome: lancamentos, 'lancamentos': lancamentos}), 200
    finally:
        cur.close()


def cadastrar_lancamento(tipo):
    cur = con.cursor()
    try:
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, tipo)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        cur.execute('''
            INSERT INTO LIVRO_CAIXA
                (ID_CATEGORIA, DESCRICAO, TIPO, VALOR, DIA, VENCIMENTO,
                 FORNECEDOR, STATUS, RECORRENCIA, ORIGEM, FORMA_PAGAMENTO, OBSERVACAO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING ID_LIVRO_CAIXA
        ''', (lancamento['id_categoria'], lancamento['descricao'], tipo,
              lancamento['valor'], lancamento['data'], lancamento['vencimento'],
              lancamento['fornecedor'], lancamento['status'], lancamento['recorrencia'],
              lancamento['origem'], lancamento['forma_pagamento'], lancamento['observacao']))
        id_lancamento = cur.fetchone()[0]
        con.commit()
        resposta = {'sucesso': True, 'id_livro_caixa': id_lancamento,
                    'mensagem': 'Lançamento cadastrado com sucesso!'}
        resposta['id_receita' if tipo == 0 else 'id_despesa'] = id_lancamento
        return jsonify(resposta), 201
    except (ValueError, TypeError) as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(erro)}), 400
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar lançamento: {erro}'}), 500
    finally:
        cur.close()


def editar_lancamento(id_lancamento, tipo):
    cur = con.cursor()
    try:
        cur.execute('SELECT ID_LIVRO_CAIXA FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ? AND TIPO = ?',
                    (id_lancamento, tipo))
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Lançamento não encontrado.'}), 404
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, tipo)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        cur.execute('''
            UPDATE LIVRO_CAIXA
            SET ID_CATEGORIA = ?, DESCRICAO = ?, VALOR = ?, DIA = ?, VENCIMENTO = ?,
                FORNECEDOR = ?, STATUS = ?, RECORRENCIA = ?, ORIGEM = ?,
                FORMA_PAGAMENTO = ?, OBSERVACAO = ?
            WHERE ID_LIVRO_CAIXA = ? AND TIPO = ?
        ''', (lancamento['id_categoria'], lancamento['descricao'], lancamento['valor'],
              lancamento['data'], lancamento['vencimento'], lancamento['fornecedor'],
              lancamento['status'], lancamento['recorrencia'], lancamento['origem'],
              lancamento['forma_pagamento'], lancamento['observacao'], id_lancamento, tipo))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Lançamento atualizado com sucesso!'}), 200
    except (ValueError, TypeError) as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(erro)}), 400
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar lançamento: {erro}'}), 500
    finally:
        cur.close()


def excluir_lancamento(id_lancamento, tipo):
    cur = con.cursor()
    try:
        cur.execute('DELETE FROM LIVRO_CAIXA WHERE ID_LIVRO_CAIXA = ? AND TIPO = ?',
                    (id_lancamento, tipo))
        if cur.rowcount == 0:
            return jsonify({'sucesso': False, 'mensagem': 'Lançamento não encontrado.'}), 404
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Lançamento excluído com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir lançamento: {erro}'}), 500
    finally:
        cur.close()


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
        categorias = [{'id_categoria': item[0], 'nome': item[1].strip(), 'status': item[2],
                       'tipo': item[3], 'descricao': item[4].strip() if item[4] else ''}
                      for item in cur.fetchall()]
        return jsonify({'sucesso': True, 'categorias': categorias}), 200
    finally:
        cur.close()


@app.route('/receitas', methods=['GET'])
def listar_receitas():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
        return listar_lancamentos(0, 'receitas')


@app.route('/receitas', methods=['POST'])
def cadastrar_receita():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
    return cadastrar_lancamento(0)


@app.route('/receitas/<int:id_lancamento>', methods=['PUT'])
def editar_receita(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
    return editar_lancamento(id_lancamento, 0)


@app.route('/receitas/<int:id_lancamento>', methods=['DELETE'])
def excluir_receita(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
    return excluir_lancamento(id_lancamento, 0)


@app.route('/despesas', methods=['GET'])
def listar_despesas():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
        return listar_lancamentos(1, 'despesas')


@app.route('/despesas', methods=['POST'])
def cadastrar_despesa():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
    return cadastrar_lancamento(1)


@app.route('/despesas/<int:id_lancamento>', methods=['PUT'])
def editar_despesa(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
    return editar_lancamento(id_lancamento, 1)


@app.route('/despesas/<int:id_lancamento>', methods=['DELETE'])
def excluir_despesa(id_lancamento):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403
    return excluir_lancamento(id_lancamento, 1)
