"""Ponte entre os webhooks do WAHA e o agente Lupe existente."""
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import hashlib
import hmac
from io import BytesIO
import json
import os
import re
import sqlite3
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import jsonify, request

from historico_lupe import ErroHistorico, HistoricoLupe
from lupe_acoes import ErroAcao, SistemaLupe


NUMERO_PADRAO = '18981146999'
SESSAO_PADRAO = 'default'
MAX_TEXTO = 2000
CONFIRMACAO = re.compile(r'^(CONFIRMAR|CANCELAR)\s+([0-9a-f-]{36})$', re.IGNORECASE)


def digitos(valor):
    return re.sub(r'\D', '', str(valor or '').split('@', 1)[0])


def numero_com_pais(valor):
    numero = digitos(valor)
    if len(numero) == 11:
        return '55' + numero
    return numero


def texto_recebido(payload):
    texto = payload.get('body') or payload.get('text') or ''
    data = payload.get('_data')
    if not texto and isinstance(data, dict):
        mensagem = data.get('message')
        if isinstance(mensagem, dict):
            texto = (mensagem.get('conversation')
                     or mensagem.get('extendedTextMessage', {}).get('text', '')
                     or mensagem.get('imageMessage', {}).get('caption', '')
                     or mensagem.get('documentMessage', {}).get('caption', ''))
    return str(texto).strip()


class WhatsAppLupe:
    def __init__(self, app, agente, banco=None):
        self.app = app
        self.agente = agente
        self.acoes = agente.acoes
        self.banco = banco or HistoricoLupe()
        self.numero = numero_com_pais(os.environ.get('WHATSAPP_ALLOWED_NUMBER', NUMERO_PADRAO))
        self.lid = (os.environ.get('WHATSAPP_ALLOWED_LID') or '').strip().lower()
        self.usuario = (os.environ.get('WHATSAPP_USER_ID') or '2').strip()
        self.url = (os.environ.get('WAHA_API_URL') or 'https://apps-guadalupe-waha.ucxocw.easypanel.host').rstrip('/')
        self.chave = os.environ.get('WAHA_API_KEY', '').strip()
        self.sessao = os.environ.get('WAHA_SESSION', SESSAO_PADRAO).strip() or SESSAO_PADRAO
        self.segredo_webhook = os.environ.get('WHATSAPP_WEBHOOK_SECRET', '').strip()

    @contextmanager
    def conexao(self):
        self.banco.caminho.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.banco.caminho, timeout=10)
        try:
            con.execute('''CREATE TABLE IF NOT EXISTS whatsapp_eventos (
                id TEXT PRIMARY KEY, estado TEXT NOT NULL, criado_em TEXT NOT NULL)''')
            con.commit()
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def reivindicar_evento(self, identificador):
        if not identificador:
            return True
        with self.conexao() as con:
            cursor = con.execute('INSERT OR IGNORE INTO whatsapp_eventos VALUES (?, ?, ?)',
                                 (identificador, 'processando', datetime.now(timezone.utc).isoformat()))
            return cursor.rowcount == 1

    def reivindicar_resumo(self, identificador):
        with self.conexao() as con:
            con.execute('INSERT OR IGNORE INTO whatsapp_eventos VALUES (?, ?, ?)',
                        (identificador, 'falhou', datetime.now(timezone.utc).isoformat()))
            cursor = con.execute("UPDATE whatsapp_eventos SET estado='processando' WHERE id=? AND estado='falhou'", (identificador,))
            return cursor.rowcount == 1

    def enviar(self, chat_id, texto):
        if not self.chave:
            raise RuntimeError('WAHA_API_KEY não configurada')
        corpo = json.dumps({'session': self.sessao, 'chatId': chat_id, 'text': texto}, ensure_ascii=False).encode('utf-8')
        pedido = Request(f'{self.url}/api/sendText', data=corpo, headers={
            'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Api-Key': self.chave,
        }, method='POST')
        try:
            with urlopen(pedido, timeout=20) as resposta:
                resposta.read(1024)
        except (HTTPError, URLError, TimeoutError, OSError):
            self.app.logger.error('Falha ao enviar resposta da Lupe pelo WAHA')
            raise

    def salvar_comprovante(self, chat_id, payload):
        media = payload.get('media')
        if not isinstance(media, dict):
            data = payload.get('_data')
            media = data.get('media') if isinstance(data, dict) else None
        if not isinstance(media, dict) or not media.get('url'):
            return False
        legenda = texto_recebido(payload)
        correspondencia = re.fullmatch(r'COMPROVANTE\s+(\d+)', legenda, re.IGNORECASE)
        if not correspondencia:
            self.enviar(chat_id, 'Para anexar o arquivo, envie a imagem ou PDF com a legenda COMPROVANTE <ID da despesa>.')
            return True
        extensoes = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
        mimetype = str(media.get('mimetype') or '').split(';', 1)[0].lower()
        extensao = next((ext for ext, tipo in extensoes.items() if mimetype == tipo), '')
        if not extensao:
            nome_media = str(media.get('filename') or '')
            extensao = os.path.splitext(nome_media)[1].lower()
        if extensao not in extensoes:
            self.enviar(chat_id, 'Aceito comprovante em PDF, JPG ou PNG.')
            return True
        if not self.chave:
            raise RuntimeError('WAHA_API_KEY não configurada')
        caminho = urlsplit(str(media['url'])).path
        if not caminho.startswith('/api/files/'):
            self.enviar(chat_id, 'Não consegui acessar o arquivo recebido pelo WAHA.')
            return True
        pedido = Request(self.url + caminho, headers={'X-Api-Key': self.chave}, method='GET')
        try:
            with urlopen(pedido, timeout=30) as resposta:
                conteudo = resposta.read(12 * 1024 * 1024 + 1)
        except (HTTPError, URLError, TimeoutError, OSError):
            self.app.logger.error('Falha ao baixar comprovante recebido pelo WAHA')
            raise
        if len(conteudo) > 12 * 1024 * 1024:
            self.enviar(chat_id, 'O comprovante deve ter no máximo 12 MB.')
            return True

        from function import gerar_token
        token = gerar_token(int(self.usuario))
        id_lancamento = int(correspondencia.group(1))
        nome = f'comprovante{extensao}'
        with self.app.test_request_context(
            f'/livro-caixa/{id_lancamento}/anexo', method='POST',
            headers={'Authorization': f'Bearer {token}', 'X-Lupe-Usuario': self.usuario},
            data={'anexo': (BytesIO(conteudo), nome)},
        ):
            from main import con
            from function import tipo_lancamento
            cursor = con.cursor()
            try:
                tipo = tipo_lancamento(id_lancamento, cursor)
            finally:
                cursor.close()
            if tipo != 1:
                self.enviar(chat_id, 'Não encontrei uma despesa com esse ID. Confira o número e tente novamente.')
                return True
            resposta = self.app.full_dispatch_request()
            dados = resposta.get_json(silent=True) or {}
        if resposta.status_code >= 400:
            self.enviar(chat_id, dados.get('mensagem', 'Não consegui anexar o comprovante. Confira se essa despesa já tem arquivo.'))
        else:
            self.enviar(chat_id, f"Comprovante anexado à despesa #{id_lancamento}.")
        return True

    def carregar_mensagens(self, conversa_id):
        try:
            return self.banco.carregar(self.usuario, conversa_id)
        except ErroHistorico as erro:
            if erro.status != 404:
                raise
        return None

    def salvar_mensagens(self, conversa_id, mensagens, conversa=None):
        agora = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        dados = {
            'id': conversa_id,
            'criadaEm': conversa['criadaEm'] if conversa else agora,
            'atualizadaEm': agora,
            'revisao': conversa['revisao'] if conversa else 0,
            'mensagens': mensagens,
        }
        self.banco.salvar(self.usuario, conversa_id, dados)

    def enviar_para_agente(self, conversa_id, mensagem):
        conversa = self.carregar_mensagens(conversa_id)
        historico = conversa['mensagens'][-20:] if conversa else []
        mensagens = historico + [{'papel': 'usuario', 'texto': mensagem[:MAX_TEXTO]}]
        if len(mensagens) % 2 != 1:
            mensagens = [{'papel': 'usuario', 'texto': mensagem[:MAX_TEXTO]}]

        from function import gerar_token
        token = gerar_token(int(self.usuario))
        with self.app.test_request_context(headers={'Authorization': f'Bearer {token}', 'X-Lupe-Usuario': self.usuario}):
            resultado = self.agente.conversar(mensagens, self.usuario, conversa_id)

        resposta = resultado['resposta']
        pendentes = [acao for acao in resultado.get('acoes', []) if acao.get('estado') == 'preparada']
        if pendentes and resposta.startswith('Posso '):
            acao = pendentes[-1]
            previa = [acao.get('titulo', 'Ação proposta')]
            if acao.get('descricao'):
                previa.append(acao['descricao'])
            previa.extend(f"{campo.get('campo')}: {campo.get('depois') or campo.get('antes')}"
                          for campo in acao.get('campos', []) if campo.get('depois') or campo.get('antes'))
            resposta += '\n\n' + '\n'.join(previa)
            resposta += f"\n\nPara executar, responda: CONFIRMAR {acao['id']}\nPara desistir: CANCELAR {acao['id']}"
        mensagens.append({'papel': 'lupe', 'texto': resposta[:8000]})
        self.salvar_mensagens(conversa_id, mensagens, conversa)
        return resposta

    def decidir_acao(self, conversa_id, decisao, identificador):
        acao, _ = self.acoes.obter(self.usuario, identificador)
        if acao['conversa_id'] != conversa_id:
            raise ErroAcao('Essa confirmação não pertence a esta conversa.', 403)
        from function import gerar_token
        token = gerar_token(int(self.usuario))
        with self.app.test_request_context(headers={'Authorization': f'Bearer {token}', 'X-Lupe-Usuario': self.usuario}):
            resultado = self.acoes.decidir(self.usuario, identificador, decisao == 'CONFIRMAR', SistemaLupe(self.app))
        conversa = self.carregar_mensagens(conversa_id)
        mensagens = conversa['mensagens'] if conversa else []
        mensagens.extend([
            {'papel': 'usuario', 'texto': f'{decisao} {identificador}'},
            {'papel': 'lupe', 'texto': resultado['resposta']},
        ])
        self.salvar_mensagens(conversa_id, mensagens, conversa)
        return resultado['resposta']

    def resumo_diario(self):
        hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
        chave = 'resumo:' + hoje.isoformat()
        if not self.reivindicar_resumo(chave):
            return {'enviado': False, 'motivo': 'ja_enviado'}
        from function import gerar_token
        token = gerar_token(int(self.usuario))
        ontem = hoje - timedelta(days=1)
        with self.app.test_request_context(headers={'Authorization': f'Bearer {token}', 'X-Lupe-Usuario': self.usuario}):
            sistema = SistemaLupe(self.app)
            movimento = sistema.consultar({'recurso': 'movimentacao', 'inicio': ontem.isoformat(), 'fim': ontem.isoformat(), 'pagina': 1, 'limite': 50})
            pendentes = []
            pagina = 1
            while pagina <= 20:
                resultado = sistema.consultar({'recurso': 'pendencia', 'pagina': pagina, 'limite': 50})
                pendentes.extend(resultado['registros'])
                if not resultado['tem_mais']:
                    break
                pagina += 1
        atraso_ou_hoje = []
        for item in pendentes:
            try:
                vencimento = datetime.fromisoformat(str(item.get('vencimento'))[:10]).date()
            except ValueError:
                continue
            if vencimento <= hoje:
                atraso_ou_hoje.append((vencimento, item))
        atraso_ou_hoje.sort(key=lambda par: (par[0], str(par[1].get('descricao', ''))))
        resumo = movimento['resumo_todos_filtrados']
        receitas = Decimal(str(resumo.get('receitas', '0')))
        despesas = Decimal(str(resumo.get('despesas', '0')))
        linhas = [
            f"Resumo financeiro de {ontem.strftime('%d/%m/%Y')}",
            f"Receitas: R$ {receitas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"Despesas: R$ {despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            f"Saldo do dia: R$ {receitas-despesas:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            '',
            f"Contas vencidas ou vencendo hoje: {len(atraso_ou_hoje)}",
        ]
        for vencimento, item in atraso_ou_hoje[:12]:
            estado = 'VENCIDA' if vencimento < hoje else 'VENCE HOJE'
            valor = Decimal(str(item.get('valor') or 0))
            valor_pt = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            linhas.append(f"• {estado} {vencimento.strftime('%d/%m')}: {item.get('descricao') or item.get('fornecedor') or 'Conta'} — {valor_pt}")
        if len(atraso_ou_hoje) > 12:
            linhas.append(f"… e mais {len(atraso_ou_hoje)-12} conta(s). Consulte a Lupe para ver a lista completa.")
        mensagem = '\n'.join(linhas)
        self.enviar(f'{self.numero}@c.us', mensagem)
        with self.conexao() as con:
            con.execute("UPDATE whatsapp_eventos SET estado='concluido' WHERE id=?", (chave,))
        return {'enviado': True, 'contas': len(atraso_ou_hoje)}

    def processar(self, evento):
        if not isinstance(evento, dict) or evento.get('event') not in {'message', 'message.any'}:
            return
        payload = evento.get('payload')
        if not isinstance(payload, dict) or payload.get('fromMe') is True:
            return
        dados_internos = payload.get('_data')
        if isinstance(dados_internos, dict) and isinstance(dados_internos.get('key'), dict) and dados_internos['key'].get('fromMe') is True:
            return
        remetente = payload.get('from') or payload.get('chatId') or ''
        if str(remetente).lower().endswith('@lid'):
            if not self.lid or str(remetente).lower() != self.lid:
                return
        elif numero_com_pais(remetente) != self.numero:
            return
        chat_id = str(remetente)
        id_evento = evento.get('id') or payload.get('id')
        if isinstance(id_evento, dict):
            id_evento = id_evento.get('_serialized')
        if not self.reivindicar_evento(str(id_evento or '')):
            return

        conversa_id = 'whatsapp-' + self.numero
        if isinstance(payload.get('media'), dict) or (isinstance(payload.get('_data'), dict) and isinstance(payload['_data'].get('media'), dict)):
            self.salvar_comprovante(chat_id, payload)
            return
        texto = texto_recebido(payload)
        if not texto:
            self.enviar(chat_id, 'Por enquanto, envie sua solicitação em texto. A Lupe pode consultar e preparar lançamentos por aqui.')
            return

        confirmacao = CONFIRMACAO.fullmatch(texto)
        try:
            if confirmacao:
                resposta = self.decidir_acao(conversa_id, confirmacao.group(1).upper(), confirmacao.group(2))
            else:
                resposta = self.enviar_para_agente(conversa_id, texto)
            self.enviar(chat_id, resposta)
        except (ErroAcao, ErroHistorico) as erro:
            self.enviar(chat_id, str(erro))
        except Exception:
            self.app.logger.exception('Falha ao processar mensagem autorizada do WhatsApp')
            self.enviar(chat_id, 'Não consegui concluir essa solicitação agora. Tente novamente em instantes.')


def registrar_whatsapp(app):
    agente = app.extensions.get('agente_lupe')
    if agente is None:
        return
    integracao = WhatsAppLupe(app, agente)
    app.extensions['whatsapp_lupe'] = integracao

    @app.route('/webhooks/waha', methods=['POST'])
    def webhook_waha():
        if not integracao.segredo_webhook:
            return jsonify(sucesso=False, mensagem='Webhook do WhatsApp não configurado.'), 503
        assinatura = request.headers.get('X-Webhook-Hmac', '')
        algoritmo = request.headers.get('X-Webhook-Hmac-Algorithm', '')
        esperado = hmac.new(integracao.segredo_webhook.encode(), request.get_data(cache=True), hashlib.sha512).hexdigest()
        if algoritmo.lower() != 'sha512' or not hmac.compare_digest(assinatura.lower(), esperado):
            return jsonify(sucesso=False), 401
        if request.content_length and request.content_length > 256 * 1024:
            return jsonify(sucesso=False), 413
        evento = request.get_json(silent=True)
        if not isinstance(evento, dict):
            return jsonify(sucesso=False), 400
        try:
            integracao.processar(evento)
            return jsonify(sucesso=True), 200
        except (HTTPError, URLError, TimeoutError, OSError):
            return jsonify(sucesso=False), 503
        except Exception:
            app.logger.exception('Falha no webhook do WAHA')
            return jsonify(sucesso=False), 500

    @app.route('/tarefas/whatsapp/resumo-diario', methods=['POST'])
    def resumo_diario_whatsapp():
        segredo = os.environ.get('WHATSAPP_TASK_SECRET', '').strip()
        if not segredo:
            return jsonify(sucesso=False, mensagem='Tarefa do WhatsApp não configurada.'), 503
        if not hmac.compare_digest(request.headers.get('X-Task-Secret', ''), segredo):
            return jsonify(sucesso=False), 401
        try:
            return jsonify(sucesso=True, **integracao.resumo_diario()), 200
        except Exception:
            with integracao.conexao() as con:
                con.execute("UPDATE whatsapp_eventos SET estado='falhou' WHERE id=?", ('resumo:' + datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat(),))
            app.logger.exception('Falha ao montar resumo financeiro pelo WhatsApp')
            return jsonify(sucesso=False), 503

