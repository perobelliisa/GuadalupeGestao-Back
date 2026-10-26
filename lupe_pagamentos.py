"""Ações de pagamento que a Lupe pode oferecer usando o backend do Guadalupe.

Em palavras simples: a Lupe entende o pedido e prepara uma cobrança. O código
Pix de verdade vem da Arkhé; a Lupe só mostra o código que recebeu do backend.
"""
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from arkhe import validar_dados
from lupe_acoes import ErroAcao, assinatura, inteiro, normalizar

BASE = '/integracoes/arkhe'
CAMPOS_PIX = {'id', 'id_cobranca', 'doador', 'valor', 'valor_livre', 'id_projeto', 'descricao', 'situacao', 'id_doacao', 'criado_em', 'pago_em'}


def cobrancas(sistema):
    # Pede ao backend a lista de cobranças já registradas.
    itens = sistema.chamar(BASE + '/cobrancas').get('cobrancas')
    if not isinstance(itens, list):
        raise ErroAcao('Não consegui consultar os pagamentos da Arkhé.', 502)
    return itens


def consultar_pagamentos(sistema, argumentos):
    # Consulta pagamentos e filtra por tipo, situação, busca ou período.
    # A Lupe pede ao Guadalupe os pagamentos registrados. Se a pessoa solicitar
    # uma atualização, o backend também consulta a Arkhé para conferir o estado.
    if not isinstance(argumentos, dict): raise ErroAcao('Informe qual pagamento deseja consultar.')
    tipo = argumentos.get('tipo')
    if tipo not in {'despesa', 'emprestimo', 'doacao_pix'}:
        raise ErroAcao('Escolha despesas, empréstimos ou doações por Pix.')
    atualizar = argumentos.get('atualizar', False)
    incluir_codigo = argumentos.get('incluir_codigo', False)
    if type(atualizar) is not bool or type(incluir_codigo) is not bool:
        raise ErroAcao('Informe filtros válidos para a consulta.')
    # Não reoferece um código de pagamento que já foi recebido no banco.
    atualizar = atualizar or incluir_codigo
    identificador = argumentos.get('id')
    if identificador is not None and (type(identificador) not in (str, int) or len(str(identificador)) > 100):
        raise ErroAcao('Informe um identificador de pagamento válido.')
    if (atualizar or incluir_codigo) and (tipo != 'doacao_pix' or identificador is None):
        raise ErroAcao('Consulte a lista e escolha uma cobrança Pix para conferir na Arkhé ou obter o código.')
    if tipo == 'doacao_pix':
        registros = cobrancas(sistema)
        if identificador is not None:
            registros = [item for item in registros if str(identificador) in (str(item.get('id')), str(item.get('id_cobranca')))]
    else:
        registros = sistema.registros(tipo)
        if identificador is not None:
            chave = 'id_livro_caixa' if tipo == 'despesa' else 'id_emprestimo'
            registros = [item for item in registros if str(item.get(chave)) == str(identificador)]
        registros = [{**item, 'situacao': ('pago' if item.get('status') == 1 else 'pendente') if tipo == 'despesa' else ('quitado' if item.get('parcelas', 0) > 0 and item.get('parcelas_pagas', 0) >= item['parcelas'] else 'pendente')} for item in registros]
    retorno = {'tipo': tipo, 'fonte': 'registros_do_sistema', 'consulta_bancaria': False}
    if atualizar:
        if len(registros) != 1: raise ErroAcao('Escolha uma cobrança existente e sem ambiguidade para consultar.')
        identificador_local = str(UUID(registros[0]['id']))
        dados = sistema.chamar(BASE + '/cobrancas/' + identificador_local + '/status')
        if not isinstance(dados.get('cobranca'), dict): raise ErroAcao('A consulta não retornou o pagamento esperado.', 502)
        registros = [dados['cobranca']]
        retorno.update({k: dados.get(k) for k in ('fonte', 'situacao_registrada', 'recebimento_registrado', 'consultado_em')})
        retorno['consulta_bancaria'] = dados.get('fonte') == 'consulta_arkhe'
    busca = normalizar(argumentos.get('busca', '')).strip()
    if busca:
        registros = [item for item in registros if busca in normalizar(' '.join(str(item.get(k) or '') for k in ('doador', 'descricao', 'finalidade', 'fornecedor', 'origem')))]
    for filtro, sinal in [('inicio', 1), ('fim', -1)]:
        if argumentos.get(filtro):
            try: dia = datetime.strptime(argumentos[filtro], '%Y-%m-%d').date().isoformat()
            except (TypeError, ValueError): raise ErroAcao('Informe uma data válida no formato ano-mês-dia.') from None
            def dentro(item):
                data = str(item.get('dia') or item.get('criado_em') or '')[:10]
                return bool(data) and (data >= dia if sinal == 1 else data <= dia)
            registros = [item for item in registros if dentro(item)]
    if argumentos.get('situacao'):
        situacao = argumentos['situacao']
        if tipo == 'emprestimo' and situacao == 'pago': situacao = 'quitado'
        if tipo == 'despesa' and situacao == 'quitado': situacao = 'pago'
        registros = [item for item in registros if item.get('situacao') == situacao]
    if argumentos.get('forma_pagamento') is not None:
        if tipo != 'despesa': raise ErroAcao('O filtro de forma de pagamento se aplica às despesas.')
        forma = argumentos['forma_pagamento']
        if type(forma) is not int or not 0 <= forma <= 5: raise ErroAcao('Informe uma forma de pagamento válida.')
        registros = [item for item in registros if item.get('forma_pagamento') == forma]
    if argumentos.get('id_projeto') is not None:
        projeto = argumentos['id_projeto']
        if type(projeto) is not int or projeto < 0: raise ErroAcao('Informe um projeto válido ou 0 para a missão.')
        registros = [item for item in registros if (item.get('conta', item.get('id_projeto')) or 0) == projeto]
    resumo = {}
    for item in registros:
        grupo = resumo.setdefault(item.get('situacao', 'verificar'), {'quantidade': 0, 'total_com_valor_definido': Decimal(0), 'quantidade_sem_valor_definido': 0})
        grupo['quantidade'] += 1
        if item.get('valor') is None: grupo['quantidade_sem_valor_definido'] += 1
        else: grupo['total_com_valor_definido'] += Decimal(str(item['valor']))
    for grupo in resumo.values(): grupo['total_com_valor_definido'] = str(grupo['total_com_valor_definido'].quantize(Decimal('.01')))
    pagina, limite = argumentos.get('pagina', 1), argumentos.get('limite', 20)
    inteiro(pagina, 'número de página'); inteiro(limite, 'limite de registros')
    limite = min(limite, 50)
    inicio = (pagina-1)*limite
    if tipo == 'doacao_pix':
        registros = [{k: v for k, v in item.items() if k in CAMPOS_PIX or (k == 'codigo_pagamento' and incluir_codigo and item.get('situacao') == 'pendente')} for item in registros]
    retorno.update(quantidade=len(registros), resumo_todos_filtrados=resumo, pagina=pagina, tem_mais=inicio+limite < len(registros), pagamentos=registros[inicio:inicio+limite])
    return retorno


def conta_recebedora(sistema):
    # Confere qual conta da Arkhé receberá a doação.
    conta = sistema.chamar(BASE + '/conta').get('conta')
    if not isinstance(conta, dict) or not conta.get('nome') or not conta.get('id_conta'):
        raise ErroAcao('Confira a conta de recebimento da Arkhé no sistema antes de gerar o código.', 422)
    return {k: conta.get(k) for k in ('id_conta', 'nome', 'banco')}


def preparar_pix(sistema, argumentos):
    # Antes de criar o Pix, a Lupe organiza os dados da doação e confere quem
    # vai receber. Ela apresenta um resumo para a pessoa confirmar.
    permitidos = {'doador', 'valor', 'valor_livre', 'id_projeto', 'descricao'}
    if not isinstance(argumentos, dict) or set(argumentos) - permitidos:
        raise ErroAcao('Informe apenas os dados da doação. O recebedor vem da conta configurada no sistema.')
    dados = {**argumentos, 'id': str(uuid4())}
    if dados.get('id_projeto') in (0, '0', ''): dados['id_projeto'] = None
    if not dados.get('doador'): raise ErroAcao('Qual é o nome do doador? Se for anônima, informe isso.')
    if not dados.get('valor') and dados.get('valor_livre') is not True:
        raise ErroAcao('Qual será o valor da doação? O doador também pode escolher o valor ao pagar.')
    try: identificador, doador, valor, projeto, descricao, livre = validar_dados(dados)
    except ValueError as erro: raise ErroAcao(str(erro)) from None
    dados = {'id': identificador, 'doador': doador, 'valor': None if livre else str(valor), 'valor_livre': livre, 'id_projeto': projeto, 'descricao': descricao}
    destino = sistema.exibir('id_projeto', projeto, 'doacao')
    conta = conta_recebedora(sistema)
    campos = [{'campo': rotulo, 'antes': '', 'depois': str(conteudo)} for rotulo, conteudo in [('Recebedor', conta['nome']), ('Instituição', conta.get('banco') or 'Arkhé'), ('Doador', doador), ('Valor', 'Escolhido pelo doador' if livre else 'R$ ' + str(valor)), ('Destino', destino)]]
    if descricao: campos.append({'campo': 'Descrição', 'antes': '', 'depois': descricao})
    return {'operacao': 'gerar_pix', 'recurso': 'pix_doacao', 'id_registro': None, 'rota': BASE + '/cobrancas', 'metodo': 'POST', 'dados': dados, 'snapshot': None, 'recebedor': conta, 'titulo': 'Gerar código Pix para doação', 'descricao': 'Código para pagamento dentro da Arkhé. Gerar o código não confirma o pagamento nem cadastra uma doação recebida.', 'campos': campos, 'destrutiva': False}


def executar_pix(sistema, plano):
    # Só roda depois da confirmação. A Lupe chama a rota do Guadalupe, e o
    # Guadalupe conversa com a Arkhé e devolve o código Pix real.
    if assinatura(conta_recebedora(sistema)) != assinatura(plano['recebedor']):
        raise ErroAcao('A conta de recebimento mudou. Prepare uma nova confirmação antes de gerar o Pix.', 409)
    dados = sistema.chamar(BASE + '/cobrancas', 'POST', plano['dados'])
    cobranca = dados.get('cobranca')
    if not isinstance(cobranca, dict) or cobranca.get('id') != plano['dados']['id']:
        raise ErroAcao('Não consegui confirmar o código gerado. Confira as cobranças antes de solicitar outro.', 502)
    return texto_codigo(cobranca, gerado=True)


def texto_codigo(cobranca, gerado=False):
    # Valida e formata o código recebido; não pede ao Gemini para inventá-lo.
    codigo = cobranca.get('codigo_pagamento')
    if not isinstance(codigo, str) or not 1 <= len(codigo) <= 2048 or any(ord(c) < 32 or ord(c) == 127 for c in codigo):
        raise ErroAcao('A criação não retornou um código válido. Confira as cobranças antes de solicitar outro.', 502)
    if cobranca.get('situacao') != 'pendente':
        raise ErroAcao('Confira a situação dessa cobrança na Arkhé antes de solicitar outro código.', 502)
    # Nunca pede ao modelo que invente, reescreva ou complete o código do provedor.
    inicio = 'Gerei o código para essa doação.' if gerado else 'Este é o código dessa doação.'
    return inicio + '\n\nCódigo de pagamento Arkhé (uso dentro da Arkhé):\n' + codigo + '\n\nO pagamento ainda está pendente.'
