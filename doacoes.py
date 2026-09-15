# Importa jsonify, request do módulo flask para uso neste arquivo.
from flask import jsonify, request

# Importa app, con do módulo main para uso neste arquivo.
from main import app, con
# Inicia a importação de vários recursos do módulo function.
from function import (
    # Disponibiliza o recurso dados_requisicao para as funções deste módulo.
    dados_requisicao,
    # Disponibiliza o recurso doacao_existe para as funções deste módulo.
    doacao_existe,
    # Disponibiliza o recurso salvar_anexo para as funções deste módulo.
    salvar_anexo,
    # Disponibiliza o recurso texto_json para as funções deste módulo.
    texto_json,
    # Disponibiliza o recurso numero_json para as funções deste módulo.
    numero_json,
    # Disponibiliza o recurso data_json para as funções deste módulo.
    data_json,
    # Disponibiliza o recurso localizar_anexo para as funções deste módulo.
    localizar_anexo,
    # Disponibiliza o recurso inserir_entrada_automatica para as funções deste módulo.
    inserir_entrada_automatica,
    # Disponibiliza o recurso usuario_pode_gerenciar_doacoes para as funções deste módulo.
    usuario_pode_gerenciar_doacoes,
    # Disponibiliza o recurso validar_doacao para as funções deste módulo.
    validar_doacao,
    # Disponibiliza o recurso validar_item_doacao para as funções deste módulo.
    validar_item_doacao,
    # Disponibiliza o recurso valor para as funções deste módulo.
    valor
# Fecha a chamada ou a lista de argumentos iniciada anteriormente.
)


# Registra o endpoint '/doacoes', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/doacoes', methods=['GET'])
# Define a função listar_doacoes, que lista as doações cadastradas.
def listar_doacoes():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            SELECT D.ID_DOACAO, D.ID_PROJETO, P.NOME, D.DOADOR, D.DIA, -- Inicia a seleção dos campos solicitados.
                   D.TIPO, D.VALOR, D.QUANTIDADE, D.DESCRICAO -- Continua a instrução SQL com os campos ou condições restantes.
            FROM DOACAO D -- Define a tabela DOACAO da consulta.
            LEFT JOIN PROJETO P ON P.ID_PROJETO = D.ID_PROJETO -- Relaciona registros preservando também os que não possuem correspondência.
            ORDER BY D.DIA DESC, D.ID_DOACAO DESC -- Ordena os registros pelos campos indicados.
        ''')  # Fecha a string SQL usada pela consulta.
        # Inicializa a lista 'doacoes' vazia.
        doacoes = []
        # Percorre item in cur.fetchall().
        for item in cur.fetchall():
            # Converte o texto recebido e o armazena em 'projeto'.
            projeto = texto_json(item[2])
            # Inicia o dicionário 'doacao' que armazenará os dados da resposta.
            doacao = {
                # Preenche o campo 'id_doacao' do objeto ou resposta que está sendo montado.
                'id_doacao': item[0],
                # Preenche o campo 'id_projeto' do objeto ou resposta que está sendo montado.
                'id_projeto': item[1],
                # Preenche o campo 'projeto' do objeto ou resposta que está sendo montado.
                'projeto': projeto,
                # Preenche o campo 'projeto_nome' do objeto ou resposta que está sendo montado.
                'projeto_nome': projeto,
                # Preenche o campo 'doador' do objeto ou resposta que está sendo montado.
                'doador': texto_json(item[3]),
                # Preenche o campo 'data' do objeto ou resposta que está sendo montado.
                'data': data_json(item[4]),
                # Preenche o campo 'dia' do objeto ou resposta que está sendo montado.
                'dia': data_json(item[4]),
                # Preenche o campo 'tipo' do objeto ou resposta que está sendo montado.
                'tipo': item[5],
                # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
                'valor': numero_json(item[6]),
                # Preenche o campo 'quantidade' do objeto ou resposta que está sendo montado.
                'quantidade': numero_json(item[7]),
                # Preenche o campo 'descricao' do objeto ou resposta que está sendo montado.
                'descricao': texto_json(item[8]),
                # Preenche o campo 'anexo' do objeto ou resposta que está sendo montado.
                'anexo': localizar_anexo('doacoes', 'doacao', item[0])
            # Fecha o dicionário que está sendo montado.
            }
            # Adiciona o item atual à lista acumulada.
            doacoes.append(doacao)
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'doacoes': doacoes}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar doações: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/doacoes', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/doacoes', methods=['POST'])
# Registra o endpoint '/cadastro_doacao', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/cadastro_doacao', methods=['POST'])
# Define a função cadastrar_doacao, que valida e cadastra uma nova doação.
def cadastrar_doacao():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Obtém os dados da requisição e os armazena em 'doacao, erro'.
        doacao, erro = validar_doacao(dados_requisicao(), cur)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            INSERT INTO DOACAO (ID_PROJETO, DOADOR, DIA, TIPO, VALOR, QUANTIDADE, DESCRICAO) -- Inicia a inclusão de um novo registro.
            VALUES (?, ?, ?, ?, ?, ?, ?) -- Define os valores que serão gravados.
            RETURNING ID_DOACAO -- Solicita ao banco o identificador gerado.
        ''', (doacao['id_projeto'], doacao['doador'], doacao['data'], doacao['tipo'],  # Fecha a string SQL usada pela consulta.
              # Conclui a chamada anterior enviando os valores preparados para o banco.
              doacao['valor'], doacao['quantidade'], doacao['descricao']))
        # Obtém um valor do primeiro registro e o armazena em 'id_doacao'.
        id_doacao = cur.fetchone()[0]
        # Cria a entrada correspondente no livro-caixa.
        id_livro_caixa = inserir_entrada_automatica(
            cur, 'Doação', doacao['valor'], doacao['data'], None, doacao['doador'])
        # Atribui a variável 'anexo' o resultado da expressão 'salvar_anexo(request.files.get('anexo'), 'doacoes', 'doacao', id_doacao)'.
        anexo = salvar_anexo(request.files.get('anexo'), 'doacoes', 'doacao', id_doacao)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'id_doacao': id_doacao,
                        'id_livro_caixa': id_livro_caixa, 'anexo': anexo,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Doação cadastrada com sucesso!'}), 201
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar doação: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/doacoes/<int:id_doacao>', methods=['PUT'], associando a URL aos métodos HTTP informados.
@app.route('/doacoes/<int:id_doacao>', methods=['PUT'])
# Define a função editar_doacao, que atualiza uma doação existente.
def editar_doacao(id_doacao):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Verifica se a condição doacao_existe(id_doacao, cur) é falsa.
        if not doacao_existe(id_doacao, cur):
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404

        # Obtém os dados da requisição e os armazena em 'doacao, erro'.
        doacao, erro = validar_doacao(dados_requisicao(), cur)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            UPDATE DOACAO -- Inicia a atualização de um registro existente.
            SET ID_PROJETO = ?, DOADOR = ?, DIA = ?, TIPO = ?, VALOR = ?, -- Define os campos que receberão os novos valores.
                QUANTIDADE = ?, DESCRICAO = ? -- Continua a instrução SQL com os campos ou condições restantes.
            WHERE ID_DOACAO = ? -- Filtra os registros conforme a condição informada.
        ''', (doacao['id_projeto'], doacao['doador'], doacao['data'], doacao['tipo'],  # Fecha a string SQL usada pela consulta.
              # Conclui a chamada anterior enviando os valores preparados para o banco.
              doacao['valor'], doacao['quantidade'], doacao['descricao'], id_doacao))
        # Atribui a variável 'anexo' o resultado da expressão 'salvar_anexo(request.files.get('anexo'), 'doacoes', 'doacao', id_doacao)'.
        anexo = salvar_anexo(request.files.get('anexo'), 'doacoes', 'doacao', id_doacao)
        # Verifica se a condição anexo é falsa.
        if not anexo:
            # Atribui a variável 'anexo' o resultado da expressão 'localizar_anexo('doacoes', 'doacao', id_doacao)'.
            anexo = localizar_anexo('doacoes', 'doacao', id_doacao)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'anexo': anexo,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Doação atualizada com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar doação: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/doacoes/<int:id_doacao>', methods=['DELETE'], associando a URL aos métodos HTTP informados.
@app.route('/doacoes/<int:id_doacao>', methods=['DELETE'])
# Define a função excluir_doacao, que remove uma doação existente.
def excluir_doacao(id_doacao):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Verifica se a condição doacao_existe(id_doacao, cur) é falsa.
        if not doacao_existe(id_doacao, cur):
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404
        # Executa no banco a consulta SQL 'DELETE FROM ITEM_DOACAO WHERE ID_DOACAO = ?'.
        cur.execute('DELETE FROM ITEM_DOACAO WHERE ID_DOACAO = ?', (id_doacao,))
        # Executa no banco a consulta SQL 'DELETE FROM DOACAO WHERE ID_DOACAO = ?'.
        cur.execute('DELETE FROM DOACAO WHERE ID_DOACAO = ?', (id_doacao,))
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Doação excluída com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir doação: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/doacoes/<int:id_doacao>/itens', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/doacoes/<int:id_doacao>/itens', methods=['GET'])
# Define a função listar_itens_doacao, que lista os produtos pertencentes a uma doação.
def listar_itens_doacao(id_doacao):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Verifica se a condição doacao_existe(id_doacao, cur) é falsa.
        if not doacao_existe(id_doacao, cur):
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404
        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            SELECT I.ID_ITEM_DOACAO, I.ID_PRODUTO, P.NOME, I.QUANTIDADE -- Inicia a seleção dos campos solicitados.
            FROM ITEM_DOACAO I -- Define a tabela ITEM_DOACAO da consulta.
            INNER JOIN PRODUTO P ON P.ID_PRODUTO = I.ID_PRODUTO -- Relaciona apenas registros que possuem correspondência na tabela associada.
            WHERE I.ID_DOACAO = ? -- Filtra os registros conforme a condição informada.
            ORDER BY I.ID_ITEM_DOACAO -- Ordena os registros pelos campos indicados.
        ''', (id_doacao,))  # Fecha a string SQL usada pela consulta.
        # Inicializa a lista 'itens' vazia.
        itens = []
        # Percorre row in cur.fetchall().
        for row in cur.fetchall():
            # Adiciona o item atual à lista acumulada.
            itens.append({
                # Preenche o campo 'id_item_doacao' do objeto ou resposta que está sendo montado.
                'id_item_doacao': row[0],
                # Preenche o campo 'id_produto' do objeto ou resposta que está sendo montado.
                'id_produto': row[1],
                # Preenche o campo 'produto' do objeto ou resposta que está sendo montado.
                'produto': texto_json(row[2]),
                # Preenche o campo 'quantidade' do objeto ou resposta que está sendo montado.
                'quantidade': numero_json(row[3])
            # Fecha a estrutura da resposta e conclui o retorno HTTP.
            })
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'itens': itens}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar itens: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/doacoes/<int:id_doacao>/itens', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/doacoes/<int:id_doacao>/itens', methods=['POST'])
# Define a função cadastrar_item_doacao, que valida e adiciona um produto a uma doação.
def cadastrar_item_doacao(id_doacao):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Verifica se a condição doacao_existe(id_doacao, cur) é falsa.
        if not doacao_existe(id_doacao, cur):
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Doação não encontrada.'}), 404

        # Obtém os dados da requisição e os armazena em 'item, erro'.
        item, erro = validar_item_doacao(dados_requisicao(), cur)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            INSERT INTO ITEM_DOACAO (ID_DOACAO, ID_PRODUTO, QUANTIDADE) -- Inicia a inclusão de um novo registro.
            VALUES (?, ?, ?) RETURNING ID_ITEM_DOACAO -- Define os valores que serão gravados.
        ''', (id_doacao, item['id_produto'], item['quantidade']))  # Fecha a string SQL usada pela consulta.
        # Obtém um valor do primeiro registro e o armazena em 'id_item'.
        id_item = cur.fetchone()[0]
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'id_item_doacao': id_item,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Item adicionado com sucesso!'}), 201
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar item: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/doacoes/itens/<int:id_item_doacao>', methods=['PUT', 'DELETE'], associando a URL aos métodos HTTP informados.
@app.route('/doacoes/itens/<int:id_item_doacao>', methods=['PUT', 'DELETE'])
# Define a função gerenciar_item_doacao, que atualiza ou remove um produto de uma doação.
def gerenciar_item_doacao(id_item_doacao):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Executa no banco a consulta SQL 'SELECT ID_ITEM_DOACAO FROM ITEM_DOACAO WHERE ID_ITEM_DOACAO = ?'.
        cur.execute('SELECT ID_ITEM_DOACAO FROM ITEM_DOACAO WHERE ID_ITEM_DOACAO = ?', (id_item_doacao,))
        # Verifica se a condição cur.fetchone() é falsa.
        if not cur.fetchone():
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Item não encontrado.'}), 404

        # Seleciona o fluxo de acordo com o método HTTP usado na requisição.
        if request.method == 'DELETE':
            # Executa no banco a consulta SQL 'DELETE FROM ITEM_DOACAO WHERE ID_ITEM_DOACAO = ?'.
            cur.execute('DELETE FROM ITEM_DOACAO WHERE ID_ITEM_DOACAO = ?', (id_item_doacao,))
            # Confirma definitivamente as alterações feitas na transação.
            con.commit()
            # Retorna uma resposta JSON de sucesso com status HTTP 200.
            return jsonify({'sucesso': True, 'mensagem': 'Item excluído com sucesso!'}), 200

        # Obtém os dados da requisição e os armazena em 'item, erro'.
        item, erro = validar_item_doacao(dados_requisicao(), cur)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            UPDATE ITEM_DOACAO SET ID_PRODUTO = ?, QUANTIDADE = ? -- Inicia a atualização de um registro existente.
            WHERE ID_ITEM_DOACAO = ? -- Filtra os registros conforme a condição informada.
        ''', (item['id_produto'], item['quantidade'], id_item_doacao))  # Fecha a string SQL usada pela consulta.
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Item atualizado com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao gerenciar item: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()
