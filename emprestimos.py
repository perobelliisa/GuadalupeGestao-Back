from flask import jsonify, request

from main import app, con
from function import (
    data_json,
    dados_requisicao,
    emprestimo_existe,
    numero_json,
    salvar_anexo,
    texto_json,
    usuario_pode_gerenciar_doacoes,
    validar_emprestimo
)


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
            LEFT JOIN USUARIO U ON U.ID_USUARIO = E.ID_USUARIO
            ORDER BY E.VALIDADE, E.ID_EMPRESTIMO DESC
        ''')
        emprestimos = []
        for item in cur.fetchall():
            projeto = texto_json(item[2])
            emprestimo = {
                'id_emprestimo': item[0],
                'id_projeto': item[1],
                'projeto': projeto,
                'projeto_nome': projeto,
                'id_usuario': item[3],
                'usuario': texto_json(item[4]),
                'finalidade': texto_json(item[5]),
                'valor': numero_json(item[6]),
                'data': data_json(item[7]),
                'dia': data_json(item[7]),
                'devolucao': data_json(item[8]),
                'parcelas': item[9],
                'validade': data_json(item[10]),
                'vencimento': data_json(item[10]),
                'origem': texto_json(item[11])
            }
            emprestimos.append(emprestimo)
        return jsonify({'sucesso': True, 'emprestimos': emprestimos}), 200
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar empréstimos: {erro}'}), 500
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
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar empréstimo: {erro}'}), 500
    finally:
        cur.close()


@app.route('/emprestimos/<int:id_emprestimo>', methods=['PUT'])
def editar_emprestimo(id_emprestimo):
    return jsonify({'sucesso': False,
                    'mensagem': 'Empréstimos não podem ser alterados depois de criados.'}), 405


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
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao salvar comprovante: {erro}'}), 500
    finally:
        cur.close()
