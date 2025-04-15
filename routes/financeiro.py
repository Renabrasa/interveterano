from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file,session
from models.models import db, Jogador, Categoria, Mensalidade, MovimentacaoFinanceira, ConfigFinanceiro
from datetime import datetime, date
from sqlalchemy import func
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
from routes.auth import login_required


financeiro_bp = Blueprint('financeiro', __name__)

# ✅ Função de verificação de login
def login_obrigatorio():
    if 'usuario' not in session:
        session['destino'] = request.endpoint
        return redirect(url_for('auth.login'))

# ----------------------------
# PAINEL MENSAL DE MENSALIDADES
# ----------------------------
@financeiro_bp.route('/financeiro')
@login_required
def painel_mensal():
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')

    jogadores = Jogador.query.join(Categoria).filter(
        Categoria.nome.notin_(['Convidado', 'Treinador', 'Goleiro']),
        Jogador.ativo == True
    ).order_by(Jogador.nome).all()

    mensalidades = {m.jogador_id: m for m in Mensalidade.query.filter_by(mes_referencia=mes).all()}
    config = ConfigFinanceiro.query.first()
    valor_padrao = config.mensalidade_padrao if config else 30.00

    for jogador in jogadores:
        if jogador.id not in mensalidades:
            nova = Mensalidade(jogador_id=jogador.id, mes_referencia=mes, valor=valor_padrao, pago=False)
            db.session.add(nova)
    db.session.commit()

    mensalidades = Mensalidade.query.filter_by(mes_referencia=mes).all()

    # Saídas do mês
    inicio_mes = datetime.strptime(mes, '%Y-%m')
    fim_mes = datetime(inicio_mes.year + (inicio_mes.month // 12), (inicio_mes.month % 12) + 1, 1)
    saidas = MovimentacaoFinanceira.query.filter(
        MovimentacaoFinanceira.tipo == 'saida',
        MovimentacaoFinanceira.data >= inicio_mes,
        MovimentacaoFinanceira.data < fim_mes
    ).all()

    total_receber = sum(m.valor for m in mensalidades)
    total_recebido = sum(m.valor for m in mensalidades if m.pago)
    total_saidas = sum(s.valor for s in saidas)
    saldo = total_recebido - total_saidas

    return render_template('financeiro/painel_mensal.html',
        mes=mes,
        mensalidades=mensalidades,
        jogadores=jogadores,
        saidas=saidas,
        total_receber=total_receber,
        total_recebido=total_recebido,
        total_saidas=total_saidas,
        saldo=saldo,
        valor_padrao=valor_padrao
    )

# ----------------------------
# AÇÕES SOBRE MENSALIDADES
# ----------------------------
@financeiro_bp.route('/financeiro/pagar/<int:mensalidade_id>')
@login_required
def registrar_pagamento_mensalidade(mensalidade_id):
    mensalidade = Mensalidade.query.get_or_404(mensalidade_id)
    mensalidade.pago = True
    mensalidade.data_pagamento = date.today()
    db.session.commit()
    flash(f'Pagamento registrado para {mensalidade.jogador.nome}', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=mensalidade.mes_referencia))

@financeiro_bp.route('/financeiro/mensalidade/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar_baixa_mensalidade(id):
    mensalidade = Mensalidade.query.get_or_404(id)
    mensalidade.pago = False
    mensalidade.data_pagamento = None
    db.session.commit()
    flash('Baixa cancelada com sucesso!', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=mensalidade.mes_referencia))

@financeiro_bp.route('/financeiro/mensalidade/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_mensalidade(id):
    mensalidade = Mensalidade.query.get_or_404(id)
    mes = mensalidade.mes_referencia
    db.session.delete(mensalidade)
    db.session.commit()
    flash('Mensalidade excluída!', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=mes))

# ----------------------------
# ATUALIZAÇÃO GLOBAL DO VALOR PADRÃO
# ----------------------------
@financeiro_bp.route('/financeiro/atualizar_valor', methods=['POST'])
@login_required
def atualizar_valor_mensalidade_padrao():
    novo_valor = float(request.form['novo_valor'])
    mes = request.form['mes']
    
    config = ConfigFinanceiro.query.first()
    if not config:
        config = ConfigFinanceiro(mensalidade_padrao=novo_valor)
        db.session.add(config)
    else:
        config.mensalidade_padrao = novo_valor

    db.session.commit()
    flash(f'Valor da mensalidade atualizado para R$ {novo_valor:.2f}', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=mes))


# ----------------------------
# RELATÓRIO DE MENSALIDADES (PDF)
# ----------------------------
@financeiro_bp.route('/financeiro/relatorio_mensalidades')
@login_required
def relatorio_mensalidades():
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')
    vencimento = datetime.strptime(mes + '-15', '%Y-%m-%d')
    hoje = datetime.today()

    mensalidades = Mensalidade.query.filter_by(mes_referencia=mes).all()
    baixadas = [m for m in mensalidades if m.pago]
    vencidas = [m for m in mensalidades if not m.pago and hoje > vencimento]
    a_vencer = [m for m in mensalidades if not m.pago and hoje <= vencimento]

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        logo_width = 300
        logo_height = 300

        # Calcula as coordenadas para centralizar
        x = (largura - logo_width) / 2
        y = (altura - logo_height) / 2
        pdf.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, f"RELATÓRIO DE MENSALIDADES - {mes}")

    y = altura - 100
    def escrever_titulo(titulo, lista):
        nonlocal y
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, titulo)
        y -= 20
        pdf.setFont("Helvetica", 10)
        for m in lista:
            pdf.drawString(60, y, f"{m.jogador.nome} - R$ {m.valor:.2f}")
            y -= 15
        y -= 10

    escrever_titulo("✅ Baixadas", baixadas)
    escrever_titulo("❌ Vencidas", vencidas)
    escrever_titulo("🟡 A Vencer", a_vencer)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"relatorio_mensalidades_{mes}.pdf", mimetype='application/pdf')

# ----------------------------
# PAINEL DE RELATÓRIOS FINANCEIROS AVANÇADOS
# ----------------------------
@financeiro_bp.route('/financeiro/relatorios/financeiros')
@login_required
def relatorios_financeiros():
    jogadores = Jogador.query.filter_by(ativo=True).order_by(Jogador.nome).all()
    ano_atual = datetime.today().year
    return render_template('financeiro/relatorios_financeiros.html', jogadores=jogadores, ano=ano_atual)

# ----------------------------
# FLUXO DE CAIXA COMPARATIVO (PDF)
# ----------------------------
@financeiro_bp.route('/financeiro/relatorios/fluxo_caixa')
@login_required
def relatorio_fluxo_caixa():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from io import BytesIO
    from reportlab.lib.colors import black, green, red
    from reportlab.lib.units import cm
    import os

    inicio = request.args.get('inicio')
    fim = request.args.get('fim')

    if not inicio or not fim:
        flash("Selecione o período corretamente.", "erro")
        return redirect(url_for('financeiro.relatorios_financeiros'))

    data_inicio = datetime.strptime(inicio, "%Y-%m")
    data_fim = datetime.strptime(fim, "%Y-%m")

    meses = []
    cursor = data_inicio
    while cursor <= data_fim:
        meses.append(cursor.strftime('%Y-%m'))
        if cursor.month == 12:
            cursor = datetime(cursor.year + 1, 1, 1)
        else:
            cursor = datetime(cursor.year, cursor.month + 1, 1)

    config = ConfigFinanceiro.query.first()
    saldo_anterior = config.saldo_inicial if config else 0.0

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4
    y = altura - 50

    # Logo no centro como marca d’água
    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        pdf.drawImage(logo_path, 150, 300, width=300, preserveAspectRatio=True, mask='auto')

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, y, f"FLUXO DE CAIXA - {inicio} a {fim}")
    y -= 30

    # Títulos das colunas
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, y, "MÊS")
    pdf.drawString(6 * cm, y, "ENTRADA")
    pdf.drawString(10 * cm, y, "SAÍDA")
    pdf.drawString(14 * cm, y, "SALDO")
    y -= 20

    total_entrada = total_saida = 0

    for mes in meses:
        ano, mes_num = map(int, mes.split('-'))
        inicio_mes = datetime(ano, mes_num, 1)
        fim_mes = datetime(ano + (mes_num // 12), (mes_num % 12) + 1, 1)

        entradas = Mensalidade.query.filter_by(mes_referencia=mes, pago=True).all()
        saidas = MovimentacaoFinanceira.query.filter(
            MovimentacaoFinanceira.tipo == 'saida',
            MovimentacaoFinanceira.data >= inicio_mes,
            MovimentacaoFinanceira.data < fim_mes
        ).all()

        soma_entrada = sum(m.valor for m in entradas)
        soma_saida = sum(s.valor for s in saidas)
        saldo = saldo_anterior + soma_entrada - soma_saida
        saldo_anterior = saldo

        total_entrada += soma_entrada
        total_saida += soma_saida

        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(black)
        pdf.drawString(2 * cm, y, mes)
        pdf.drawString(6 * cm, y, f"R$ {soma_entrada:.2f}")
        pdf.drawString(10 * cm, y, f"R$ {soma_saida:.2f}")
        pdf.setFillColor(green if saldo >= 0 else red)
        pdf.drawString(14 * cm, y, f"R$ {saldo:.2f}")
        y -= 15

    # Total final
    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(black)
    pdf.drawString(2 * cm, y, "TOTAL")
    pdf.drawString(6 * cm, y, f"R$ {total_entrada:.2f}")
    pdf.drawString(10 * cm, y, f"R$ {total_saida:.2f}")
    saldo_total = total_entrada - total_saida
    pdf.setFillColor(green if saldo_total >= 0 else red)
    pdf.drawString(14 * cm, y, f"R$ {saldo_total:.2f}")

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"fluxo_caixa_{inicio}_a_{fim}.pdf", mimetype='application/pdf')



# ==========================
# ENTRADAS
# ==========================
@financeiro_bp.route('/financeiro/entradas')
@login_required
def exibir_entradas():
        
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')

    jogadores = Jogador.query.join(Categoria).filter(
        Categoria.nome.notin_(['Convidado', 'Treinador', 'Goleiro']),
        Jogador.ativo == True
    ).order_by(Jogador.nome).all()

    mensalidades = Mensalidade.query.filter_by(mes_referencia=mes).all()

    config = ConfigFinanceiro.query.first()
    valor_padrao = config.mensalidade_padrao if config else 30.00

    return render_template('financeiro/entradas.html',
        mes=mes,
        jogadores=jogadores,
        mensalidades=mensalidades,
        valor_padrao=valor_padrao
    )

    
# ==========================
# SAÍDAS
# ==========================
@financeiro_bp.route('/financeiro/saidas', methods=['GET', 'POST'])
@login_required
def exibir_saidas():
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')
    if request.method == 'POST':
        nova_saida = MovimentacaoFinanceira(
            tipo='saida',
            descricao=request.form['descricao'],
            categoria=request.form['categoria'],
            valor=float(request.form['valor']),
            data=datetime.strptime(request.form['data'], '%Y-%m-%d')
        )
        db.session.add(nova_saida)
        db.session.commit()
        flash('Saída registrada com sucesso!', 'sucesso')
        return redirect(url_for('financeiro.exibir_saidas', mes=mes))

    ano, mes_num = map(int, mes.split('-'))
    inicio = datetime(ano, mes_num, 1)
    fim = datetime(ano + (mes_num // 12), (mes_num % 12) + 1, 1)

    saidas = MovimentacaoFinanceira.query.filter(
        MovimentacaoFinanceira.tipo == 'saida',
        MovimentacaoFinanceira.data >= inicio,
        MovimentacaoFinanceira.data < fim
    ).all()

    return render_template('financeiro/saidas.html', mes=mes, saidas=saidas)

@financeiro_bp.route('/financeiro/saidas/excluir/<int:id>')
@login_required
def excluir_saida(id):
    saida = MovimentacaoFinanceira.query.get_or_404(id)
    mes = saida.data.strftime('%Y-%m')
    db.session.delete(saida)
    db.session.commit()
    flash('Saída excluída com sucesso!', 'sucesso')
    return redirect(url_for('financeiro.exibir_saidas', mes=mes))

# ==========================
# SALDO
# ==========================
@financeiro_bp.route('/financeiro/saldo', methods=['GET', 'POST'])
@login_required
def exibir_saldo():
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')
    ano, mes_num = map(int, mes.split('-'))
    inicio = datetime(ano, mes_num, 1)
    fim = datetime(ano + (mes_num // 12), (mes_num % 12) + 1, 1)

    config = ConfigFinanceiro.query.first()
    if not config:
        config = ConfigFinanceiro(mensalidade_padrao=30.0, saldo_inicial=0.0)
        db.session.add(config)
        db.session.commit()

    if request.method == 'POST':
        novo_valor = float(request.form['saldo_inicial'])
        config.saldo_inicial = novo_valor
        db.session.commit()
        flash('Saldo inicial atualizado!', 'sucesso')

    entradas = sum(m.valor for m in Mensalidade.query.filter_by(mes_referencia=mes, pago=True).all())
    saidas = sum(s.valor for s in MovimentacaoFinanceira.query.filter(
        MovimentacaoFinanceira.tipo == 'saida',
        MovimentacaoFinanceira.data >= inicio,
        MovimentacaoFinanceira.data < fim
    ).all())

    saldo = config.saldo_inicial + entradas - saidas
    mes_primeiro = Mensalidade.query.order_by(Mensalidade.mes_referencia.asc()).first()
    mes_primeiro = mes_primeiro.mes_referencia if mes_primeiro else mes

    return render_template('financeiro/saldo.html', mes=mes, entradas=entradas,
                           saidas=saidas, saldo=saldo,
                           saldo_inicial=config.saldo_inicial,
                           mes_primeiro=mes_primeiro)

@financeiro_bp.route('/financeiro/relatorios')
@login_required
def relatorios():
      
    return render_template('financeiro/relatorios.html')


@financeiro_bp.route('/financeiro/relatorios/inadimplencia')
@login_required
def relatorio_inadimplencia():
    from flask import send_file
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')
    vencimento = datetime.strptime(mes + '-15', '%Y-%m-%d')
    hoje = datetime.today()

    mensalidades = Mensalidade.query.join(Jogador).join(Categoria).filter(
        Mensalidade.mes_referencia == mes,
        Mensalidade.pago == False,
        Jogador.ativo == True,
        hoje > vencimento
    ).with_entities(
        Jogador.nome.label('nome'),
        Categoria.nome.label('categoria'),
        Mensalidade.valor
    ).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        # Define o tamanho da imagem
        logo_width = 300
        logo_height = 300

        # Calcula as coordenadas para centralizar
        x = (largura - logo_width) / 2
        y = (altura - logo_height) / 2
        pdf.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')


    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, f"RELATÓRIO DE INADIMPLÊNCIA - {mes}")

    y = altura - 100
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Jogadores com mensalidade vencida:")
    y -= 25

    pdf.setFont("Helvetica", 10)
    for m in mensalidades:
        pdf.drawString(60, y, f"{m.nome} - Categoria: {m.categoria} - Valor: R$ {m.valor:.2f}")
        y -= 15
        if y < 100:
            pdf.showPage()
            y = altura - 50

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"inadimplencia_{mes}.pdf", mimetype='application/pdf')


@financeiro_bp.route('/financeiro/relatorios/individual')
@login_required
def relatorio_individual():
    from flask import request, send_file
    jogador_id = request.args.get('jogador_id')
    ano = request.args.get('ano') or datetime.today().year

    if not jogador_id:
        flash("Selecione um jogador.", "erro")
        return redirect(url_for('financeiro.relatorios_financeiros'))

    jogador = Jogador.query.get_or_404(jogador_id)
    mensalidades = Mensalidade.query.filter(
        Mensalidade.jogador_id == jogador_id,
        Mensalidade.mes_referencia.like(f"{ano}-%")
    ).order_by(Mensalidade.mes_referencia.asc()).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    # Marca d'água
    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        logo_width = 300
        logo_height = 300
        # Calcula as coordenadas para centralizar
        x = (largura - logo_width) / 2
        y = (altura - logo_height) / 2
        pdf.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, f"RELATÓRIO INDIVIDUAL - {jogador.nome.upper()} - {ano}")

    y = altura - 100
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Mensalidades:")
    y -= 25
    pdf.setFont("Helvetica", 10)

    for m in mensalidades:
        status = "Pago" if m.pago else "Pendente"
        pdf.drawString(60, y, f"{m.mes_referencia} - Valor: R$ {m.valor:.2f} - Status: {status}")
        y -= 15
        if y < 100:
            pdf.showPage()
            y = altura - 50

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"relatorio_individual_{jogador.nome}_{ano}.pdf", mimetype='application/pdf')


@financeiro_bp.route('/financeiro/relatorios/resumo_anual')
@login_required
def relatorio_resumo_anual():
    from flask import request, send_file
    ano = int(request.args.get('ano') or datetime.today().year)

    dados = []
    for mes in range(1, 13):
        mes_ref = f"{ano}-{mes:02d}"
        entradas = Mensalidade.query.filter_by(mes_referencia=mes_ref, pago=True).all()
        total_entrada = sum(m.valor for m in entradas)

        inicio_mes = datetime(ano, mes, 1)
        fim_mes = datetime(ano + (mes // 12), (mes % 12) + 1, 1)
        saidas = MovimentacaoFinanceira.query.filter(
            MovimentacaoFinanceira.tipo == 'saida',
            MovimentacaoFinanceira.data >= inicio_mes,
            MovimentacaoFinanceira.data < fim_mes
        ).all()
        total_saida = sum(s.valor for s in saidas)

        saldo = total_entrada - total_saida
        dados.append({'mes': f"{mes:02d}/{ano}", 'entrada': total_entrada, 'saida': total_saida, 'saldo': saldo})

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        logo_width = 300
        logo_height = 300
        # Calcula as coordenadas para centralizar
        x = (largura - logo_width) / 2
        y = (altura - logo_height) / 2
        pdf.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, f"RESUMO ANUAL DE MOVIMENTAÇÃO - {ano}")
    y = altura - 90

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "MÊS")
    pdf.drawString(150, y, "ENTRADA")
    pdf.drawString(250, y, "SAÍDA")
    pdf.drawString(350, y, "SALDO")
    y -= 20
    pdf.setFont("Helvetica", 10)

    for d in dados:
        pdf.drawString(50, y, d['mes'])
        pdf.drawString(150, y, f"R$ {d['entrada']:.2f}")
        pdf.drawString(250, y, f"R$ {d['saida']:.2f}")
        cor = 'green' if d['saldo'] >= 0 else 'red'
        pdf.setFillColorRGB(0, 0.5, 0) if cor == 'green' else pdf.setFillColorRGB(1, 0, 0)
        pdf.drawString(350, y, f"R$ {d['saldo']:.2f}")
        pdf.setFillColorRGB(0, 0, 0)
        y -= 15
        if y < 100:
            pdf.showPage()
            y = altura - 50

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"resumo_anual_{ano}.pdf", mimetype='application/pdf')


@financeiro_bp.route('/financeiro/relatorios/saidas_detalhadas')
@login_required
def relatorio_saidas_detalhadas():
    from flask import request, send_file
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')
    ano, mes_num = map(int, mes.split('-'))

    inicio = datetime(ano, mes_num, 1)
    fim = datetime(ano + (mes_num // 12), (mes_num % 12) + 1, 1)

    saidas = MovimentacaoFinanceira.query.filter(
        MovimentacaoFinanceira.tipo == 'saida',
        MovimentacaoFinanceira.data >= inicio,
        MovimentacaoFinanceira.data < fim
    ).order_by(MovimentacaoFinanceira.data.asc()).all()

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        logo_width = 300
        logo_height = 300

        # Calcula as coordenadas para centralizar
        x = (largura - logo_width) / 2
        y = (altura - logo_height) / 2
        pdf.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, f"SAÍDAS DETALHADAS - {mes}")

    y = altura - 90
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "DATA")
    pdf.drawString(120, y, "CATEGORIA")
    pdf.drawString(250, y, "DESCRIÇÃO")
    pdf.drawString(430, y, "VALOR")
    y -= 20
    pdf.setFont("Helvetica", 10)

    for s in saidas:
        pdf.drawString(50, y, s.data.strftime('%d/%m/%Y'))
        pdf.drawString(120, y, s.categoria)
        pdf.drawString(250, y, s.descricao)
        pdf.drawRightString(500, y, f"R$ {s.valor:.2f}")
        y -= 15
        if y < 100:
            pdf.showPage()
            y = altura - 50

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"saidas_detalhadas_{mes}.pdf", mimetype='application/pdf')


@financeiro_bp.route('/financeiro/relatorio_performance')
@login_required
def relatorio_performance():
    return "<h1>Relatório de performance ainda não implementado.</h1>"



@financeiro_bp.route('/financeiro/gerar_mensalidades', methods=['POST'])
@login_required
def gerar_mensalidades():
    mes = request.form['mes']
    valor_mensalidade = float(request.form['valor_mensalidade'])

    jogadores = Jogador.query.join(Categoria).filter(
        Categoria.nome.notin_(['Convidado', 'Treinador', 'Goleiro']),
        Jogador.ativo == True
    ).all()

    mensalidades_do_mes = {m.jogador_id: m for m in Mensalidade.query.filter_by(mes_referencia=mes).all()}

    novos = 0
    atualizados = 0

    for jogador in jogadores:
        m = mensalidades_do_mes.get(jogador.id)
        if not m:
            nova = Mensalidade(jogador_id=jogador.id, mes_referencia=mes, valor=valor_mensalidade, pago=False)
            db.session.add(nova)
            novos += 1
        elif not m.pago:
            m.valor = valor_mensalidade
            atualizados += 1

    db.session.commit()
    flash(f'{novos} novas mensalidades criadas e {atualizados} atualizadas com o valor R$ {valor_mensalidade:.2f}', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=mes))


@financeiro_bp.route('/financeiro/relatorios/fluxo_caixa_analitico')
@login_required
def relatorio_fluxo_caixa_analitico():
    from reportlab.lib.colors import red, blue, green, black
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    from io import BytesIO
    import os
    from datetime import datetime

    inicio = request.args.get('inicio')
    fim = request.args.get('fim')

    if not inicio or not fim:
        flash("Selecione o período corretamente.", "erro")
        return redirect(url_for('financeiro.relatorios_financeiros'))

    data_inicio = datetime.strptime(inicio, "%Y-%m")
    data_fim = datetime.strptime(fim, "%Y-%m")

    meses = []
    cursor = data_inicio
    while cursor <= data_fim:
        meses.append(cursor.strftime('%Y-%m'))
        if cursor.month == 12:
            cursor = datetime(cursor.year + 1, 1, 1)
        else:
            cursor = datetime(cursor.year, cursor.month + 1, 1)

    config = ConfigFinanceiro.query.first()
    saldo_anterior = config.saldo_inicial if config else 0.0

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4
    y = altura - 60

    # Logo centralizada como marca d'água
    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        img_width = 12 * cm
        img_height = 12 * cm
        x_logo = (largura - img_width) / 2
        y_logo = (altura - img_height) / 2
        pdf.drawImage(logo_path, x_logo, y_logo, width=img_width, height=img_height, mask='auto')

    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(black)
    pdf.drawCentredString(largura / 2, y, "FLUXO DE CAIXA ANALÍTICO")
    y -= 30

    for mes in meses:
        ano, mes_num = map(int, mes.split('-'))
        nome_mes = datetime(ano, mes_num, 1).strftime('%B/%Y').upper()
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(black)
        pdf.drawString(50, y, f"MÊS: {nome_mes}")
        y -= 20

        # ENTRADAS
        pdf.setFont("Helvetica-Bold", 11)
        pdf.setFillColor(black)
        pdf.drawString(60, y, "ENTRADAS")
        y -= 15

        entradas = Mensalidade.query.filter_by(mes_referencia=mes, pago=True).all()
        total_entrada = sum(m.valor for m in entradas)

        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(blue)
        entrada_desc = "Mensalidades"
        entrada_valor = f"R$ {total_entrada:.2f}"
        pdf.drawString(70, y, entrada_desc)

        x1 = 70 + pdf.stringWidth(entrada_desc, "Helvetica", 10) + 5
        x2 = largura - 50 - pdf.stringWidth(entrada_valor, "Helvetica", 10) - 10
        while x1 < x2:
            pdf.line(x1, y + 3, x1 + 2, y + 3)
            x1 += 4

        pdf.drawRightString(largura - 50, y, entrada_valor)
        y -= 20

        # SAÍDAS
        pdf.setFont("Helvetica-Bold", 11)
        pdf.setFillColor(black)
        pdf.drawString(60, y, "SAÍDAS")
        y -= 15

        inicio_mes = datetime(ano, mes_num, 1)
        fim_mes = datetime(ano + (mes_num // 12), (mes_num % 12) + 1, 1)
        saidas = MovimentacaoFinanceira.query.filter(
            MovimentacaoFinanceira.tipo == 'saida',
            MovimentacaoFinanceira.data >= inicio_mes,
            MovimentacaoFinanceira.data < fim_mes
        ).all()

        total_saida = 0
        pdf.setFont("Helvetica", 10)
        for s in saidas:
            pdf.setFillColor(red)
            descricao = s.descricao
            valor_str = f"R$ {s.valor:.2f}"
            pdf.drawString(70, y, descricao)

            x1 = 70 + pdf.stringWidth(descricao, "Helvetica", 10) + 5
            x2 = largura - 50 - pdf.stringWidth(valor_str, "Helvetica", 10) - 10
            while x1 < x2:
                pdf.line(x1, y + 3, x1 + 2, y + 3)
                x1 += 4

            pdf.drawRightString(largura - 50, y, valor_str)
            total_saida += s.valor
            y -= 15

        # SALDO
        saldo = saldo_anterior + total_entrada - total_saida
        saldo_label = "Saldo do mês:"
        saldo_str = f"R$ {saldo:.2f}"

        pdf.setFont("Helvetica-Bold", 11)
        pdf.setFillColor(green if saldo >= 0 else red)
        pdf.drawString(60, y, saldo_label)

        x1 = 60 + pdf.stringWidth(saldo_label, "Helvetica-Bold", 11) + 5
        x2 = largura - 50 - pdf.stringWidth(saldo_str, "Helvetica-Bold", 11) - 10
        while x1 < x2:
            pdf.line(x1, y + 3, x1 + 2, y + 3)
            x1 += 4

        pdf.drawRightString(largura - 50, y, saldo_str)
        y -= 30

        saldo_anterior = saldo

        if y < 100:
            pdf.showPage()
            y = altura - 60
            if os.path.exists(logo_path):
                pdf.drawImage(logo_path, x_logo, y_logo, width=img_width, height=img_height, mask='auto')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"fluxo_caixa_analitico_{inicio}_a_{fim}.pdf",
                     mimetype='application/pdf')




@financeiro_bp.route('/financeiro/relatorios/gerar_fluxo_caixa')
@login_required
def gerar_fluxo_caixa():
    if 'analitico' in request.args:
        return redirect(url_for('financeiro.relatorio_fluxo_caixa_analitico', inicio=request.args['inicio'], fim=request.args['fim']))
    else:
        return redirect(url_for('financeiro.relatorio_fluxo_caixa', inicio=request.args['inicio'], fim=request.args['fim']))
