# Importa jsonify, request do módulo flask para uso neste arquivo.
from flask import jsonify, request

# Importa app, con do módulo main para uso neste arquivo.
from main import app, con
# Inicia a importação de vários recursos do módulo function.
from function import (
    # Disponibiliza o recurso dados_requisicao para as funções deste módulo.
    dados_requisicao,
    # Disponibiliza o recurso editar_lancamento para as funções deste módulo.
    editar_lancamento,
    # Disponibiliza o recurso excluir_lancamento para as funções deste módulo.
    excluir_lancamento,
    # Disponibiliza o recurso inserir_lancamento para as funções deste módulo.
    inserir_lancamento,
    # Disponibiliza o recurso listar_lancamentos para as funções deste módulo.
    listar_lancamentos,
    # Disponibiliza o recurso usuario_pode_gerenciar_doacoes para as funções deste módulo.
    usuario_pode_gerenciar_doacoes,
    # Disponibiliza o recurso validar_lancamento para as funções deste módulo.
    validar_lancamento,
    # Disponibiliza o recurso texto_json para as funções deste módulo.
    texto_json,
    # Disponibiliza o recurso tipo_lancamento para as funções deste módulo.
    tipo_lancamento
# Fecha a chamada ou a lista de argumentos iniciada anteriormente.
)


# Registra o endpoint '/categorias', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/categorias', methods=['GET'])
# Define a função listar_categorias, que lista as categorias cadastradas para os lançamentos.
def listar_categorias():
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
            SELECT ID_CATEGORIA, NOME, STATUS, TIPO, DESCRICAO -- Inicia a seleção dos campos solicitados.
            FROM CATEGORIA -- Define a tabela CATEGORIA da consulta.
            ORDER BY NOME -- Ordena os registros pelos campos indicados.
        ''')  # Fecha a string SQL usada pela consulta.
        # Inicializa a lista 'categorias' vazia.
        categorias = []
        # Percorre item in cur.fetchall().
        for item in cur.fetchall():
            # Inicia o dicionário 'categoria' que armazenará os dados da resposta.
            categoria = {
                # Preenche o campo 'id_categoria' do objeto ou resposta que está sendo montado.
                'id_categoria': item[0],
                # Preenche o campo 'id' do objeto ou resposta que está sendo montado.
                'id': item[0],
                # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
                'valor': item[0],
                # Preenche o campo 'nome' do objeto ou resposta que está sendo montado.
                'nome': texto_json(item[1]),
                # Preenche o campo 'status' do objeto ou resposta que está sendo montado.
                'status': item[2],
                # Preenche o campo 'tipo' do objeto ou resposta que está sendo montado.
                'tipo': item[3],
                # Preenche o campo 'descricao' do objeto ou resposta que está sendo montado.
                'descricao': texto_json(item[4])
            # Fecha o dicionário que está sendo montado.
            }
            # Adiciona o item atual à lista acumulada.
            categorias.append(categoria)
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'categorias': categorias}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar categorias: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/livro-caixa', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/livro-caixa', methods=['GET'])
# Define a função listar_livro_caixa, que lista os lançamentos do livro caixa.
def listar_livro_caixa():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Atribui a variável 'movimentacoes' o resultado da expressão 'listar_lancamentos(cur)'.
        movimentacoes = listar_lancamentos(cur)
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'movimentacoes': movimentacoes}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar livro-caixa: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/entradas', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/entradas', methods=['POST'])
# Define a função cadastrar_entrada, que cadastra uma entrada no livro caixa.
def cadastrar_entrada():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Obtém os dados da requisição e os armazena em 'lancamento, erro'.
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, 0)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        # Atribui a variável 'id_lancamento' o resultado da expressão 'inserir_lancamento(cur, lancamento, 0)'.
        id_lancamento = inserir_lancamento(cur, lancamento, 0)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'id_livro_caixa': id_lancamento,
                        # Preenche o campo 'id_categoria' do objeto ou resposta que está sendo montado.
                        'id_categoria': lancamento['id_categoria'],
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Entrada cadastrada com sucesso!'}), 201
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar entrada: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/livro-caixa/<int:id_lancamento>', methods=['PUT', 'DELETE'], associando a URL aos métodos HTTP informados.
@app.route('/livro-caixa/<int:id_lancamento>', methods=['PUT', 'DELETE'])
# Define a função gerenciar_livro_caixa, que atualiza ou remove um lançamento do livro caixa.
def gerenciar_livro_caixa(id_lancamento):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Atribui a variável 'tipo' o resultado da expressão 'tipo_lancamento(id_lancamento, cur)'.
        tipo = tipo_lancamento(id_lancamento, cur)
        # Verifica se tipo is None.
        if tipo is None:
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Lançamento não encontrado.'}), 404

        # Seleciona o fluxo de acordo com o método HTTP usado na requisição.
        if request.method == 'DELETE':
            # Chama a exclusão do lançamento identificado e do tipo correspondente.
            excluir_lancamento(cur, id_lancamento, tipo)
            # Confirma definitivamente as alterações feitas na transação.
            con.commit()
            # Retorna uma resposta JSON de sucesso com status HTTP 200.
            return jsonify({'sucesso': True, 'mensagem': 'Lançamento excluído com sucesso!'}), 200

        # Obtém os dados da requisição e os armazena em 'lancamento, erro'.
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, tipo)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        # Chama a atualização do lançamento com o cursor, os dados e o tipo informados.
        editar_lancamento(cur, id_lancamento, lancamento, tipo)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'id_categoria': lancamento['id_categoria'], 'mensagem': 'Lançamento atualizado com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao gerenciar lançamento: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/receitas', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/receitas', methods=['GET'])
# Define a função listar_receitas, que lista as receitas cadastradas.
def listar_receitas():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Atribui a variável 'receitas' o resultado da expressão 'listar_lancamentos(cur, 0)'.
        receitas = listar_lancamentos(cur, 0)
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'receitas': receitas, 'lancamentos': receitas}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar receitas: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/receitas', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/receitas', methods=['POST'])
# Define a função cadastrar_receita, que cadastra uma receita.
def cadastrar_receita():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Obtém os dados da requisição e os armazena em 'lancamento, erro'.
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, 0)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        # Atribui a variável 'id_lancamento' o resultado da expressão 'inserir_lancamento(cur, lancamento, 0)'.
        id_lancamento = inserir_lancamento(cur, lancamento, 0)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'id_livro_caixa': id_lancamento,
                        # Preenche o campo 'id_categoria' do objeto ou resposta que está sendo montado.
                        'id_categoria': lancamento['id_categoria'],
                        # Preenche o campo 'id_receita' do objeto ou resposta que está sendo montado.
                        'id_receita': id_lancamento,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Receita cadastrada com sucesso!'}), 201
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar receita: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/receitas/<int:id_lancamento>', methods=['PUT'], associando a URL aos métodos HTTP informados.
@app.route('/receitas/<int:id_lancamento>', methods=['PUT'])
# Define a função editar_receita, que atualiza uma receita existente.
def editar_receita(id_lancamento):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Obtém os dados da requisição e os armazena em 'lancamento, erro'.
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, 0)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        # Chama a atualização do lançamento com o cursor, os dados e o tipo informados.
        editar_lancamento(cur, id_lancamento, lancamento, 0)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'id_categoria': lancamento['id_categoria'], 'mensagem': 'Receita atualizada com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar receita: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/receitas/<int:id_lancamento>', methods=['DELETE'], associando a URL aos métodos HTTP informados.
@app.route('/receitas/<int:id_lancamento>', methods=['DELETE'])
# Define a função excluir_receita, que remove uma receita existente.
def excluir_receita(id_lancamento):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Chama a exclusão do lançamento identificado e do tipo correspondente.
        excluir_lancamento(cur, id_lancamento, 0)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Receita excluída com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir receita: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/despesas', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/despesas', methods=['GET'])
# Define a função listar_despesas, que lista as despesas cadastradas.
def listar_despesas():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Atribui a variável 'despesas' o resultado da expressão 'listar_lancamentos(cur, 1)'.
        despesas = listar_lancamentos(cur, 1)
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'despesas': despesas, 'lancamentos': despesas}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar despesas: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/despesas', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/despesas', methods=['POST'])
# Define a função cadastrar_despesa, que cadastra uma despesa.
def cadastrar_despesa():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Obtém os dados da requisição e os armazena em 'lancamento, erro'.
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, 1)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        # Atribui a variável 'id_lancamento' o resultado da expressão 'inserir_lancamento(cur, lancamento, 1)'.
        id_lancamento = inserir_lancamento(cur, lancamento, 1)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'id_livro_caixa': id_lancamento,
                        # Preenche o campo 'id_categoria' do objeto ou resposta que está sendo montado.
                        'id_categoria': lancamento['id_categoria'],
                        # Preenche o campo 'id_despesa' do objeto ou resposta que está sendo montado.
                        'id_despesa': id_lancamento,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Despesa cadastrada com sucesso!'}), 201
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar despesa: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/despesas/<int:id_lancamento>', methods=['PUT'], associando a URL aos métodos HTTP informados.
@app.route('/despesas/<int:id_lancamento>', methods=['PUT'])
# Define a função editar_despesa, que atualiza uma despesa existente.
def editar_despesa(id_lancamento):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Obtém os dados da requisição e os armazena em 'lancamento, erro'.
        lancamento, erro = validar_lancamento(dados_requisicao(), cur, 1)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400
        # Chama a atualização do lançamento com o cursor, os dados e o tipo informados.
        editar_lancamento(cur, id_lancamento, lancamento, 1)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'id_categoria': lancamento['id_categoria'], 'mensagem': 'Despesa atualizada com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar despesa: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/despesas/<int:id_lancamento>', methods=['DELETE'], associando a URL aos métodos HTTP informados.
@app.route('/despesas/<int:id_lancamento>', methods=['DELETE'])
# Define a função excluir_despesa, que remove uma despesa existente.
def excluir_despesa(id_lancamento):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Chama a exclusão do lançamento identificado e do tipo correspondente.
        excluir_lancamento(cur, id_lancamento, 1)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Despesa excluída com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir despesa: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()
