import datetime
import unicodedata
from decimal import Decimal, InvalidOperation

from flask import jsonify, request

from main import app, con
from function import usuario_pode_gerenciar_doacoes, salvar_anexo


def dados_requisicao():
    if request.is_json:
        return request.get_json() or {}
    return request.form


def valor(dados, nome, padrao=None):
    resposta = dados.get(nome, padrao)
    return resposta.strip() if isinstance(resposta, str) else resposta


def texto_sem_acento(texto):
    texto = unicodedata.normalize('NFKD', str(texto))
    return ''.join(letra for letra in texto if not unicodedata.combining(letra)).strip().lower()


def converter_tipo(tipo):
    try:
        return int(tipo)
    except (TypeError, ValueError):
        tipos = {'dinheiro': 0, 'produto': 1, 'produtos': 1, 'servico': 2, 'servicos': 2}
        return tipos.get(texto_sem_acento(tipo))


def converter_valor(numero):
    texto = str(numero).strip().replace('R$', '').replace(' ', '')
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    return Decimal(texto)


def converter_data(data):
    for formato in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(str(data), formato).date()
        except (TypeError, ValueError):
            pass
    raise ValueError('Data inválida.')


def validar_doacao(dados, cur):
    try:
        id_projeto = int(valor(dados, 'id_projeto'))
        doador = valor(dados, 'doador')
        tipo = converter_tipo(valor(dados, 'tipo'))
        quantidade = int(valor(dados, 'quantidade'))
        valor_doacao = converter_valor(valor(dados, 'valor'))
        data = converter_data(valor(dados, 'data', valor(dados, 'dia')))
    except (TypeError, ValueError, InvalidOperation):
        return None, 'Projeto, doador, tipo, quantidade, valor e data devem ser válidos.'

    if not doador:
        return None, 'Doador é obrigatório.'
    if tipo not in (0, 1, 2):
        return None, 'Tipo de doação inválido.'
    if quantidade <= 0 or valor_doacao <= 0:
        return None, 'Quantidade e valor devem ser maiores que zero.'

    cur.execute('SELECT ID_PROJETO FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
    if not cur.fetchone():
        return None, 'Projeto não encontrado.'

    return {
        'id_projeto': id_projeto,
        'doador': doador,
        'tipo': tipo,
        'quantidade': quantidade,
        'valor': valor_doacao,
        'data': data,
        'descricao': valor(dados, 'descricao', '')
    }, None


def doacao_existe(id_doacao, cur):
    cur.execute('SELECT ID_DOACAO FROM DOACAO WHERE ID_DOACAO = ?', (id_doacao,))
    return cur.fetchone() is not None


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
            INNER JOIN PROJETO P ON P.ID_PROJETO = D.ID_PROJETO
            ORDER BY D.DIA DESC, D.ID_DOACAO DESC
        ''')
        doacoes = []
        for item in cur.fetchall():
            doacoes.append({
                'id_doacao': item[0],
                'id_projeto': item[1],
                'projeto': item[2].strip(),
                'doador': item[3].strip(),
                'data': item[4].isoformat() if item[4] else None,
                'dia': item[4].isoformat() if item[4] else None,
                'tipo': item[5],
                'valor': float(item[6]) if item[6] is not None else None,
                'quantidade': item[7],
                'descricao': item[8].strip() if item[8] else ''
            })
        return jsonify({'sucesso': True, 'doacoes': doacoes}), 200
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
    except ValueError as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(erro)}), 400
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
        salvar_anexo(request.files.get('anexo'), 'doacoes', 'doacao', id_doacao)
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Doação atualizada com sucesso!'}), 200
    except ValueError as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'mensagem': str(erro)}), 400
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
        itens = [{'id_item_doacao': row[0], 'id_produto': row[1],
                  'produto': row[2].strip(), 'quantidade': row[3]}
                 for row in cur.fetchall()]
        return jsonify({'sucesso': True, 'itens': itens}), 200
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
        dados = dados_requisicao()
        try:
            id_produto = int(valor(dados, 'id_produto'))
            quantidade = int(valor(dados, 'quantidade'))
        except (TypeError, ValueError):
            return jsonify({'sucesso': False, 'mensagem': 'Produto e quantidade devem ser válidos.'}), 400
        if quantidade <= 0:
            return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser maior que zero.'}), 400
        cur.execute('SELECT ID_PRODUTO FROM PRODUTO WHERE ID_PRODUTO = ?', (id_produto,))
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Produto não encontrado.'}), 400
        cur.execute('''
            INSERT INTO ITEM_DOACAO (ID_DOACAO, ID_PRODUTO, QUANTIDADE)
            VALUES (?, ?, ?) RETURNING ID_ITEM_DOACAO
        ''', (id_doacao, id_produto, quantidade))
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

        dados = dados_requisicao()
        try:
            id_produto = int(valor(dados, 'id_produto'))
            quantidade = int(valor(dados, 'quantidade'))
        except (TypeError, ValueError):
            return jsonify({'sucesso': False, 'mensagem': 'Produto e quantidade devem ser válidos.'}), 400
        if quantidade <= 0:
            return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser maior que zero.'}), 400
        cur.execute('SELECT ID_PRODUTO FROM PRODUTO WHERE ID_PRODUTO = ?', (id_produto,))
        if not cur.fetchone():
            return jsonify({'sucesso': False, 'mensagem': 'Produto não encontrado.'}), 400
        cur.execute('''
            UPDATE ITEM_DOACAO SET ID_PRODUTO = ?, QUANTIDADE = ?
            WHERE ID_ITEM_DOACAO = ?
        ''', (id_produto, quantidade, id_item_doacao))
        con.commit()
        return jsonify({'sucesso': True, 'mensagem': 'Item atualizado com sucesso!'}), 200
    except Exception as erro:
        con.rollback()
        return jsonify({'sucesso': False, 'erro': f'Erro ao gerenciar item: {erro}'}), 500
    finally:
        cur.close()
