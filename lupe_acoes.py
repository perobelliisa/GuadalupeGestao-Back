"""Ferramentas da Lupe: consultas autorizadas e alterações somente após confirmação."""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from hashlib import sha256
import json
import re
import time
import unicodedata
from uuid import uuid4

from flask import jsonify, request
from historico_lupe import HistoricoLupe, validar_id, ErroHistorico


class ErroAcao(RuntimeError):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


# As únicas rotas e campos aos quais o agente tem acesso.
RECURSOS = {
    'receita': ('/receitas', 'receitas', 'id_livro_caixa'),
    'despesa': ('/despesas', 'despesas', 'id_livro_caixa'),
    'movimentacao': ('/livro-caixa', 'movimentacoes', 'id_livro_caixa'),
    'doacao': ('/doacoes', 'doacoes', 'id_doacao'),
    'emprestimo': ('/emprestimos', 'emprestimos', 'id_emprestimo'),
    'categoria': ('/categorias', 'categorias', 'id_categoria'),
    'projeto': ('/projetos', 'projetos', 'id_projeto'),
    'pendencia': ('/pendencias', 'pendencias', 'id'),
    'documento': ('/documentos', 'documentos', 'id_documento'),
    'usuario': ('/usuarios', 'usuarios', 'id_usuario'),
}
CAMPOS_MOV = {'descricao', 'valor', 'dia', 'id_categoria', 'categoria', 'conta', 'origem', 'forma_pagamento', 'fornecedor', 'status', 'recorrencia', 'dia_inicio', 'dia_fim', 'vencimento', 'observacao'}
CAMPOS = {
    'receita': CAMPOS_MOV, 'despesa': CAMPOS_MOV,
    'doacao': {'id_projeto', 'doador', 'dia', 'tipo', 'valor', 'quantidade', 'descricao'},
    'emprestimo': {'id_projeto', 'id_usuario', 'finalidade', 'origem', 'valor', 'dia', 'devolucao', 'validade', 'parcelas', 'parcelas_pagas'},
    'categoria': {'nome', 'descricao'},
    'usuario': {'nome', 'email', 'tipo', 'status', 'projetos'},
}
CRIAR = {'receita', 'despesa', 'doacao', 'emprestimo'}
ALTERAR = CRIAR | {'categoria', 'usuario'}
EXCLUIR = CRIAR | {'documento', 'usuario'}
ROTULOS = {'descricao': 'Descrição', 'valor': 'Valor (R$)', 'dia': 'Data', 'origem': 'Origem', 'forma_pagamento': 'Forma de pagamento', 'id_categoria': 'Categoria', 'categoria': 'Categoria', 'conta': 'Projeto / missão', 'id_projeto': 'Projeto', 'status': 'Status', 'fornecedor': 'Fornecedor', 'recorrencia': 'Recorrência', 'dia_inicio': 'Início', 'dia_fim': 'Fim', 'vencimento': 'Vencimento', 'observacao': 'Observação', 'doador': 'Doador', 'tipo': 'Tipo', 'quantidade': 'Quantidade', 'finalidade': 'Finalidade', 'devolucao': 'Devolução', 'validade': 'Vencimento', 'parcelas': 'Parcelas', 'parcelas_pagas': 'Parcelas pagas', 'id_usuario': 'Responsável', 'nome': 'Nome', 'email': 'E-mail', 'projetos': 'Projetos'}
NOMES = {'receita': 'receita', 'despesa': 'despesa', 'doacao': 'doação', 'emprestimo': 'empréstimo', 'categoria': 'categoria', 'usuario': 'usuário', 'documento': 'documento'}
LEITURA = set().union(*CAMPOS.values()) | {'id', 'id_livro_caixa', 'id_doacao', 'id_emprestimo', 'id_categoria', 'id_projeto', 'id_usuario', 'id_documento', 'data', 'nome', 'categoria', 'projeto', 'projeto_nome', 'usuario', 'chave', 'dias', 'prioridade', 'parcela', 'projetos', 'anexo', 'caminho'}


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if not unicodedata.combining(c)).casefold()


def assinatura(dados):
    return sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def inteiro(valor, nome='identificador'):
    if type(valor) is not int or valor < 1:
        raise ErroAcao(f'Informe um {nome} válido.')
    return valor


# Faz as ferramentas usarem as rotas e permissões que o Guadalupe já possui.
class SistemaLupe:
    def __init__(self, app):
        self.app = app
        # Credenciais são encaminhadas às rotas, nunca enviadas ao modelo.
        self.headers = {campo: request.headers[campo] for campo in ('Authorization', 'Cookie', 'User-Agent') if campo in request.headers}

    def chamar(self, caminho, metodo='GET', dados=None, formulario=False):
        # Chama uma rota interna com a autenticação da pessoa que está logada.
        opcoes = {'headers': self.headers, 'method': metodo}
        if dados is not None:
            opcoes['data' if formulario else 'json'] = dados
        with self.app.test_request_context(caminho, **opcoes):
            resposta = self.app.full_dispatch_request()
            resultado = resposta.get_json(silent=True)
        if resposta.status_code >= 400 or not isinstance(resultado, dict) or resultado.get('sucesso') is False:
            if caminho.startswith('/integracoes/arkhe/') and isinstance(resultado, dict) and resultado.get('mensagem') == 'A integração Arkhé ainda não foi configurada no servidor.':
                raise ErroAcao('A integração Arkhé ainda não foi configurada no servidor. Peça ao administrador para configurar o recebimento de doações.', 422)
            mensagem = resultado.get('mensagem') if isinstance(resultado, dict) and resposta.status_code < 500 else None
            if not isinstance(mensagem, str) or len(mensagem) > 300:
                mensagem = 'Não foi possível realizar a operação no sistema. Confira os dados e tente novamente.'
            raise ErroAcao(mensagem, resposta.status_code if resposta.status_code >= 400 else 502)
        return resultado

    def registros(self, recurso):
        # Busca registros de um tipo, como despesas ou doações.
        if recurso not in RECURSOS:
            raise ErroAcao('Este recurso não está disponível para a Lupe.')
        rota, campo, _ = RECURSOS[recurso]
        dados = self.chamar(rota).get(campo)
        if not isinstance(dados, list):
            raise ErroAcao('O sistema não retornou os registros esperados.', 502)
        return [{k: v for k, v in item.items() if k in LEITURA} for item in dados if isinstance(item, dict)]

    def registro(self, recurso, identificador):
        # Localiza um registro específico pelo ID.
        inteiro(identificador)
        campo = RECURSOS[recurso][2]
        for item in self.registros(recurso):
            if item.get(campo) == identificador:
                return item
        raise ErroAcao('O registro solicitado não está mais disponível.', 404)

    def consultar(self, argumentos):
        # Filtra os registros e calcula totais para responder perguntas.
        if not isinstance(argumentos, dict):
            raise ErroAcao('Informe os filtros da consulta.')
        recurso = argumentos.get('recurso')
        registros = self.registros(recurso)
        identificador = argumentos.get('id')
        if identificador is not None:
            inteiro(identificador)
            registros = [item for item in registros if item.get(RECURSOS[recurso][2]) == identificador]
        busca = normalizar(argumentos.get('busca', '')).strip()
        if busca:
            registros = [item for item in registros if busca in normalizar(json.dumps(item, ensure_ascii=False))]
        for filtro, comparacao in [('inicio', lambda a, b: a >= b), ('fim', lambda a, b: a <= b)]:
            if argumentos.get(filtro):
                data = argumentos[filtro]
                if not isinstance(data, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', data):
                    raise ErroAcao('Informe uma data no formato ano-mês-dia.')
                registros = [item for item in registros if (item.get('dia') or item.get('data') or item.get('vencimento')) and comparacao(str(item.get('dia') or item.get('data') or item.get('vencimento'))[:10], data)]
        if argumentos.get('id_projeto') is not None:
            projeto = argumentos['id_projeto']
            registros = [item for item in registros if item.get('conta', item.get('id_projeto')) == projeto or projeto in item.get('projetos', [])]
        if argumentos.get('tipo') is not None:
            registros = [item for item in registros if item.get('tipo') == argumentos['tipo']]
        if argumentos.get('status') is not None:
            registros = [item for item in registros if item.get('status') == argumentos['status']]
        pagina = argumentos.get('pagina', 1)
        limite = argumentos.get('limite', 20)
        inteiro(pagina, 'número de página')
        inteiro(limite, 'limite de registros')
        limite = min(limite, 50)
        resumo = {'quantidade': len(registros)}
        if recurso in {'receita', 'despesa', 'movimentacao', 'doacao', 'emprestimo', 'pendencia'}:
            resumo['total_valor'] = str(sum((Decimal(str(item.get('valor') or 0)) for item in registros), Decimal(0)).quantize(Decimal('0.01')))
        if recurso == 'movimentacao':
            entradas = sum((Decimal(str(item.get('valor') or 0)) for item in registros if item.get('tipo') == 0), Decimal(0))
            despesas = sum((Decimal(str(item.get('valor') or 0)) for item in registros if item.get('tipo') == 1), Decimal(0))
            resumo.update(receitas=str(entradas.quantize(Decimal('0.01'))), despesas=str(despesas.quantize(Decimal('0.01'))), saldo=str((entradas-despesas).quantize(Decimal('0.01'))))
        inicio = (pagina-1)*limite
        return {'recurso': recurso, 'resumo_todos_filtrados': resumo, 'pagina': pagina, 'tem_mais': inicio+limite < len(registros), 'registros': registros[inicio:inicio+limite]}

    def preparar(self, argumentos):
        # Confere os dados e monta uma proposta; ainda não grava nada.
        if not isinstance(argumentos, dict):
            raise ErroAcao('Informe os dados da ação.')
        operacao, recurso = argumentos.get('operacao'), argumentos.get('recurso')
        permitidos = {'criar': CRIAR, 'alterar': ALTERAR, 'excluir': EXCLUIR, 'registrar_pagamento': {'despesa', 'emprestimo'}}
        if recurso not in permitidos.get(operacao, set()):
            raise ErroAcao('Esta operação não está disponível para a Lupe. Use uma função disponível no sistema.')
        dados = argumentos.get('dados', {})
        if not isinstance(dados, dict) or set(dados) - CAMPOS.get(recurso, set()):
            raise ErroAcao('Os campos enviados não são permitidos nesta operação.')
        atual = None
        identificador = argumentos.get('id')
        if operacao != 'criar':
            atual = self.registro(recurso, inteiro(identificador))
        rota = RECURSOS[recurso][0]
        if operacao == 'criar' and recurso == 'receita':
            rota = '/entradas'
        if operacao != 'criar':
            rota += '/' + str(identificador)
        metodo = {'criar': 'POST', 'alterar': 'PUT', 'excluir': 'DELETE', 'registrar_pagamento': 'POST'}[operacao]
        corpo = {}
        if operacao in {'criar', 'alterar'}:
            corpo = {campo: atual[campo] for campo in CAMPOS[recurso] if atual and campo in atual}
            if recurso in {'receita', 'despesa'}:
                corpo.pop('categoria', None)  # O ID preserva a categoria atual numa edição parcial.
                if 'categoria' in dados and 'id_categoria' not in dados:
                    corpo.pop('id_categoria', None)
            corpo.update(dados)
            if recurso == 'doacao':
                # A missão não é um projeto: a FK deve ficar vazia, nunca 0.
                if corpo.get('id_projeto') in (None, '', 0, '0'):
                    corpo['id_projeto'] = None
                if corpo.get('dia'):
                    try:
                        dia = datetime.strptime(corpo['dia'], '%Y-%m-%d').date()
                    except (TypeError, ValueError):
                        raise ErroAcao('Qual foi a data do recebimento? Informe uma data válida.') from None
                    if dia >= datetime.now().date():
                        raise ErroAcao('O cadastro aceita doações recebidas antes de hoje. Pergunte a data do recebimento; não escolha uma data pelo usuário.')
            if recurso == 'usuario' and isinstance(corpo.get('projetos'), list):
                corpo['projetos'] = [item.get('id_projeto', item.get('id')) if isinstance(item, dict) else item for item in corpo['projetos']]
            if recurso in {'receita', 'despesa'}:
                for campo, valor in {'conta': 0, 'status': 0, 'recorrencia': 0, 'fornecedor': '', 'observacao': ''}.items():
                    corpo.setdefault(campo, valor)
                if corpo.get('categoria') and not corpo.get('id_categoria'):
                    compativeis = [item for item in self.registros('categoria') if item.get('tipo') == (1 if recurso == 'despesa' else 0) and normalizar(item.get('nome', '')).strip() == normalizar(corpo['categoria']).strip()]
                    if len(compativeis) > 1: raise ErroAcao('Há mais de uma categoria com esse nome. Informe o identificador.')
                    if compativeis:
                        corpo['id_categoria'] = compativeis[0]['id_categoria']
                        corpo.pop('categoria')
            obrigatorios = {
                'receita': ['descricao', 'valor', 'dia', 'origem', 'forma_pagamento'],
                'despesa': ['descricao', 'valor', 'dia', 'origem', 'forma_pagamento'],
                'doacao': ['doador', 'dia', 'tipo'],
                'emprestimo': ['id_projeto', 'finalidade', 'origem', 'valor', 'dia', 'devolucao', 'validade', 'parcelas'],
                'categoria': ['nome'], 'usuario': ['nome', 'email', 'tipo', 'status'],
            }[recurso]
            faltam = [ROTULOS.get(campo, campo) for campo in obrigatorios if corpo.get(campo) is None or corpo.get(campo) == '']
            if recurso in {'receita', 'despesa'} and not (corpo.get('id_categoria') or corpo.get('categoria')):
                faltam.append('Categoria')
            if recurso == 'doacao':
                if corpo.get('tipo') in (0, 4) and not corpo.get('valor'): faltam.append('Valor')
                if corpo.get('tipo') in (1, 2, 3, 4) and not corpo.get('quantidade'): faltam.append('Quantidade')
            if faltam:
                raise ErroAcao('Antes de preparar a ação, informe: ' + ', '.join(faltam) + '.')
            for campo, valor in corpo.items():
                if campo == 'projetos':
                    if not isinstance(valor, list) or any(type(item) is not int for item in valor):
                        raise ErroAcao('Informe uma lista válida de projetos.')
                elif valor is not None and type(valor) not in (str, int, float):
                    raise ErroAcao('Informe valores válidos para os campos.')
                if isinstance(valor, str) and len(valor) > (500 if campo == 'observacao' else 300):
                    raise ErroAcao('Um campo excede o tamanho permitido.')
            for campo in ('valor', 'quantidade'):
                if corpo.get(campo) is not None:
                    try:
                        numero = Decimal(str(corpo[campo]))
                        if not numero.is_finite() or not 0 < numero <= Decimal('9999999999999.99'):
                            raise ValueError()
                        if campo == 'valor' and numero != numero.quantize(Decimal('0.01')):
                            raise ValueError()
                    except (InvalidOperation, ValueError):
                        raise ErroAcao('Informe um valor positivo válido, com ponto decimal.') from None
            for campo in ('status', 'forma_pagamento', 'recorrencia', 'tipo', 'parcelas', 'parcelas_pagas'):
                if campo in corpo and (type(corpo[campo]) is not int or corpo[campo] < 0):
                    raise ErroAcao('Informe um código válido para ' + ROTULOS.get(campo, campo) + '.')
            for campo, limite in [('status', 1), ('forma_pagamento', 5), ('recorrencia', 4), ('tipo', 2 if recurso == 'usuario' else 4)]:
                if campo in corpo and corpo[campo] > limite:
                    raise ErroAcao('O código de ' + ROTULOS.get(campo, campo) + ' é inválido.')
            # Referências devem existir e serão novamente validadas pela rota de negócio.
            referencias = [('id_categoria', 'categoria'), ('conta', 'projeto'), ('id_projeto', 'projeto'), ('id_usuario', 'usuario')]
            for campo, destino in referencias:
                if corpo.get(campo):
                    referencia = self.registro(destino, inteiro(corpo[campo]))
                    if campo == 'id_categoria' and referencia.get('tipo') != (1 if recurso == 'despesa' else 0):
                        raise ErroAcao('A categoria não pertence ao tipo do lançamento.')
            if atual and not any(corpo.get(k) != atual.get(k) for k in dados):
                raise ErroAcao('Os dados informados já estão cadastrados. Nenhuma alteração é necessária.')
        if operacao == 'registrar_pagamento':
            pendencias = [item for item in self.registros('pendencia') if item.get('id') == identificador and item.get('tipo') == recurso]
            vencimento = argumentos.get('vencimento')
            if recurso == 'despesa' and not atual.get('recorrencia'):
                if atual.get('status') == 1:
                    raise ErroAcao('Esta despesa já está registrada como paga.')
                corpo = {campo: atual[campo] for campo in CAMPOS_MOV if campo in atual and campo != 'categoria'}
                corpo['status'] = 1
                metodo, rota = 'PUT', '/despesas/' + str(identificador)
            else:
                ocorrencia = next((item for item in pendencias if item.get('vencimento') == vencimento), None)
                if not ocorrencia:
                    raise ErroAcao('Consulte a pendência e informe o vencimento exato antes de registrar o pagamento.')
                corpo, rota = {'vencimento': vencimento}, f'/pendencias/{recurso}/{identificador}/pagar'
                atual = {'registro': atual, 'ocorrencia': ocorrencia}
        nome = NOMES[recurso]
        verbo = {'criar': 'Cadastrar', 'alterar': 'Alterar', 'excluir': 'Excluir', 'registrar_pagamento': 'Registrar pagamento de'}[operacao]
        titulo = f'{verbo} {nome}' + (f' #{identificador}' if atual else '')
        alvo = atual.get('registro', atual) if atual else {}
        descricao = str(alvo.get('descricao') or alvo.get('finalidade') or alvo.get('nome') or alvo.get('doador') or corpo.get('descricao') or corpo.get('finalidade') or corpo.get('doador') or '')
        if recurso == 'doacao':
            descricao += ' A entrada vinculada no livro-caixa também será ' + ('removida.' if operacao == 'excluir' else 'sincronizada.')
        if operacao == 'registrar_pagamento':
            descricao += ' Registra no sistema um pagamento já realizado; não transfere dinheiro.'
        exibidos = corpo if operacao != 'excluir' else {k: v for k, v in alvo.items() if k in CAMPOS.get(recurso, {'nome'})}
        campos = []
        for campo, valor in exibidos.items():
            if operacao == 'alterar' and campo not in dados:
                continue
            campos.append({'campo': ROTULOS.get(campo, campo), 'antes': self.exibir(campo, alvo.get(campo), recurso) if operacao == 'alterar' else '', 'depois': self.exibir(campo, valor, recurso)})
        return {'operacao': operacao, 'recurso': recurso, 'id_registro': identificador, 'rota': rota, 'metodo': metodo, 'dados': corpo, 'snapshot': assinatura(atual) if atual else None, 'vencimento': argumentos.get('vencimento'), 'titulo': titulo, 'descricao': descricao, 'campos': campos, 'destrutiva': operacao == 'excluir'}

    def exibir(self, campo, valor, recurso):
        # Troca IDs por nomes que a pessoa consiga entender.
        if campo == 'id_projeto' and recurso == 'doacao' and valor in (None, '', 0): return 'Missão Guadalupe'
        if valor is None or valor == '': return '—'
        if campo == 'forma_pagamento': return {0: 'Pix', 1: 'Crédito', 2: 'Débito', 3: 'Boleto', 4: 'Parcelamento', 5: 'Dinheiro'}.get(valor, str(valor))
        if campo == 'status' and recurso in {'receita', 'despesa'}: return 'Pago' if valor == 1 else 'Não pago'
        if campo == 'status' and recurso == 'usuario': return 'Ativo' if valor == 0 else 'Inativo'
        if campo == 'tipo' and recurso == 'usuario': return {0: 'Administrador', 1: 'Gestor', 2: 'Responsável'}.get(valor, str(valor))
        if campo == 'tipo' and recurso == 'doacao': return {0: 'Dinheiro', 1: 'Alimento', 2: 'Roupa', 3: 'Tecido', 4: 'Outro'}.get(valor, str(valor))
        if campo == 'recorrencia': return {0: 'Não recorrente', 1: 'Quinzenal', 2: 'Mensal', 3: 'Diária', 4: 'Semanal'}.get(valor, str(valor))
        destino = {'id_categoria': 'categoria', 'conta': 'projeto', 'id_projeto': 'projeto', 'id_usuario': 'usuario'}.get(campo)
        if destino and valor:
            registro = self.registro(destino, valor)
            return str(registro.get('nome', '')) + f' (#{valor})'
        if campo == 'conta' and valor == 0: return 'Missão Guadalupe'
        if isinstance(valor, list): return ', '.join(map(str, valor)) or '—'
        return str(valor)

    def conferir(self, plano):
        # Verifica se o registro não mudou desde que a proposta foi mostrada.
        if not plano['snapshot']: return
        atual = self.registro(plano['recurso'], plano['id_registro'])
        if plano['operacao'] == 'registrar_pagamento' and plano['rota'].startswith('/pendencias/'):
            ocorrencia = next((item for item in self.registros('pendencia') if item.get('id') == plano['id_registro'] and item.get('tipo') == plano['recurso'] and item.get('vencimento') == plano['vencimento']), None)
            atual = {'registro': atual, 'ocorrencia': ocorrencia}
        if assinatura(atual) != plano['snapshot']:
            raise ErroAcao('Este registro mudou depois da proposta. Peça à Lupe para preparar a ação novamente.', 409)

    def executar(self, plano):
        # Chama a rota que grava a alteração depois da confirmação.
        if plano['recurso'] == 'pix_doacao' and plano['operacao'] == 'gerar_pix':
            from lupe_pagamentos import executar_pix
            return executar_pix(self, plano)
        self.conferir(plano)
        resultado = self.chamar(plano['rota'], plano['metodo'], plano['dados'] if plano['metodo'] != 'DELETE' else None, formulario=plano['recurso'] == 'usuario')
        verbo = {'criar': 'Cadastrei', 'alterar': 'Atualizei', 'excluir': 'Excluí', 'registrar_pagamento': 'Registrei o pagamento de'}[plano['operacao']]
        artigo = 'o' if plano['recurso'] in {'emprestimo', 'usuario', 'documento'} else 'a'
        return f"{verbo} {artigo} {NOMES[plano['recurso']]} com sucesso."


# Guarda propostas e confirmações para evitar ações sem aceite ou duplicadas.
class AcoesLupe:
    def __init__(self, banco=None, relogio=time.time):
        self.banco = banco or HistoricoLupe()
        self.relogio = relogio

    @contextmanager
    def conexao(self):
        # Abre o SQLite do histórico e garante a tabela de ações.
        with self.banco.conexao() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS lupe_acoes (
                id TEXT PRIMARY KEY, usuario TEXT NOT NULL, conversa TEXT NOT NULL,
                estado TEXT NOT NULL, expira REAL NOT NULL, plano TEXT NOT NULL, resultado TEXT)''')
            con.commit()
            yield con

    def publico(self, linha):
        plano = json.loads(linha[5])
        estado = linha[3]
        if estado == 'preparada' and linha[4] < self.relogio(): estado = 'expirada'
        return {'id': linha[0], 'conversa_id': linha[2], 'estado': estado, 'expira_em': datetime.fromtimestamp(linha[4], timezone.utc).isoformat(), 'titulo': plano['titulo'], 'descricao': plano['descricao'], 'campos': plano['campos'], 'destrutiva': plano['destrutiva'], 'resultado': linha[6]}

    def criar(self, usuario, conversa, plano):
        # Salva uma proposta pendente com prazo para confirmação.
        validar_id(conversa)
        identificador = str(uuid4())
        with self.conexao() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute("UPDATE lupe_acoes SET estado='substituida' WHERE usuario=? AND conversa=? AND estado='preparada'", (str(usuario), conversa))
            con.execute('INSERT INTO lupe_acoes VALUES (?, ?, ?, ?, ?, ?, NULL)', (identificador, str(usuario), conversa, 'preparada', self.relogio()+900, json.dumps(plano, ensure_ascii=False)))
        return self.obter(usuario, identificador)[0]

    def obter(self, usuario, identificador):
        with self.conexao() as con:
            linha = con.execute('SELECT * FROM lupe_acoes WHERE usuario=? AND id=?', (str(usuario), identificador)).fetchone()
        if not linha: raise ErroAcao('Esta ação não está disponível para sua conta.', 404)
        return self.publico(linha), json.loads(linha[5])

    def listar(self, usuario, conversa):
        validar_id(conversa)
        with self.conexao() as con:
            linhas = con.execute('SELECT * FROM lupe_acoes WHERE usuario=? AND conversa=? ORDER BY rowid DESC LIMIT 10', (str(usuario), conversa)).fetchall()
        return [self.publico(linha) for linha in reversed(linhas)]

    def decidir(self, usuario, identificador, confirmar, sistema):
        # Marca a ação como confirmada ou cancelada e trata sua execução.
        with self.conexao() as con:
            con.execute('BEGIN IMMEDIATE')
            linha = con.execute('SELECT * FROM lupe_acoes WHERE usuario=? AND id=?', (str(usuario), identificador)).fetchone()
            if not linha: raise ErroAcao('Esta ação não está disponível para sua conta.', 404)
            acao = self.publico(linha)
            if acao['estado'] in {'concluida', 'cancelada'}:
                return {'acao': acao, 'resposta': acao['resultado'], 'ja_processada': True}
            if acao['estado'] != 'preparada':
                raise ErroAcao('Esta ação expirou, foi substituída ou já está em processamento. Confira o histórico antes de tentar outra operação.', 409)
            if not confirmar:
                resposta = 'Tudo bem, deixei essa ação de lado.'
                con.execute("UPDATE lupe_acoes SET estado='cancelada',resultado=? WHERE id=?", (resposta, identificador))
                self.banco.responder_acao(con, usuario, linha[2], json.loads(linha[5]), resposta)
            else:
                # Persiste a execução antes da chamada de negócio. Repetições nunca executam duas vezes.
                con.execute("UPDATE lupe_acoes SET estado='executando' WHERE id=?", (identificador,))
            plano = json.loads(linha[5])
        if not confirmar:
            return {'acao': self.obter(usuario, identificador)[0], 'resposta': resposta, 'ja_processada': False}
        try:
            resposta = sistema.executar(plano)
            estado = 'concluida'
        except ErroAcao as erro:
            resposta = str(erro)
            estado = 'alterada' if erro.status == 409 else ('incerta' if erro.status >= 500 else 'falhou')
        except Exception:
            resposta = 'Não foi possível confirmar o resultado da operação. Confira o cadastro no sistema antes de propor outra ação.'
            estado = 'incerta'
        with self.conexao() as con:
            con.execute('UPDATE lupe_acoes SET estado=?,resultado=? WHERE id=?', (estado, resposta, identificador))
            if estado == 'concluida':
                self.banco.responder_acao(con, usuario, linha[2], plano, resposta)
                if plano.get('recurso') == 'pix_doacao' and plano.get('operacao') == 'gerar_pix':
                    from lupe_recebimentos import acompanhar_cobranca
                    acompanhar_cobranca(con, usuario, plano['dados']['id'], linha[2])
        return {'acao': self.obter(usuario, identificador)[0], 'resposta': resposta, 'ja_processada': False}


def registrar_acoes(app, autorizado, identificar_usuario, acoes, sistema_factory=None):
    # Registra as rotas para listar, confirmar e cancelar propostas da Lupe.
    sistema_factory = sistema_factory or (lambda: SistemaLupe(app))
    def proteger(funcao):
        @wraps(funcao)
        def executar(*args, **kwargs):
            usuario = identificar_usuario()
            if not usuario or not autorizado() or request.headers.get('X-Lupe-Usuario', str(usuario)) != str(usuario):
                return jsonify(sucesso=False, mensagem='Acesso não autorizado.'), 403
            try:
                return funcao(usuario, *args, **kwargs)
            except (ErroAcao, ErroHistorico) as erro:
                return jsonify(sucesso=False, mensagem=str(erro)), erro.status
            except Exception:
                app.logger.error('Falha no fluxo de confirmação da Lupe')
                return jsonify(sucesso=False, mensagem='Não foi possível confirmar a ação. Confira o histórico antes de tentar novamente.'), 503
        return executar

    @app.route('/lupe/acoes', methods=['GET'])
    @proteger
    def listar_acoes_lupe(usuario):
        return jsonify(sucesso=True, acoes=acoes.listar(usuario, request.args.get('conversa_id', '')))

    @app.route('/lupe/acoes/<identificador>/<decisao>', methods=['POST'])
    @proteger
    def decidir_acao_lupe(usuario, identificador, decisao):
        if decisao not in ('confirmar', 'cancelar'):
            raise ErroAcao('Decisão inválida.')
        dados = request.get_json(silent=True)
        if decisao == 'confirmar' and (not isinstance(dados, dict) or dados != {'confirmar': True}):
            raise ErroAcao('Confirme explicitamente a ação para continuar.')
        resultado = acoes.decidir(usuario, identificador, decisao == 'confirmar', sistema_factory())
        try:
            resultado['conversa'] = acoes.banco.carregar(usuario, resultado['acao']['conversa_id'])
        except ErroHistorico as erro:
            if erro.status != 404: raise
        return jsonify(sucesso=True, **resultado)
