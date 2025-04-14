from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.models import db, Jogador, Convidado, Jogo, Performance
from sqlalchemy import func
from routes.auth import login_required


performance_bp = Blueprint('performance', __name__, template_folder='../templates/performance')

# ✅ Verificação de login
def login_obrigatorio():
    if 'usuario' not in session:
        session['destino'] = request.endpoint
        return redirect(url_for('auth.login'))

# ---------------------
# ROTA PRINCIPAL (PROTEGIDA)
# ---------------------
@performance_bp.route('/performance')
@login_required
def index():
    retorno = login_obrigatorio()
    if retorno: return retorno

    jogadores = Jogador.query.all()
    convidados = Convidado.query.all()
    jogos = Jogo.query.order_by(Jogo.data.desc()).all()
    performances = Performance.query.all()

    jogadores_json = [{'id': j.id, 'nome': j.nome} for j in jogadores]
    convidados_json = [{'id': c.id, 'nome': c.nome} for c in convidados]

    return render_template(
        'performance/performance.html',
        jogadores=jogadores,
        convidados=convidados,
        jogos=jogos,
        performances=performances,
        jogadores_json=jogadores_json,
        convidados_json=convidados_json
    )

# ---------------------
# ADICIONAR (PROTEGIDA)
# ---------------------
@performance_bp.route('/performance/adicionar', methods=['POST'])
def adicionar_performance():
    retorno = login_obrigatorio()
    if retorno: return retorno

    jogo_id = request.form['jogo_id']
    tipo = request.form['tipo']
    participante_id = request.form['participante_id']
    gols = int(request.form['gols'])
    assistencias = int(request.form['assistencias'])
    participou = request.form.get('participou') == 'on'

    existente = Performance.query.filter_by(
        jogo_id=jogo_id,
        jogador_id=participante_id if tipo == 'jogador' else None,
        convidado_id=participante_id if tipo == 'convidado' else None
    ).first()

    if existente:
        return "<script>alert('Este participante já tem performance registrada neste jogo.'); window.location.href='/performance';</script>"

    nova = Performance(
        jogo_id=jogo_id,
        jogador_id=participante_id if tipo == 'jogador' else None,
        convidado_id=participante_id if tipo == 'convidado' else None,
        gols=gols,
        assistencias=assistencias,
        participou=participou
    )
    db.session.add(nova)
    db.session.commit()
    return redirect(url_for('performance.index'))

# ---------------------
# EDITAR (PROTEGIDA)
# ---------------------
@performance_bp.route('/performance/editar/<int:id>', methods=['POST'])
def editar_performance(id):
    retorno = login_obrigatorio()
    if retorno: return retorno

    perf = Performance.query.get_or_404(id)
    tipo = request.form['tipo']
    participante_id = request.form['participante_id']
    jogo_id = request.form['jogo_id']
    gols = int(request.form['gols'])
    assistencias = int(request.form['assistencias'])
    participou = request.form.get('participou') == 'on'

    duplicado = Performance.query.filter(
        Performance.jogo_id == jogo_id,
        Performance.id != id,
        Performance.jogador_id == (participante_id if tipo == 'jogador' else None),
        Performance.convidado_id == (participante_id if tipo == 'convidado' else None)
    ).first()

    if duplicado:
        flash('Este participante já está registrado neste jogo.', 'erro')
        return redirect(url_for('performance.index'))

    perf.jogo_id = jogo_id
    perf.gols = gols
    perf.assistencias = assistencias
    perf.participou = participou
    perf.jogador_id = participante_id if tipo == 'jogador' else None
    perf.convidado_id = participante_id if tipo == 'convidado' else None

    db.session.commit()
    return redirect(url_for('performance.index'))

# ---------------------
# EXCLUIR (PROTEGIDA)
# ---------------------
@performance_bp.route('/performance/excluir/<int:id>', methods=['POST'])
def excluir_performance(id):
    retorno = login_obrigatorio()
    if retorno: return retorno

    perf = Performance.query.get_or_404(id)
    db.session.delete(perf)
    db.session.commit()
    return redirect(url_for('performance.index'))

# ---------------------
# GRÁFICOS (LIVRE)
# ---------------------
@performance_bp.route('/api/performance/graficos')
def dados_graficos():
    gols = db.session.query(Jogador.nome, func.sum(Performance.gols))\
        .join(Performance, Performance.jogador_id == Jogador.id)\
        .group_by(Jogador.id).all()

    assistencias = db.session.query(Jogador.nome, func.sum(Performance.assistencias))\
        .join(Performance, Performance.jogador_id == Jogador.id)\
        .group_by(Jogador.id).all()

    participacoes = db.session.query(Jogador.nome, func.count(Performance.id))\
        .join(Performance, Performance.jogador_id == Jogador.id)\
        .filter(Performance.participou == True)\
        .group_by(Jogador.id).all()

    vitorias = db.session.query(func.count()).filter(Jogo.resultado == 'vitória').scalar()
    empates = db.session.query(func.count()).filter(Jogo.resultado == 'empate').scalar()
    derrotas = db.session.query(func.count()).filter(Jogo.resultado == 'derrota').scalar()

    def formatar(lista):
        return {'labels': [i[0] for i in lista], 'valores': [i[1] for i in lista]}

    return jsonify({
        'gols': formatar(gols),
        'assistencias': formatar(assistencias),
        'participacoes': formatar(participacoes),
        'resultados': {
            'labels': ['Vitórias', 'Empates', 'Derrotas'],
            'valores': [vitorias, empates, derrotas]
        }
    })

@performance_bp.route('/performance/graficos')
def graficos():
    return render_template('performance/graficos.html')

@performance_bp.route('/performance/grafico')
def grafico_resultados():
    vitorias = db.session.query(func.count()).filter(Jogo.resultado == 'vitória').scalar()
    empates = db.session.query(func.count()).filter(Jogo.resultado == 'empate').scalar()
    derrotas = db.session.query(func.count()).filter(Jogo.resultado == 'derrota').scalar()

    return render_template('performance/grafico.html', vitorias=vitorias, empates=empates, derrotas=derrotas)

# ---------------------
# RANKING (LIVRE)
# ---------------------
@performance_bp.route('/performance/ranking')
def ranking():
    jogadores_stats = db.session.query(
        Jogador.nome,
        func.coalesce(func.sum(Performance.gols), 0),
        func.coalesce(func.sum(Performance.assistencias), 0),
        func.count(Performance.id)
    ).join(Performance).group_by(Jogador.id).all()

    convidados_stats = db.session.query(
        Convidado.nome,
        func.coalesce(func.sum(Performance.gols), 0),
        func.coalesce(func.sum(Performance.assistencias), 0),
        func.count(Performance.id)
    ).join(Performance).group_by(Convidado.id).all()

    ranking_total = []

    for nome, gols, assist, part in jogadores_stats:
        ranking_total.append({'nome': nome + " (Jogador)", 'gols': gols, 'assist': assist, 'part': part})

    for nome, gols, assist, part in convidados_stats:
        ranking_total.append({'nome': nome + " (Convidado)", 'gols': gols, 'assist': assist, 'part': part})

    ranking_total.sort(key=lambda x: (x['gols'], x['assist'], x['part']), reverse=True)

    return render_template('performance/ranking.html', ranking=ranking_total)
