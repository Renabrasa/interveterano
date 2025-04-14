from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.models import db, Jogador, Categoria, Mensalidade, MovimentacaoFinanceira, ConfigFinanceiro
from datetime import datetime, date
from sqlalchemy import func,and_
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
from flask import send_file


financeiro_bp = Blueprint('financeiro', __name__)


@financeiro_bp.route('/financeiro/pagar/<int:mensalidade_id>')
def registrar_pagamento_mensalidade(mensalidade_id):
    mensalidade = Mensalidade.query.get_or_404(mensalidade_id)
    mensalidade.pago = True
    mensalidade.data_pagamento = date.today()
    db.session.commit()
    flash(f'Pagamento registrado para {mensalidade.jogador.nome}', 'sucesso')
    return redirect(url_for('financeiro.painel_mensal', mes=mensalidade.mes_referencia))


@financeiro_bp.route('/financeiro/mensalidade/<int:id>/editar', methods=['POST'])
def editar_mensalidade(id):
    mensalidade = Mensalidade.query.get_or_404(id)
    novo_valor = float(request.form['valor'])
    mensalidade.valor = novo_valor
    db.session.commit()
    flash('Valor atualizado com sucesso!', 'sucesso')
    return redirect(url_for('financeiro.painel_mensal', mes=mensalidade.mes_referencia))


@financeiro_bp.route('/financeiro/mensalidade/<int:id>/baixar', methods=['POST'])
def baixar_mensalidade(id):
    mensalidade = Mensalidade.query.get_or_404(id)
    mensalidade.pago = True
    mensalidade.data_pagamento = datetime.strptime(request.form['data_pagamento'], '%Y-%m-%d')
    db.session.commit()
    flash('Baixa registrada com sucesso!', 'sucesso')
    return redirect(url_for('financeiro.painel_mensal', mes=mensalidade.mes_referencia))


@financeiro_bp.route('/financeiro/mensalidade/<int:id>/excluir', methods=['GET'])
def excluir_mensalidade(id):
    print(f"➡️ Tentando excluir mensalidade com ID: {id}")
    mensalidade = Mensalidade.query.get(id)

    if mensalidade:
        mes = mensalidade.mes_referencia or datetime.today().strftime('%Y-%m')
        db.session.delete(mensalidade)
        db.session.commit()
        flash(f'Mensalidade do jogador ID {mensalidade.jogador_id} excluída com sucesso!', 'sucesso')
        print(f"✅ Mensalidade ID {id} excluída")
    else:
        flash('Mensalidade não encontrada.', 'erro')
        print(f"❌ Mensalidade ID {id} não encontrada")

    return redirect(url_for('financeiro.painel_mensal', mes=mes))




@financeiro_bp.route('/financeiro/atualizar_valor', methods=['POST'])
def atualizar_valor_mensalidade_padrao():
    novo_valor = float(request.form['novo_valor'])
    mes = request.form.get('mes') or datetime.today().strftime('%Y-%m')

    config = ConfigFinanceiro.query.first()
    if not config:
        config = ConfigFinanceiro(mensalidade_padrao=novo_valor)
        db.session.add(config)
    else:
        config.mensalidade_padrao = novo_valor

    # Atualiza mensalidades não pagas do mês escolhido
    mensalidades_pendentes = Mensalidade.query.filter_by(mes_referencia=mes, pago=False).all()
    for m in mensalidades_pendentes:
        m.valor = novo_valor

    db.session.commit()
    flash(f'Valor da mensalidade atualizado para R$ {novo_valor:.2f} no mês {mes}', 'sucesso')
    return redirect(url_for('financeiro.painel_mensal', mes=mes))

@financeiro_bp.route('/financeiro/mensalidade/<int:id>/cancelar_baixa', methods=['POST'])
def cancelar_baixa_mensalidade(id):
    mensalidade = Mensalidade.query.get_or_404(id)
    mensalidade.pago = False
    mensalidade.data_pagamento = None
    db.session.commit()
    flash('Baixa cancelada com sucesso.', 'sucesso')
    return redirect(url_for('financeiro.painel_mensal', mes=mensalidade.mes_referencia))


#
#
#Modelos para Saidas em abas
#      


from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.models import db, Jogador, Categoria, Mensalidade, MovimentacaoFinanceira, ConfigFinanceiro
from datetime import datetime
from sqlalchemy import func, and_



# --------- ABA 1: ENTRADAS (MENSALIDADES) ---------
@financeiro_bp.route('/financeiro/entradas')
def exibir_entradas():
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')

    jogadores = Jogador.query.join(Categoria).filter(
        and_(
            Categoria.nome.notin_(['Convidado', 'Treinador', 'Goleiro']),
            Jogador.ativo == True
        )
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

    return render_template('financeiro/entradas.html',
                           mes=mes,
                           mensalidades=mensalidades,
                           jogadores=jogadores,
                           valor_padrao=valor_padrao)


# --------- ABA 2: SAÍDAS ---------
@financeiro_bp.route('/financeiro/saidas', methods=['GET', 'POST'])
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

    inicio_mes = datetime.strptime(mes, '%Y-%m')
    fim_mes = datetime(inicio_mes.year + (inicio_mes.month // 12), (inicio_mes.month % 12) + 1, 1)
    saidas = MovimentacaoFinanceira.query.filter(
        MovimentacaoFinanceira.tipo == 'saida',
        MovimentacaoFinanceira.data >= inicio_mes,
        MovimentacaoFinanceira.data < fim_mes
    ).all()

    return render_template('financeiro/saidas.html', mes=mes, saidas=saidas)


@financeiro_bp.route('/financeiro/saida/<int:id>/excluir')
def excluir_saida(id):
    saida = MovimentacaoFinanceira.query.get_or_404(id)
    db.session.delete(saida)
    db.session.commit()
    flash('Saída excluída com sucesso!', 'sucesso')
    return redirect(url_for('financeiro.exibir_saidas'))


# --------- ABA 3: SALDO ---------
@financeiro_bp.route('/financeiro/saldo', methods=['GET', 'POST'])
def exibir_saldo():
    mes = request.args.get('mes') or datetime.today().strftime('%Y-%m')

    # Buscar ou criar configuração
    config = ConfigFinanceiro.query.first()
    if not config:
        config = ConfigFinanceiro(mensalidade_padrao=30.00, saldo_inicial=0.0)
        db.session.add(config)
        db.session.commit()

    # Detectar primeiro mês de controle (ex: mais antigo mês com dados)
    primeiro_mes = Mensalidade.query.with_entities(Mensalidade.mes_referencia).order_by(Mensalidade.mes_referencia).first()
    mes_primeiro = primeiro_mes[0] if primeiro_mes else mes

    # Atualizar saldo inicial apenas no primeiro mês
    if request.method == 'POST' and mes == mes_primeiro:
        novo_saldo = float(request.form['saldo_inicial'])
        config.saldo_inicial = novo_saldo
        db.session.commit()
        flash('Saldo inicial atualizado com sucesso!', 'sucesso')
        return redirect(url_for('financeiro.exibir_saldo', mes=mes))

    # Calcular saldo acumulado
    saldo = config.saldo_inicial
    entradas_acumuladas = 0.0
    saidas_acumuladas = 0.0

    # Buscar todos os meses de controle ordenados
    meses_controlados = Mensalidade.query.with_entities(Mensalidade.mes_referencia).distinct().order_by(Mensalidade.mes_referencia).all()
    for m in meses_controlados:
        m_ref = m[0]

        entradas = db.session.query(func.sum(Mensalidade.valor)).filter_by(
            mes_referencia=m_ref, pago=True
        ).scalar() or 0.0

        inicio = datetime.strptime(m_ref, '%Y-%m')
        fim = datetime(inicio.year + (inicio.month // 12), (inicio.month % 12) + 1, 1)

        saidas = db.session.query(func.sum(MovimentacaoFinanceira.valor)).filter(
            MovimentacaoFinanceira.tipo == 'saida',
            MovimentacaoFinanceira.data >= inicio,
            MovimentacaoFinanceira.data < fim
        ).scalar() or 0.0

        if m_ref <= mes:
            entradas_acumuladas += entradas
            saidas_acumuladas += saidas

    saldo_final = saldo + entradas_acumuladas - saidas_acumuladas

    return render_template('financeiro/saldo.html',
        mes=mes,
        saldo=saldo_final,
        saldo_inicial=config.saldo_inicial,
        mes_primeiro=mes_primeiro,
        entradas=entradas_acumuladas,
        saidas=saidas_acumuladas
    )


#
#
#Relatorio financeiro
#
#

from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from io import BytesIO
import os

@financeiro_bp.route('/financeiro/relatorios/mensalidades')
def relatorio_mensalidades():
    hoje = datetime.today()
    mes = request.args.get('mes') or hoje.strftime('%Y-%m')
    data_vencimento = datetime.strptime(mes + '-15', '%Y-%m-%d')

    mensalidades = Mensalidade.query.filter_by(mes_referencia=mes).all()
    
    baixadas = [m for m in mensalidades if m.pago]
    vencidas = [m for m in mensalidades if not m.pago and data_vencimento < hoje]
    a_vencer = [m for m in mensalidades if not m.pago and data_vencimento >= hoje]

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    # Marca d'água
    imagem_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(imagem_path):
        escudo = ImageReader(imagem_path)
        pdf.drawImage(escudo, 200, 350, width=200, height=200, mask='auto')

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, f"RELATÓRIO DE MENSALIDADES - {mes.upper()}")

    y = altura - 100
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "✅ Mensalidades Baixadas")
    y -= 20
    pdf.setFont("Helvetica", 10)
    for m in baixadas:
        pdf.drawString(60, y, f"{m.jogador.nome} - R$ {m.valor:.2f}")
        y -= 15

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "❌ Mensalidades Vencidas")
    y -= 20
    pdf.setFont("Helvetica", 10)
    for m in vencidas:
        pdf.drawString(60, y, f"{m.jogador.nome} - R$ {m.valor:.2f}")
        y -= 15

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "🟡 Mensalidades a Vencer")
    y -= 20
    pdf.setFont("Helvetica", 10)
    for m in a_vencer:
        pdf.drawString(60, y, f"{m.jogador.nome} - R$ {m.valor:.2f}")
        y -= 15

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"relatorio_mensalidades_{mes}.pdf", mimetype='application/pdf')


@financeiro_bp.route('/financeiro/relatorios')
def pagina_relatorios():
    mes = datetime.today().strftime('%Y-%m')
    return render_template('financeiro/relatorios.html', mes=mes)


@financeiro_bp.route('/financeiro/relatorios/performance')
def relatorio_performance():
    flash("Relatório de performance ainda não disponível. Em breve!", "info")
    return redirect(url_for('financeiro.pagina_relatorios'))

@financeiro_bp.route('/financeiro/relatorios/financeiro')
def relatorio_financeiro():
    flash("Relatório financeiro ainda não está disponível. Em breve!", "info")
    return redirect(url_for('financeiro.pagina_relatorios'))


@financeiro_bp.route('/financeiro/relatorios/financeiro')
def relatorios_financeiros():
    jogadores = Jogador.query.filter_by(ativo=True).order_by(Jogador.nome).all()
    ano_atual = datetime.today().year
    return render_template('financeiro/relatorios_financeiros.html', jogadores=jogadores, ano=ano_atual)



@financeiro_bp.route('/financeiro/relatorios/fluxo_caixa')
def relatorio_fluxo_caixa():
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')

    if not inicio or not fim:
        flash("Período inválido. Selecione mês inicial e final.", "erro")
        return redirect(url_for('financeiro.relatorios_financeiros'))

    # Transformar início e fim em objetos de data
    data_inicio = datetime.strptime(inicio, "%Y-%m")
    data_fim = datetime.strptime(fim, "%Y-%m")
    hoje = datetime.today()

    if data_fim < data_inicio:
        flash("O mês final deve ser posterior ao mês inicial.", "erro")
        return redirect(url_for('financeiro.relatorios_financeiros'))

    meses = []
    cursor = data_inicio
    while cursor <= data_fim:
        meses.append(cursor.strftime('%Y-%m'))
        if cursor.month == 12:
            cursor = datetime(cursor.year + 1, 1, 1)
        else:
            cursor = datetime(cursor.year, cursor.month + 1, 1)

    dados = []
    for mes in meses:
        entradas = Mensalidade.query.filter_by(mes_referencia=mes, pago=True).all()
        total_entrada = sum(e.valor for e in entradas)

        ano, mes_num = map(int, mes.split('-'))
        inicio_mes = datetime(ano, mes_num, 1)
        fim_mes = datetime(ano + (mes_num // 12), (mes_num % 12) + 1, 1)

        saidas = MovimentacaoFinanceira.query.filter(
            MovimentacaoFinanceira.tipo == 'saida',
            MovimentacaoFinanceira.data >= inicio_mes,
            MovimentacaoFinanceira.data < fim_mes
        ).all()
        total_saida = sum(s.valor for s in saidas)

        saldo = total_entrada - total_saida

        dados.append({
            'mes': mes,
            'entrada': total_entrada,
            'saida': total_saida,
            'saldo': saldo
        })

    # PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    # Marca d’água
    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        pdf.drawImage(logo_path, 180, 320, width=250, mask='auto')

    # Cabeçalho
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, f"FLUXO DE CAIXA - {inicio} a {fim}")
    pdf.setFont("Helvetica", 10)

    y = altura - 90
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "MÊS")
    pdf.drawString(150, y, "ENTRADA")
    pdf.drawString(250, y, "SAÍDA")
    pdf.drawString(350, y, "SALDO")
    pdf.setFont("Helvetica", 10)

    y -= 20
    for d in dados:
        pdf.drawString(50, y, d['mes'])
        pdf.drawString(150, y, f"R$ {d['entrada']:.2f}")
        pdf.drawString(250, y, f"R$ {d['saida']:.2f}")
        saldo = f"R$ {d['saldo']:.2f}"
        cor = 'green' if d['saldo'] >= 0 else 'red'
        pdf.setFillColorRGB(0, 0.5, 0) if cor == 'green' else pdf.setFillColorRGB(1, 0, 0)
        pdf.drawString(350, y, saldo)
        pdf.setFillColorRGB(0, 0, 0)
        y -= 15

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"fluxo_caixa_{inicio}_a_{fim}.pdf", mimetype='application/pdf')
