from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file,session
from models.models import db, Categoria, Mensalidade, MovimentacaoFinanceira, ConfigFinanceiro,Configuracao, Pessoa
from datetime import datetime, timedelta,date
from sqlalchemy import func,or_
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

    # Buscar pessoas que são jogadores ativos e não isentos
    jogadores = Pessoa.query.filter(
        Pessoa.ativo == True,
        Pessoa.tipo == 'jogador',
        Pessoa.categoria.notin_(['Convidado', 'Treinador', 'Goleiro'])
    ).order_by(Pessoa.nome).all()

    # Busca as mensalidades do mês (com pessoa_id válido)
    mensalidades = {
        m.pessoa_id: m for m in Mensalidade.query.filter_by(mes_referencia=mes).all() if m.pessoa_id
    }

    # Valor padrão da mensalidade
    config = ConfigFinanceiro.query.first()
    valor_padrao = config.mensalidade_padrao if config else 30.00

    # Geração automática de mensalidades faltantes
    for jogador in jogadores:
        if jogador.id not in mensalidades:
            nova = Mensalidade(
                pessoa_id=jogador.id,
                mes_referencia=mes,
                valor=valor_padrao,
                pago=False
            )
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

    return render_template(
        'financeiro/painel_mensal.html',
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
@financeiro_bp.route('/financeiro/pagar/<int:mensalidade_id>', methods=['GET','POST'], endpoint='baixar_mensalidade')
@login_required
def registrar_pagamento_mensalidade(mensalidade_id):
    mensalidade = Mensalidade.query.get_or_404(mensalidade_id)
    mensalidade.pago = True
    mensalidade.data_pagamento = date.today()
    db.session.commit()
    flash(f'Pagamento registrado para {mensalidade.pessoa.nome}', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=mensalidade.mes_referencia))

@financeiro_bp.route('/financeiro/cancelar/<int:mensalidade_id>', methods=['POST'])
@login_required
def cancelar_baixa(mensalidade_id):
    mensalidade = Mensalidade.query.get_or_404(mensalidade_id)
    mensalidade.pago = False
    db.session.commit()
    flash(f"Baixa cancelada para {mensalidade.pessoa.nome}.", "info")
    return redirect(url_for('financeiro.exibir_entradas', mes=request.args.get('mes')))


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

@financeiro_bp.route('/aplicar-novo-valor', methods=['POST'])
@login_required
def aplicar_novo_valor():
    mes = request.form.get('mes')
    valor_str = request.form.get('valor')

    if not valor_str:
        flash('O valor informado é inválido.', 'erro')
        return redirect(url_for('financeiro.exibir_entradas', mes=mes))

    try:
        novo_valor = float(valor_str)
    except ValueError:
        flash('Valor inválido para mensalidade.', 'erro')
        return redirect(url_for('financeiro.exibir_entradas', mes=mes))

    # Atualiza valor padrão da mensalidade no config
    config = Configuracao.query.first()
    if config:
        config.valor_mensalidade = novo_valor
    else:
        config = Configuracao(valor_mensalidade=novo_valor)
        db.session.add(config)

    # Atualiza mensalidades pendentes
    mensalidades = Mensalidade.query.filter_by(mes_referencia=mes).all()
    for m in mensalidades:
        if not m.pago and not m.isento_manual:
            m.valor = novo_valor

    # Cria mensalidades para jogadores que ainda não têm
    jogadores = Pessoa.query.filter(
        Pessoa.ativo == True,
        Pessoa.tipo == 'jogador',
        Pessoa.categoria.notin_(['Goleiro', 'Treinador', 'Convidado'])
    ).all()

    ids_existentes = [m.pessoa_id for m in mensalidades]

    for jogador in jogadores:
        if jogador.id not in ids_existentes:
            nova = Mensalidade(
                pessoa_id=jogador.id,
                mes_referencia=mes,
                valor=novo_valor,
                pago=False
            )
            db.session.add(nova)

    db.session.commit()
    flash('Valor atualizado e aplicado às mensalidades pendentes.', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=mes))


# ----------------------------
# Isenção manual de mensalidade
# ----------------------------


@financeiro_bp.route('/financeiro/isentar/<int:mensalidade_id>', methods=['POST'])
@login_required
def isentar_mensalidade(mensalidade_id):
    mensalidade = Mensalidade.query.get_or_404(mensalidade_id)
    mensalidade.valor = 0.00
    mensalidade.pago = False  # garante que não fique "pago"
    mensalidade.status = 'isento'  # opcional, caso use campo específico
    db.session.commit()
    flash('Mensalidade isenta com sucesso.', 'sucesso')
    return redirect(request.referrer or url_for('financeiro.exibir_entradas'))


@financeiro_bp.route('/cancelar-isencao/<int:mensalidade_id>', methods=['POST'])
def cancelar_isencao(mensalidade_id):
    mensalidade = Mensalidade.query.get_or_404(mensalidade_id)
    mensalidade.valor = 30.00  # ou valor padrão atual
    mensalidade.isento_manual = False
    db.session.commit()
    flash('Isenção cancelada com sucesso.', 'sucesso')
    return redirect(url_for('financeiro.exibir_entradas', mes=request.args.get('mes')))




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
    def escrever_titulo(titulo, lista,icone=None):
        nonlocal y
        if icone:
            icon_path = os.path.join('static', 'img', 'icons', icone)
            if os.path.exists(icon_path):
                pdf.drawImage(icon_path, 40, y - 1, width=14, height=14, mask='auto')
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, titulo)
        y -= 20
        pdf.setFont("Helvetica", 10)
        for m in lista:
           status = "Isento" if m.valor == 0 else f"R$ {m.valor:.2f}"
           pdf.drawString(60, y, f"{m.pessoa.nome} - {status}")
           y -= 15
        y -= 10

    escrever_titulo("   Baixadas (Pagas)", baixadas, 'check.png')
    escrever_titulo("   Vencidas (Não pagas)", vencidas, 'erro.png')
    escrever_titulo("   A Vencer (Ainda no prazo)", a_vencer, 'alerta.png')


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
    jogadores = Pessoa.query.filter_by(ativo=True).order_by(Pessoa.nome).all()
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


def calcular_mes_anterior(mes_str):
    mes_dt = datetime.strptime(mes_str, '%Y-%m')
    anterior = mes_dt.replace(day=1) - timedelta(days=1)
    return anterior.strftime('%Y-%m')

def calcular_mes_proximo(mes_str):
    mes_dt = datetime.strptime(mes_str, '%Y-%m')
    proximo = (mes_dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    return proximo.strftime('%Y-%m')



@financeiro_bp.route('/financeiro/entradas')
@login_required
def exibir_entradas():
    mes = request.args.get('mes') or datetime.now().strftime('%Y-%m')
    
    config = Configuracao.query.first()
    valor_config = Configuracao.query.filter_by(chave='valor_mensalidade').first()
    valor_mensalidade = float(valor_config.valor) if valor_config else 30.0

    jogadores = Pessoa.query.filter(
        Pessoa.ativo == True,
        Pessoa.tipo == 'jogador',
        or_(
            Pessoa.data_inicio_jogador == None,
            Pessoa.data_inicio_jogador <= datetime.strptime(mes, '%Y-%m')
        ),
        Pessoa.categoria.notin_(['Convidado', 'Treinador', 'Goleiro'])
    ).order_by(Pessoa.nome).all()

    for jogador in jogadores:
        existente = Mensalidade.query.filter_by(pessoa_id=jogador.id, mes_referencia=mes).first()
        if not existente:
            nova = Mensalidade(
                pessoa_id=jogador.id,
                mes_referencia=mes,
                valor=valor_mensalidade,
                pago=False
            )
            db.session.add(nova)

    db.session.commit()

    mensalidades = Mensalidade.query.filter_by(mes_referencia=mes).all()
    mensalidade_map = {m.pessoa_id: m for m in mensalidades}

    return render_template(
        'financeiro/entradas.html',
        jogadores=jogadores,
        mensalidade_map=mensalidade_map,
        valor_mensalidade=valor_mensalidade,
        mes=mes,
        mes_anterior=calcular_mes_anterior(mes),
        mes_proximo=calcular_mes_proximo(mes),
        config=config
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

        # Calcula o saldo com base no mês anterior
    mes_atual = datetime.strptime(mes, '%Y-%m')
    mes_anterior = (mes_atual.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    # Buscar saldo do mês anterior
    if mes == '2024-12':
        saldo_acumulado = config.saldo_inicial
    else:
        saldo_mes_anterior = ConfigFinanceiro.query.first().saldo_inicial
        for m in Mensalidade.query.filter(Mensalidade.mes_referencia < mes, Mensalidade.pago == True).all():
            saldo_mes_anterior += m.valor
        for s in MovimentacaoFinanceira.query.filter(MovimentacaoFinanceira.tipo == 'saida', MovimentacaoFinanceira.data < inicio).all():
            saldo_mes_anterior -= s.valor
        saldo_acumulado = saldo_mes_anterior

    saldo = saldo_acumulado + entradas - saidas

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
    mes = datetime.today().strftime('%Y-%m')
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    hoje = datetime.today()

    if not inicio or not fim:
        vencimento = datetime.strptime(mes + '-15', '%Y-%m-%d')
        mensalidades = Mensalidade.query.join(Pessoa).filter(
            Mensalidade.mes_referencia == mes,
            Mensalidade.pago == False,
            Pessoa.ativo == True,
            hoje > vencimento
        ).with_entities(
            Pessoa.nome.label('nome'),
            Pessoa.categoria.label('categoria'),
            Mensalidade.valor,
            Mensalidade.mes_referencia.label('mes')
        ).all()
        titulo = f"RELATÓRIO DE INADIMPLÊNCIA - {mes}"
    else:
        mensalidades = Mensalidade.query.join(Pessoa).filter(
            Mensalidade.mes_referencia >= inicio,
            Mensalidade.mes_referencia <= fim,
            Mensalidade.pago == False,
            Pessoa.ativo == True
        ).with_entities(
            Pessoa.nome.label('nome'),
            Pessoa.categoria.label('categoria'),
            Mensalidade.valor,
            Mensalidade.mes_referencia.label('mes')
        ).order_by(Mensalidade.mes_referencia).all()
        titulo = f"RELATÓRIO DE INADIMPLÊNCIA - DE {inicio} A {fim}"

    # Organiza os dados por mês
    agrupado = {}
    for m in mensalidades:
        agrupado.setdefault(m.mes, []).append(m)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    logo_path = os.path.join('static', 'img', 'escudo_inter.png')
    if os.path.exists(logo_path):
        logo_width = 300
        logo_height = 300
        x = (largura - logo_width) / 2
        y = (altura - logo_height) / 2
        pdf.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(largura / 2, altura - 50, titulo)

    y = altura - 100
    pdf.setFont("Helvetica", 10)
    total_geral = 0

    for mes, lista in agrupado.items():
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, f"🔸 MÊS: {mes}")
        y -= 20
        pdf.setFont("Helvetica", 10)

        subtotal = 0
        for m in lista:
            valor_str = f"R$ {m.valor:.2f}"
            if m.valor == 0:
                valor_str += " (Isento)"
            linha = f"{m.nome.ljust(30)}  {m.categoria.ljust(15)}  {valor_str.rjust(12)}"
            pdf.drawString(60, y, linha)
            y -= 15
            subtotal += m.valor

        pdf.setDash(1, 2)
        pdf.line(60, y, largura - 60, y)
        pdf.setDash()  # remove pontilhado
        y -= 15
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(largura - 60, y, f"TOTAL MÊS: R$ {subtotal:.2f}")
        total_geral += subtotal
        y -= 30

        if y < 120:
            pdf.showPage()
            y = altura - 100

    pdf.setDash(2, 2)
    pdf.setLineWidth(0.5)
    pdf.line(60, y, largura - 60, y)
    pdf.setDash()
    pdf.setLineWidth(1)

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(largura - 60, y, f"TOTAL GERAL: R$ {total_geral:.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"inadimplencia_{datetime.today().strftime('%Y-%m')}.pdf", mimetype='application/pdf')




@financeiro_bp.route('/financeiro/relatorios/individual')
@login_required
def relatorio_individual():
    from flask import request, send_file
    pessoa_id = request.args.get('pessoa_id') or request.args.get('jogador_id')
    ano = request.args.get('ano') or datetime.today().year

    if not pessoa_id:
        flash("Selecione um jogador.", "erro")
        return redirect(url_for('financeiro.relatorios_financeiros'))

    jogador = Pessoa.query.get_or_404(pessoa_id)
    mensalidades = Mensalidade.query.filter(
        Mensalidade.pessoa_id == pessoa_id,
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
        x = (largura - logo_width) / 2
        y_logo = (altura - logo_height) / 2
        pdf.drawImage(logo_path, x, y_logo, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

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

    # 🧾 Totais
    y -= 10
    total_entrada = sum(d['entrada'] for d in dados)
    total_saida = sum(d['saida'] for d in dados)
    total_saldo = total_entrada - total_saida

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "TOTAL")
    pdf.drawString(150, y, f"R$ {total_entrada:.2f}")
    pdf.drawString(250, y, f"R$ {total_saida:.2f}")
    if total_saldo >= 0:
        pdf.setFillColorRGB(0, 0.5, 0)
    else:
        pdf.setFillColorRGB(1, 0, 0)
    pdf.drawString(350, y, f"R$ {total_saldo:.2f}")
    pdf.setFillColorRGB(0, 0, 0)

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
    mes = request.form.get('mes')
    valor = float(request.form.get('valor'))

    if not mes or not valor:
        flash('Mês e valor são obrigatórios.', 'erro')
        return redirect(url_for('financeiro.exibir_entradas'))

    jogadores = Pessoa.query.filter(
        Pessoa.ativo == True,
        Pessoa.tipo == 'jogador',
        Pessoa.data_inativacao == None
    ).all()

    for jogador in jogadores:
        existente = Mensalidade.query.filter_by(pessoa_id=jogador.id, mes_referencia=mes).first()
        if not existente:
            nova = Mensalidade(
                pessoa_id=jogador.id,
                mes_referencia=mes,
                valor=valor,
                pago=False
            )
            db.session.add(nova)

    # Atualiza o valor padrão (se desejar salvar o novo valor)
    config = Configuracao.query.first()
    if config:
        config.valor_mensalidade = valor
    else:
        config = Configuracao(valor_mensalidade=valor)
        db.session.add(config)

    db.session.commit()
    flash(f'Mensalidades geradas para {mes}.', 'sucesso')
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


