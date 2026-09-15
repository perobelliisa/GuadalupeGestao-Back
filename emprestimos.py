# Importa jsonify, request do módulo flask para uso neste arquivo.
from flask import jsonify, request

# Importa app, con do módulo main para uso neste arquivo.
from main import app, con
# Inicia a importação de vários recursos do módulo function.
from function import (
    # Disponibiliza o recurso data_json para as funções deste módulo.
    data_json,
    # Disponibiliza o recurso dados_requisicao para as funções deste módulo.
    dados_requisicao,
    # Disponibiliza o recurso emprestimo_existe para as funções deste módulo.
    emprestimo_existe,
    # Disponibiliza o recurso inserir_entrada_automatica para as funções deste módulo.
    inserir_entrada_automatica,
    # Disponibiliza o recurso numero_json para as funções deste módulo.
    numero_json,
    # Disponibiliza o recurso salvar_anexo para as funções deste módulo.
    salvar_anexo,
    # Disponibiliza o recurso texto_json para as funções deste módulo.
    texto_json,
    # Disponibiliza o recurso usuario_pode_gerenciar_doacoes para as funções deste módulo.
    usuario_pode_gerenciar_doacoes,
    # Disponibiliza o recurso validar_emprestimo para as funções deste módulo.
    validar_emprestimo
# Fecha a chamada ou a lista de argumentos iniciada anteriormente.
)


# Registra o endpoint '/emprestimos', methods=['GET'], associando a URL aos métodos HTTP informados.
@app.route('/emprestimos', methods=['GET'])
# Define a função listar_emprestimos, que lista os empréstimos cadastrados.
def listar_emprestimos():
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
            SELECT E.ID_EMPRESTIMO, E.ID_PROJETO, P.NOME, E.ID_USUARIO, -- Inicia a seleção dos campos solicitados.
                   U.NOME, E.FINALIDADE, E.VALOR, E.DIA, E.DEVOLUCAO, -- Continua a instrução SQL com os campos ou condições restantes.
                   E.PARCELAS, E.PARCELAS_PAGAS, E.VALIDADE, E.ORIGEM -- Continua a instrução SQL com os campos ou condições restantes.
            FROM EMPRESTIMO E -- Define a tabela EMPRESTIMO da consulta.
            INNER JOIN PROJETO P ON P.ID_PROJETO = E.ID_PROJETO -- Relaciona apenas registros que possuem correspondência na tabela associada.
            LEFT JOIN USUARIO U ON U.ID_USUARIO = E.ID_USUARIO -- Relaciona registros preservando também os que não possuem correspondência.
            ORDER BY E.VALIDADE, E.ID_EMPRESTIMO DESC -- Ordena os registros pelos campos indicados.
        ''')  # Fecha a string SQL usada pela consulta.
        # Inicializa a lista 'emprestimos' vazia.
        emprestimos = []
        # Percorre item in cur.fetchall().
        for item in cur.fetchall():
            # Converte o texto recebido e o armazena em 'projeto'.
            projeto = texto_json(item[2])
            # Inicia o dicionário 'emprestimo' que armazenará os dados da resposta.
            emprestimo = {
                # Preenche o campo 'id_emprestimo' do objeto ou resposta que está sendo montado.
                'id_emprestimo': item[0],
                # Preenche o campo 'id_projeto' do objeto ou resposta que está sendo montado.
                'id_projeto': item[1],
                # Preenche o campo 'projeto' do objeto ou resposta que está sendo montado.
                'projeto': projeto,
                # Preenche o campo 'projeto_nome' do objeto ou resposta que está sendo montado.
                'projeto_nome': projeto,
                # Preenche o campo 'id_usuario' do objeto ou resposta que está sendo montado.
                'id_usuario': item[3],
                # Preenche o campo 'usuario' do objeto ou resposta que está sendo montado.
                'usuario': texto_json(item[4]),
                # Preenche o campo 'finalidade' do objeto ou resposta que está sendo montado.
                'finalidade': texto_json(item[5]),
                # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
                'valor': numero_json(item[6]),
                # Preenche o campo 'data' do objeto ou resposta que está sendo montado.
                'data': data_json(item[7]),
                # Preenche o campo 'dia' do objeto ou resposta que está sendo montado.
                'dia': data_json(item[7]),
                # Preenche o campo 'devolucao' do objeto ou resposta que está sendo montado.
                'devolucao': data_json(item[8]),
                # Preenche o campo 'parcelas' do objeto ou resposta que está sendo montado.
                'parcelas': item[9],
                # Preenche o campo 'parcelas_pagas' do objeto ou resposta que está sendo montado.
                'parcelas_pagas': item[10] or 0,
                # Preenche o campo 'validade' do objeto ou resposta que está sendo montado.
                'validade': data_json(item[11]),
                # Preenche o campo 'vencimento' do objeto ou resposta que está sendo montado.
                'vencimento': data_json(item[11]),
                # Preenche o campo 'origem' do objeto ou resposta que está sendo montado.
                'origem': texto_json(item[12])
            # Fecha o dicionário que está sendo montado.
            }
            # Adiciona o item atual à lista acumulada.
            emprestimos.append(emprestimo)
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'emprestimos': emprestimos}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao listar empréstimos: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/emprestimos', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/emprestimos', methods=['POST'])
# Define a função cadastrar_emprestimo, que valida e cadastra um novo empréstimo.
def cadastrar_emprestimo():
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Obtém os dados da requisição e os armazena em 'emprestimo, erro'.
        emprestimo, erro = validar_emprestimo(dados_requisicao(), cur)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            INSERT INTO EMPRESTIMO -- Inicia a inclusão de um novo registro.
                (ID_PROJETO, ID_USUARIO, FINALIDADE, VALOR, DIA, DEVOLUCAO, -- Continua a instrução SQL com os campos ou condições restantes.
                 PARCELAS, PARCELAS_PAGAS, VALIDADE, ORIGEM) -- Continua a instrução SQL com os campos ou condições restantes.
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) -- Define os valores que serão gravados.
            RETURNING ID_EMPRESTIMO -- Solicita ao banco o identificador gerado.
        ''', (emprestimo['id_projeto'], emprestimo['id_usuario'], emprestimo['finalidade'],  # Fecha a string SQL usada pela consulta.
              # Passa o valor 'emprestimo['valor'], emprestimo['dia'], emprestimo['devolucao']' como argumento da operação atual.
              emprestimo['valor'], emprestimo['dia'], emprestimo['devolucao'],
              # Conclui a chamada anterior enviando os valores preparados para o banco.
              emprestimo['parcelas'], 0, emprestimo['validade'], emprestimo['origem']))
        # Obtém um valor do primeiro registro e o armazena em 'id_emprestimo'.
        id_emprestimo = cur.fetchone()[0]
        # Cria a entrada correspondente no livro-caixa.
        id_livro_caixa = inserir_entrada_automatica(
            cur, emprestimo['finalidade'], emprestimo['valor'], emprestimo['dia'],
            emprestimo['devolucao'], emprestimo['origem'])
        # Atribui a variável 'anexo' o resultado da expressão 'salvar_anexo(request.files.get('anexo'), 'emprestimos', 'emprestimo', id_emprestimo)'.
        anexo = salvar_anexo(request.files.get('anexo'), 'emprestimos', 'emprestimo', id_emprestimo)
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'id_emprestimo': id_emprestimo,
                        'id_livro_caixa': id_livro_caixa, 'anexo': anexo,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Empréstimo cadastrado com sucesso!'}), 201
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao cadastrar empréstimo: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/emprestimos/<int:id_emprestimo>', methods=['PUT'], associando a URL aos métodos HTTP informados.
@app.route('/emprestimos/<int:id_emprestimo>', methods=['PUT'])
# Define a função editar_emprestimo, que atualiza os dados ou o pagamento de um empréstimo.
def editar_emprestimo(id_emprestimo):
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
            SELECT ID_PROJETO, ID_USUARIO, FINALIDADE, VALOR, DIA, DEVOLUCAO, -- Inicia a seleção dos campos solicitados.
                   PARCELAS, PARCELAS_PAGAS, VALIDADE, ORIGEM -- Continua a instrução SQL com os campos ou condições restantes.
            FROM EMPRESTIMO -- Define a tabela EMPRESTIMO da consulta.
            WHERE ID_EMPRESTIMO = ? -- Filtra os registros conforme a condição informada.
        ''', (id_emprestimo,))  # Fecha a string SQL usada pela consulta.
        # Obtém um valor do primeiro registro e o armazena em 'atual'.
        atual = cur.fetchone()
        # Verifica se a condição atual é falsa.
        if not atual:
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Empréstimo não encontrado.'}), 404

        # Converte os dados recebidos na requisição para um dicionário manipulável.
        dados = dict(dados_requisicao())
        # Converte o valor da expressão para inteiro e o armazena em 'parcelas_atual'.
        parcelas_atual = int(atual[6] or 0)
        # Converte o valor da expressão para inteiro e o armazena em 'parcelas_pagas_atual'.
        parcelas_pagas_atual = int(atual[7] or 0)

        # O controle de pagamento envia apenas a quantidade de parcelas pagas.
        # Verifica se 'parcelas_pagas' in dados and len(dados) == 1.
        if 'parcelas_pagas' in dados and len(dados) == 1:
            # Inicia um bloco protegido para capturar erros durante a operação.
            try:
                # Remove espaços extras das extremidades do texto.
                parcelas_pagas = int(str(dados['parcelas_pagas']).strip())
            # Captura o erro (TypeError, ValueError) e permite tratá-lo.
            except (TypeError, ValueError):
                # Retorna uma resposta JSON de erro com status HTTP 400.
                return jsonify({'sucesso': False, 'mensagem': 'A quantidade de parcelas pagas é inválida.'}), 400
            # Verifica se parcelas_pagas < 0 or parcelas_pagas > parcelas_atual.
            if parcelas_pagas < 0 or parcelas_pagas > parcelas_atual:
                # Retorna uma resposta JSON de erro com status HTTP 400.
                return jsonify({'sucesso': False, 'mensagem': 'As parcelas pagas devem estar entre zero e o total de parcelas.'}), 400
            # Executa no banco a consulta SQL 'UPDATE EMPRESTIMO SET PARCELAS_PAGAS = ? WHERE ID_EMPRESTIMO = ?'.
            cur.execute('UPDATE EMPRESTIMO SET PARCELAS_PAGAS = ? WHERE ID_EMPRESTIMO = ?',
                        # Conclui a chamada anterior enviando os valores preparados para o banco.
                        (parcelas_pagas, id_emprestimo))
            # Confirma definitivamente as alterações feitas na transação.
            con.commit()
            # Inicia a resposta JSON que será devolvida por este endpoint.
            return jsonify({'sucesso': True, 'parcelas_pagas': parcelas_pagas,
                            # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                            'mensagem': 'Pagamento atualizado com sucesso.'}), 200

        # Completa a edição com os dados atuais para permitir alterações parciais.
        # Inicia o dicionário 'dados_completos' que armazenará os dados da resposta.
        dados_completos = {
            # Preenche o campo 'id_projeto' do objeto ou resposta que está sendo montado.
            'id_projeto': atual[0],
            # Preenche o campo 'id_usuario' do objeto ou resposta que está sendo montado.
            'id_usuario': atual[1] or '',
            # Preenche o campo 'finalidade' do objeto ou resposta que está sendo montado.
            'finalidade': atual[2],
            # Preenche o campo 'valor' do objeto ou resposta que está sendo montado.
            'valor': atual[3],
            # Preenche o campo 'dia' do objeto ou resposta que está sendo montado.
            'dia': data_json(atual[4]),
            # Preenche o campo 'devolucao' do objeto ou resposta que está sendo montado.
            'devolucao': data_json(atual[5]),
            # Preenche o campo 'parcelas' do objeto ou resposta que está sendo montado.
            'parcelas': parcelas_atual,
            # Preenche o campo 'validade' do objeto ou resposta que está sendo montado.
            'validade': data_json(atual[8]),
            # Preenche o campo 'origem' do objeto ou resposta que está sendo montado.
            'origem': atual[9]
        # Fecha o dicionário que está sendo montado.
        }
        # Mescla os novos dados no dicionário existente.
        dados_completos.update(dados)
        # Armazena em 'emprestimo, erro' o resultado da validação dos dados.
        emprestimo, erro = validar_emprestimo(dados_completos, cur)
        # Verifica se a validação retornou uma mensagem de erro.
        if erro:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': erro}), 400

        # Atribui a variável 'parcelas_pagas' o resultado da expressão 'parcelas_pagas_atual'.
        parcelas_pagas = parcelas_pagas_atual
        # Verifica se 'parcelas_pagas' in dados.
        if 'parcelas_pagas' in dados:
            # Inicia um bloco protegido para capturar erros durante a operação.
            try:
                # Remove espaços extras das extremidades do texto.
                parcelas_pagas = int(str(dados['parcelas_pagas']).strip())
            # Captura o erro (TypeError, ValueError) e permite tratá-lo.
            except (TypeError, ValueError):
                # Retorna uma resposta JSON de erro com status HTTP 400.
                return jsonify({'sucesso': False, 'mensagem': 'A quantidade de parcelas pagas é inválida.'}), 400
        # Verifica se parcelas_pagas < 0 or parcelas_pagas > emprestimo['parcelas'].
        if parcelas_pagas < 0 or parcelas_pagas > emprestimo['parcelas']:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'As parcelas pagas devem estar entre zero e o total de parcelas.'}), 400

        # Inicia a execução da consulta ou comando SQL no banco de dados.
        cur.execute('''
            UPDATE EMPRESTIMO SET ID_PROJETO = ?, ID_USUARIO = ?, FINALIDADE = ?, -- Inicia a atualização de um registro existente.
                VALOR = ?, DIA = ?, DEVOLUCAO = ?, PARCELAS = ?, PARCELAS_PAGAS = ?, -- Continua a instrução SQL com os campos ou condições restantes.
                VALIDADE = ?, ORIGEM = ? -- Continua a instrução SQL com os campos ou condições restantes.
            WHERE ID_EMPRESTIMO = ? -- Filtra os registros conforme a condição informada.
        ''', (emprestimo['id_projeto'], emprestimo['id_usuario'], emprestimo['finalidade'],  # Fecha a string SQL usada pela consulta.
              # Passa o valor 'emprestimo['valor'], emprestimo['dia'], emprestimo['devolucao']' como argumento da operação atual.
              emprestimo['valor'], emprestimo['dia'], emprestimo['devolucao'],
              # Passa o valor 'emprestimo['parcelas'], parcelas_pagas, emprestimo['validade']' como argumento da operação atual.
              emprestimo['parcelas'], parcelas_pagas, emprestimo['validade'],
              # Conclui a chamada anterior enviando os valores preparados para o banco.
              emprestimo['origem'], id_emprestimo))
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'parcelas_pagas': parcelas_pagas,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Empréstimo atualizado com sucesso.'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao atualizar empréstimo: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/emprestimos/<int:id_emprestimo>', methods=['DELETE'], associando a URL aos métodos HTTP informados.
@app.route('/emprestimos/<int:id_emprestimo>', methods=['DELETE'])
# Define a função excluir_emprestimo, que remove um empréstimo existente.
def excluir_emprestimo(id_emprestimo):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Verifica se a condição emprestimo_existe(id_emprestimo, cur) é falsa.
        if not emprestimo_existe(id_emprestimo, cur):
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Empréstimo não encontrado.'}), 404
        # Executa no banco a consulta SQL 'DELETE FROM EMPRESTIMO WHERE ID_EMPRESTIMO = ?'.
        cur.execute('DELETE FROM EMPRESTIMO WHERE ID_EMPRESTIMO = ?', (id_emprestimo,))
        # Confirma definitivamente as alterações feitas na transação.
        con.commit()
        # Retorna uma resposta JSON de sucesso com status HTTP 200.
        return jsonify({'sucesso': True, 'mensagem': 'Empréstimo excluído com sucesso!'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Desfaz as alterações da transação após uma falha.
        con.rollback()
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao excluir empréstimo: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()


# Registra o endpoint '/emprestimos/<int:id_emprestimo>/anexo', methods=['POST'], associando a URL aos métodos HTTP informados.
@app.route('/emprestimos/<int:id_emprestimo>/anexo', methods=['POST'])
# Define a função salvar_anexo_emprestimo, que salva o comprovante anexado a um empréstimo.
def salvar_anexo_emprestimo(id_emprestimo):
    # Verifica se o usuário possui permissão para acessar este módulo.
    if not usuario_pode_gerenciar_doacoes():
        # Retorna uma resposta JSON de erro com status HTTP 403.
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 403

    # Abre um cursor do banco e o armazena em 'cur'.
    cur = con.cursor()
    # Inicia um bloco protegido para capturar erros durante a operação.
    try:
        # Verifica se a condição emprestimo_existe(id_emprestimo, cur) é falsa.
        if not emprestimo_existe(id_emprestimo, cur):
            # Retorna uma resposta JSON de erro com status HTTP 404.
            return jsonify({'sucesso': False, 'mensagem': 'Empréstimo não encontrado.'}), 404
        # Atribui a variável 'anexo' o resultado da expressão 'salvar_anexo(request.files.get('anexo'), 'emprestimos', 'emprestimo', id_emprestimo)'.
        anexo = salvar_anexo(request.files.get('anexo'), 'emprestimos', 'emprestimo', id_emprestimo)
        # Verifica se a condição anexo é falsa.
        if not anexo:
            # Retorna uma resposta JSON de erro com status HTTP 400.
            return jsonify({'sucesso': False, 'mensagem': 'Selecione um comprovante para enviar.'}), 400
        # Inicia a resposta JSON que será devolvida por este endpoint.
        return jsonify({'sucesso': True, 'anexo': anexo,
                        # Preenche o campo 'mensagem' do objeto ou resposta que está sendo montado.
                        'mensagem': 'Comprovante salvo com sucesso.'}), 200
    # Captura o erro Exception as erro e permite tratá-lo.
    except Exception as erro:
        # Retorna uma resposta JSON de erro com status HTTP 500.
        return jsonify({'sucesso': False, 'erro': f'Erro ao salvar comprovante: {erro}'}), 500
    # Inicia a etapa que sempre será executada para liberar recursos.
    finally:
        # Fecha o cursor para liberar o recurso do banco.
        cur.close()
