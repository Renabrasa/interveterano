from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from models.models import db, Jogo
from datetime import datetime

calendario_bp = Blueprint('calendario', __name__, template_folder='../templates/calendario')


# Página do calendário
@calendario_bp.route('/calendario')
def exibir_calendario():
    logado = session.get('logado', False)
    return render_template('calendario.html', logado=logado)
''

# API para retornar os jogos em JSON (para o FullCalendar)
@calendario_bp.route('/api/jogos')
def listar_jogos():
    jogos = Jogo.query.all()
    eventos = []
    for jogo in jogos:
        eventos.append({
            'id': jogo.id,
            'title': jogo.titulo,
            'start': jogo.data.strftime('%Y-%m-%dT%H:%M:%S'),
        })
    return jsonify(eventos)


# Criar novo jogo
@calendario_bp.route('/api/jogos', methods=['POST'])
def criar_jogo():
    if not session.get('logado'):
        return jsonify({"erro": "Acesso não autorizado"}), 403

    dados = request.get_json()

    try:
        data_formatada = dados.get('data')
        if not data_formatada:
            return jsonify({'erro': 'Data não informada'}), 400

        data_obj = datetime.fromisoformat(data_formatada)

        novo = Jogo(
            titulo=dados.get('titulo', ''),
            data=data_obj,
            local=dados.get('local', ''),
            inter_mandante=bool(dados.get('inter_mandante', False)),
            resultado=dados.get('resultado')  # pode ser None
        )
        db.session.add(novo)
        db.session.commit()

        return jsonify({'status': 'ok', 'id': novo.id})

    except Exception as e:
        return jsonify({'erro': f'Erro ao criar jogo: {str(e)}'}), 400




# Atualizar jogo
@calendario_bp.route('/api/jogos/<int:id>', methods=['PUT'])
def editar_jogo(id):
    if not session.get('logado'):
        return jsonify({"erro": "Acesso não autorizado"}), 403
    jogo = Jogo.query.get_or_404(id)
    dados = request.json
    jogo.titulo = dados['titulo']
    jogo.data = datetime.fromisoformat(dados['data'])
    jogo.local = dados.get('local')
    jogo.inter_mandante = dados.get('inter_mandante', False)
    jogo.resultado = dados.get('resultado')  # NOVO
    db.session.commit()
    return jsonify({'status': 'ok'})



# Excluir jogo
@calendario_bp.route('/api/jogos/<int:id>', methods=['DELETE'])
def excluir_jogo(id):
    if not session.get('logado'):
        return jsonify({"erro": "Acesso não autorizado"}), 403
    jogo = Jogo.query.get_or_404(id)
    db.session.delete(jogo)
    db.session.commit()
    return jsonify({'status': 'ok'})

@calendario_bp.route('/api/jogos/<int:id>')
def obter_jogo(id):
    jogo = Jogo.query.get_or_404(id)
    return jsonify({
        'id': jogo.id,
        'titulo': jogo.titulo,
        'data': jogo.data.isoformat(),
        'local': jogo.local,
        'inter_mandante': jogo.inter_mandante,
        'resultado': jogo.resultado  # NOVO
    })


from flask import send_file
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import calendar as cal_mod
import base64
from datetime import date

# Retorna jogos do mês em JSON
@calendario_bp.route('/api/jogos/mes')
def jogos_do_mes():
    data_str = request.args.get('data')  # yyyy-mm-dd
    data_str = data_str[:10]  # garante que só pegue 'yyyy-mm-dd'
    data_ref = datetime.strptime(data_str, '%Y-%m-%d')
    ano, mes = data_ref.year, data_ref.month

    jogos = Jogo.query.filter(
        db.extract('year', Jogo.data) == ano,
        db.extract('month', Jogo.data) == mes
    ).order_by(Jogo.data).all()

    lista = []
    for j in jogos:
        lista.append({
            'id': j.id,
            'titulo': j.titulo,
            'data': j.data.isoformat(),
            'data_formatada': j.data.strftime('%d/%m %H:%Mh'),
            'local': j.local,
            'inter_mandante': j.inter_mandante
        })
    return jsonify(lista)


# Gera o PDF da agenda do mês
@calendario_bp.route('/exportar/agenda')
def exportar_agenda_pdf():
    mes_param = request.args.get('mes')  # formato yyyy-mm
    ano, mes = map(int, mes_param.split('-'))
    meses_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    nome_mes = meses_pt[mes - 1]


    jogos = Jogo.query.filter(
        db.extract('year', Jogo.data) == ano,
        db.extract('month', Jogo.data) == mes
    ).order_by(Jogo.data).all()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    # Marca d'água escudo
    try:
        with open('static/img/escudo_inter.png', 'rb') as f:
            imagem_base64 = base64.b64encode(f.read()).decode()
           # Centralizar imagem em A4 (21cm x 29.7cm)
            img_width = 12 * cm
            img_height = 12 * cm
            x = (21 * cm - img_width) / 2
            y = (29.7 * cm - img_height) / 2
            p.drawImage(f"data:image/png;base64,{imagem_base64}", x, y, width=img_width, height=img_height, mask='auto')

    except:
        pass  # Se a imagem não existir, ignora

    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(10.5*cm, 27*cm, f"AGENDA DE JOGOS DO MÊS {nome_mes.upper()}")

    # Lista dos jogos
    p.setFont("Helvetica", 12)
    y = 25.5*cm
    if not jogos:
        p.drawString(2.5*cm, y, "Nenhum jogo agendado.")
    else:
        for j in jogos:
            data_str = j.data.strftime('%d/%m %H:%Mh')
            linha = f"{data_str} — {j.titulo} | Local: {j.local} | Inter mandante: {'Sim' if j.inter_mandante else 'Não'}"
            p.drawString(2.5*cm, y, linha)
            y -= 1*cm
            if y < 2*cm:
                p.showPage()
                y = 27*cm

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'agenda_{mes_param}.pdf', mimetype='application/pdf')
