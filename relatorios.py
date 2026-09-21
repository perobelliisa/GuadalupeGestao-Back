import datetime
from io import BytesIO

from flask import jsonify, request, send_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from main import app, con
from function import id_usuario_logado


TIPOS_VALIDOS = {'entrada', 'saida', 'doacao', 'emprestimo'}


def moeda(valor):
    numero = float(valor or 0)
    texto = f'{numero:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {texto}'


def data_br(valor):
    return valor.strftime('%d/%m/%Y') if valor else '-'


def ler_data(nome):
    texto = request.args.get(nome, '').strip()
    if not texto:
        return None
    return datetime.datetime.strptime(texto, '%Y-%m-%d').date()


def consultar_registros(tipos, inicio, fim, id_projeto):
    cur = con.cursor()
    registros = []
    try:
        if 'entrada' in tipos or 'saida' in tipos:
            desejados = []
            if 'entrada' in tipos:
                desejados.append(0)
            if 'saida' in tipos:
                desejados.append(1)
            marcadores = ','.join('?' for _ in desejados)
            sql = f'''SELECT L.TIPO, L.DIA, L.DESCRICAO, L.VALOR, L.CONTA, P.NOME
                      FROM LIVRO_CAIXA L
                      LEFT JOIN PROJETO P ON P.ID_PROJETO = L.CONTA
                      WHERE L.TIPO IN ({marcadores})'''
            parametros = list(desejados)
            if inicio:
                sql += ' AND L.DIA >= ?'
                parametros.append(inicio)
            if fim:
                sql += ' AND L.DIA <= ?'
                parametros.append(fim)
            if id_projeto is not None:
                sql += ' AND L.CONTA = ?'
                parametros.append(id_projeto)
            cur.execute(sql, parametros)
            for item in cur.fetchall():
                registros.append({'tipo': 'Entrada' if item[0] == 0 else 'Saída', 'chave': 'entrada' if item[0] == 0 else 'saida', 'data': item[1], 'descricao': str(item[2] or '').strip(), 'valor': float(item[3] or 0), 'projeto': str(item[5] or 'Sem projeto').strip()})

        consultas = [
            ('doacao', 'Doação', 'SELECT D.DIA, D.DESCRICAO, D.VALOR, D.ID_PROJETO, P.NOME FROM DOACAO D LEFT JOIN PROJETO P ON P.ID_PROJETO = D.ID_PROJETO WHERE 1=1', 'D.DIA', 'D.ID_PROJETO'),
            ('emprestimo', 'Empréstimo', 'SELECT E.DIA, E.FINALIDADE, E.VALOR, E.ID_PROJETO, P.NOME FROM EMPRESTIMO E LEFT JOIN PROJETO P ON P.ID_PROJETO = E.ID_PROJETO WHERE 1=1', 'E.DIA', 'E.ID_PROJETO')
        ]
        for chave, nome, sql_base, campo_data, campo_projeto in consultas:
            if chave not in tipos:
                continue
            sql = sql_base
            parametros = []
            if inicio:
                sql += f' AND {campo_data} >= ?'
                parametros.append(inicio)
            if fim:
                sql += f' AND {campo_data} <= ?'
                parametros.append(fim)
            if id_projeto is not None:
                sql += f' AND {campo_projeto} = ?'
                parametros.append(id_projeto)
            cur.execute(sql, parametros)
            for item in cur.fetchall():
                registros.append({'tipo': nome, 'chave': chave, 'data': item[0], 'descricao': str(item[1] or nome).strip(), 'valor': float(item[2] or 0), 'projeto': str(item[4] or 'Sem projeto').strip()})
        return sorted(registros, key=lambda item: item['data'] or datetime.date.min, reverse=True)
    finally:
        cur.close()


def rodape(canvas, documento):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#DCE5F4'))
    canvas.line(12 * mm, 10 * mm, 198 * mm, 10 * mm)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(colors.HexColor('#697588'))
    canvas.drawString(12 * mm, 6 * mm, 'Guadalupe Gestões — Relatório institucional')
    canvas.drawRightString(198 * mm, 6 * mm, f'Página {documento.page}')
    canvas.restoreState()


@app.route('/relatorios/pdf', methods=['GET'])
def gerar_relatorio_pdf():
    if not id_usuario_logado():
        return jsonify({'sucesso': False, 'mensagem': 'Acesso não autorizado'}), 401
    try:
        tipos = {item.strip() for item in request.args.get('tipos', '').split(',') if item.strip()}
        if not tipos or not tipos.issubset(TIPOS_VALIDOS):
            return jsonify({'sucesso': False, 'mensagem': 'Selecione ao menos um tipo válido.'}), 400
        inicio = ler_data('inicio')
        fim = ler_data('fim')
        if inicio and fim and inicio > fim:
            return jsonify({'sucesso': False, 'mensagem': 'A data inicial não pode ser posterior à data final.'}), 400
        projeto_texto = request.args.get('projeto', '').strip()
        id_projeto = int(projeto_texto) if projeto_texto else None
        registros = consultar_registros(tipos, inicio, fim, id_projeto)

        projeto_nome = 'Todos os projetos'
        if id_projeto is not None:
            cur = con.cursor()
            cur.execute('SELECT NOME FROM PROJETO WHERE ID_PROJETO = ?', (id_projeto,))
            projeto_encontrado = cur.fetchone()
            cur.close()
            projeto_nome = str(projeto_encontrado[0]).strip() if projeto_encontrado else 'Projeto não encontrado'

        totais = {chave: sum(item['valor'] for item in registros if item['chave'] == chave) for chave in TIPOS_VALIDOS}
        buffer = BytesIO()
        documento = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm, topMargin=11*mm, bottomMargin=14*mm, title='Relatório Guadalupe Gestões')
        estilos = getSampleStyleSheet()
        estilo_branco = ParagraphStyle('branco', parent=estilos['Normal'], textColor=colors.white, fontSize=9, leading=12)
        estilo_titulo = ParagraphStyle('titulo', parent=estilos['Heading1'], textColor=colors.HexColor('#14213D'), fontSize=18, leading=22, spaceAfter=3*mm)
        estilo_texto = ParagraphStyle('texto', parent=estilos['Normal'], textColor=colors.HexColor('#526078'), fontSize=8.5, leading=11)
        estilo_celula = ParagraphStyle('celula', parent=estilos['Normal'], textColor=colors.HexColor('#263650'), fontSize=7.5, leading=9, alignment=TA_LEFT)
        historia = []

        cabecalho = Table([[Paragraph('<b>GUADALUPE GESTÕES</b><br/><font size="8">Relatório institucional e financeiro</font>', estilo_branco), Paragraph(f'<b>{datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}</b>', estilo_branco)]], colWidths=[135*mm, 47*mm], rowHeights=24*mm)
        cabecalho.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#2868F0')),('BACKGROUND',(1,0),(1,0),colors.HexColor('#13AFA5')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ALIGN',(1,0),(1,0),'RIGHT'),('LEFTPADDING',(0,0),(0,0),6*mm),('RIGHTPADDING',(1,0),(1,0),5*mm)]))
        historia.extend([cabecalho, Spacer(1, 7*mm), Paragraph('Relatório de movimentações', estilo_titulo)])
        periodo = f'{data_br(inicio) if inicio else "Início"} até {data_br(fim) if fim else "Hoje"}' if inicio or fim else 'Todos os períodos'
        historia.extend([Paragraph(f'<b>Período:</b> {periodo} &nbsp;&nbsp; <b>Projeto:</b> {projeto_nome}', estilo_texto), Spacer(1, 5*mm)])

        cards = [['ENTRADAS', 'SAÍDAS', 'DOAÇÕES', 'EMPRÉSTIMOS', 'SALDO'], [moeda(totais['entrada']), moeda(totais['saida']), moeda(totais['doacao']), moeda(totais['emprestimo']), moeda(totais['entrada'] - totais['saida'])]]
        resumo = Table(cards, colWidths=[36.4*mm]*5, rowHeights=[7*mm, 10*mm])
        resumo.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTNAME',(0,1),(-1,1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),6.5),('FONTSIZE',(0,1),(-1,1),8),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor('#137748')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#E8F8EF')),('TEXTCOLOR',(1,0),(1,-1),colors.HexColor('#D9473B')),('BACKGROUND',(1,0),(1,-1),colors.HexColor('#FFF0EE')),('TEXTCOLOR',(2,0),(2,-1),colors.HexColor('#245ED8')),('BACKGROUND',(2,0),(2,-1),colors.HexColor('#E9F1FF')),('TEXTCOLOR',(3,0),(3,-1),colors.HexColor('#7653D6')),('BACKGROUND',(3,0),(3,-1),colors.HexColor('#F1EDFF')),('TEXTCOLOR',(4,0),(4,-1),colors.HexColor('#087E76')),('BACKGROUND',(4,0),(4,-1),colors.HexColor('#E5F8F5')),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#DCE5F4')),('INNERGRID',(0,0),(-1,-1),.5,colors.white)]))
        historia.extend([resumo, Spacer(1, 6*mm)])

        linhas = [['DATA', 'TIPO', 'DESCRIÇÃO', 'PROJETO', 'VALOR']]
        for item in registros:
            linhas.append([data_br(item['data']), item['tipo'], Paragraph(item['descricao'], estilo_celula), Paragraph(item['projeto'], estilo_celula), moeda(item['valor'])])
        if not registros:
            linhas.append(['-', '-', 'Nenhum registro encontrado com os filtros selecionados.', '-', '-'])
        tabela = Table(linhas, colWidths=[24*mm, 25*mm, 61*mm, 45*mm, 27*mm], repeatRows=1)
        estilo_tabela = [('BACKGROUND',(0,0),(-1,0),colors.HexColor('#245ED8')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),7),('ALIGN',(4,1),(4,-1),'RIGHT'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('FONTSIZE',(0,1),(-1,-1),7.5),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor('#263650')),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#DCE5F4')),('TOPPADDING',(0,0),(-1,-1),3*mm),('BOTTOMPADDING',(0,0),(-1,-1),3*mm)]
        for indice in range(2, len(linhas), 2):
            estilo_tabela.append(('BACKGROUND',(0,indice),(-1,indice),colors.HexColor('#F5F8FD')))
        tabela.setStyle(TableStyle(estilo_tabela))
        historia.extend([tabela, Spacer(1, 4*mm), Paragraph(f'{len(registros)} registro(s) encontrado(s)', estilo_texto)])
        documento.build(historia, onFirstPage=rodape, onLaterPages=rodape)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f'relatorio-guadalupe-{datetime.date.today().isoformat()}.pdf')
    except ValueError:
        return jsonify({'sucesso': False, 'mensagem': 'Os filtros informados são inválidos.'}), 400
    except Exception as erro:
        return jsonify({'sucesso': False, 'erro': f'Erro ao gerar relatório: {erro}'}), 500
