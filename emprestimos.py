import datetime
from decimal import Decimal, InvalidOperation

from flask import jsonify, request

from main import app, con
from doacoes import dados_requisicao, valor, converter_valor, converter_data
from function import usuario_pode_gerenciar_doacoes, salvar_anexo


def validar_emprestimo(dados, cur):
    try:
        id_projeto = int(valor(dados, 'id_projeto'))
        id_usuario = int(valor(dados, 'id_usuario'))
        finalidade = valor(dados, 'finalidade')
        origem = valor(dados, 'origem')
        valor_emprestimo = converter_valor(valor(dados, 'valor'))
        parcelas = int(valor(dados, 'parcelas'))
        dia = converter_data(valor(dados, 'data', valor(dados, 'dia')))
        validade = converter_data(valor(dados, 'validade', valor(dados, 'vencimento')))
        devolucao = valor(dados, 'devolucao')
        if devolucao:
            devolucao = converter_data(devolucao)
    except (TypeError, ValueError, InvalidOperation):
        return None, 'Projeto, usuário, finalidade, origem, valor, parcelas e datas devem ser válidos.'

    if not finalidade or not origem:
        return None, 'Finalidade e origem são obrigatórias.'
    if valor_emprestimo <= 0 or parcelas <= 0:
        return None, 'Valor e parcelas devem ser maiores que zero.'
    if validade < dia:
        return None, 'A data de vencimento não pode ser anterior à data do empréstimo.'

    cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
    if not cur.fetchone():
        return None, 'Projeto não encontrado.'
    cur.execute('SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?', (id_usuario,))
    if not cur.fetchone():
        return None, 'Usuário não encontrado.'

    return {
        'id_projeto': id_projeto,
        'id_usuario': id_usuario,
        'finalidade': finalidade,
        'origem': origem,
        'valor': valor_emprestimo,
        'parcelas': parcelas,
        'dia': dia,
        'validade': validade,
        'devolucao': devolucao
    }, None


def emprestimo_existe(id_emprestimo, cur):
    cur.execute('SELECT ID_EMPRESTIMO FROM EMPRESTIMO WHERE ID_EMPRESTIMO = ?', (id_emprestimo,))
    return cur.fetchone() is not None


@app.route('/emprestimos', methods=['GET'])
def listar_emprestimos():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        cur.execute('''
            SELECT E.ID_EMPRESTIMO, E.ID_PROJETO, P.NOME, E.ID_USUARIO,
                   U.NOME, E.FINALIDADE, E.VALOR, E.DIA, E.DEVOLUCAO,
                   E.PARCELAS, E.VALIDADE, E.ORIGEM
            FROM EMPRESTIMO E
            INNER JOIN PROJETO P ON P.ID_PROJETO = E.ID_PROJETO
            INNER JOIN USUARIO U ON U.ID_USUARIO = E.ID_USUARIO
            ORDER BY E.VALIDADE, E.ID_EMPRESTIMO DESC
        ''')
        emprestimos = []
        for item in cur.fetchall():
            emprestimos.append({
                'id_emprestimo': item[0],
                'id_projeto': item[1],
                'projeto': item[2].strip(),
                'id_usuario': item[3],
                'usuario': item[4].strip(),
                'finalidade': item[5].strip() if item[5] else '',
                'valor': float(item[6]) if item[6] is not None else None,
                'data': item[7].isoformat() if item[7] else None,
                'dia': item[7].isoformat() if item[7] else None,
                'devolucao': item[8].isoformat() if item[8] else None,
                'parcelas': item[9],
                'validade': item[10].isoformat() if item[10] else None,
                'vencimento': item[10].isoformat() if item[10] else None,
                'origem': item[11].strip() if item[11] else ''
            })
        return jsonify({'sucesso': True, 'emprestimos': emprestimos}), 200
    finally:
        cur.close()


@app.route('/emprestimos', methods=['POST'])
def cadastrar_emprestimo():
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        emprestimo, erro = validar_emprestimo(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        cur.execute('''
            INSERT INTO EMPRESTIMO
                (ID_PROJETO, ID_USUARIO, FINALIDADE, VALOR, DIA, DEVOLUCAO,
                 PARCELAS, VALIDADE, ORIGEM)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING ID_EMPRESTIMO
        ''', (emprestimo['id_projeto'], emprestimo['id_usuario'], emprestimo['finalidade'],
              emprestimo['valor'], emprestimo['dia'], emprestimo['devolucao'],
              emprestimo['parcelas'], emprestimo['validade'], emprestimo['origem']))
        id_emprestimo = cur.fetchone()[0]
        anexo = salvar_anexo(request.files.get('anexo'), 'emprestimos', 'emprestimo', id_emprestimo)
        con.commit()
        return jsonify({'sucesso': True, 'id_emprestimo': id_emprestimo, 'anexo': anexo,
                        'mensagem': 'Empréstimo cadastrado com sucesso!'}), 201
    except ValueError as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(erro)}), 400
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar empréstimo: {erro}'}), 500
    finally:
        cur.close()


@app.route('/emprestimos/<int:id_emprestimo>', methods=['PUT'])
def editar_emprestimo(id_emprestimo):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if not emprestimo_existe(id_emprestimo, cur):
            return jsonify({'sucesso': False, 'mensagem': 'Empréstimo não encontrado.'}), 404
        emprestimo, erro = validar_emprestimo(dados_requisicao(), cur)
        if erro:
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        cur.execute('''
            UPDATE EMPRESTIMO
            SET ID_PROJETO = ?, ID_USUARIO = ?, FINALIDADE = ?, VALOR = ?, DIA = ?,
                DEVOLUCAO = ?, PARCELAS = ?, VALIDADE = ?, ORIGEM = ?
            WHERE ID_EMPRESTIMO = ?
        ''', (emprestimo['id_projeto'], emprestimo['id_usuario'], emprestimo['finalidade'],
              emprestimo['valor'], emprestimo['dia'], emprestimo['devolucao'],
              emprestimo['parcelas'], emprestimo['validade'], emprestimo['origem'],
              id_emprestimo))
        salvar_anexo(request.files.get('anexo'), 'emprestimos', 'emprestimo', id_emprestimo)
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Empréstimo atualizado com sucesso!'}), 200
    except ValueError as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(erro)}), 400
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar empréstimo: {erro}'}), 500
    finally:
        cur.close()


@app.route('/emprestimos/<int:id_emprestimo>', methods=['DELETE'])
def excluir_emprestimo(id_emprestimo):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if not emprestimo_existe(id_emprestimo, cur):
            return jsonify({'sucesso': False, 'mensagem': 'Empréstimo não encontrado.'}), 404
        cur.execute('DELETE FROM EMPRESTIMO WHERE ID_EMPRESTIMO = ?', (id_emprestimo,))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Empréstimo excluído com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir empréstimo: {erro}'}), 500
    finally:
        cur.close()


@app.route('/emprestimos/<int:id_emprestimo>/anexo', methods=['POST'])
def salvar_anexo_emprestimo(id_emprestimo):
    if not usuario_pode_gerenciar_doacoes():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    cur = con.cursor()
    try:
        if not emprestimo_existe(id_emprestimo, cur):
            return jsonify({'sucesso': False, 'mensagem': 'Empréstimo não encontrado.'}), 404
        anexo = salvar_anexo(request.files.get('anexo'), 'emprestimos', 'emprestimo', id_emprestimo)
        if not anexo:
            return jsonify({'sucesso': False, 'mensagem': 'Selecione um comprovante para enviar.'}), 400
        return jsonify({'sucesso': True, 'anexo': anexo,
                        'mensagem': 'Comprovante salvo com sucesso.'}), 200
    except ValueError as erro:
        return jsonify({'sucesso': False, 'mensagem': str(erro)}), 400
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao salvar comprovante: {erro}'}), 500
    finally:
        cur.close()
