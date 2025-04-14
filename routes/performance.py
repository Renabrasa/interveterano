from flask import Blueprint, render_template, request, redirect, url_for,session
from models.models import db, Jogador, Convidado, Jogo, Performance
from flask import flash


performance_bp = Blueprint('performance', __name__, template_folder='../templates/performance')

# ✅ Função de verificação de login
def login_obrigatorio():
    if 'usuario' not in session:
        session['destino'] = request.endpoint
        return redirect(url_for('auth.login'))


# Página principal da performance
@performance_bp.route('/performance')
def index():
    retorno = login_obrigatorio()
    if retorno: return retorno
    
    jogadores = Jogador.query.all()
    convidados = Convidado.query.all()
    jogos = Jogo.query.order_by(Jogo.data.desc()).all()
    performances = Performance.query.all()

    # Convertendo apenas os dados necessários para o JavaScript (JSON serializável)
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


# Cadastro de nova performance
@performance_bp.route('/performance/adicionar', methods=['POST'])
def adicionar_performance():
    jogo_id = request.form['jogo_id']
    tipo = request.form['tipo']
    participante_id = request.form['participante_id']
    gols = int(request.form['gols'])
    assistencias = int(request.form['assistencias'])
    participou = request.form.get('participou') == 'on'

    # Verifica duplicidade
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



# Rota para editar performance
@performance_bp.route('/performance/editar/<int:id>', methods=['POST'])
def editar_performance(id):
    perf = Performance.query.get_or_404(id)

    tipo = request.form['tipo']
    participante_id = request.form['participante_id']
    jogo_id = request.form['jogo_id']
    gols = int(request.form['gols'])
    assistencias = int(request.form['assistencias'])
    participou = request.form.get('participou') == 'on'

    # Validação: impedir duplicidade ao editar (exclui a própria performance da verificação)
    duplicado = Performance.query.filter(
        Performance.jogo_id == jogo_id,
        Performance.id != id,
        Performance.jogador_id == (participante_id if tipo == 'jogador' else None),
        Performance.convidado_id == (participante_id if tipo == 'convidado' else None)
    ).first()

    if duplicado:
       flash('Este participante já está registrado neste jogo.', 'erro')
       return redirect(url_for('performance.index'))


    # Atualiza dados
    perf.jogo_id = jogo_id
    perf.gols = gols
    perf.assistencias = assistencias
    perf.participou = participou
    perf.jogador_id = participante_id if tipo == 'jogador' else None
    perf.convidado_id = participante_id if tipo == 'convidado' else None

    db.session.commit()
    return redirect(url_for('performance.index'))

# Rota para excluir performance
@performance_bp.route('/performance/excluir/<int:id>', methods=['POST'])
def excluir_performance(id):
    perf = Performance.query.get_or_404(id)
    db.session.delete(perf)
    db.session.commit()
    return redirect(url_for('performance.index'))

################################
####### GRAFICOS ###############
################################

from flask import jsonify
from sqlalchemy import func

# Rota para retornar dados para os gráficos
@performance_bp.route('/api/performance/graficos')
def dados_graficos():
    from sqlalchemy import func

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
        return {
            'labels': [item[0] for item in lista],
            'valores': [item[1] for item in lista]
        }

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
    from sqlalchemy import func
    from models.models import Jogo

    vitorias = db.session.query(func.count()).filter(Jogo.resultado == 'vitória').scalar()
    empates = db.session.query(func.count()).filter(Jogo.resultado == 'empate').scalar()
    derrotas = db.session.query(func.count()).filter(Jogo.resultado == 'derrota').scalar()

    return render_template('performance/grafico.html', vitorias=vitorias, empates=empates, derrotas=derrotas)




################################
####### RAnking ###############
################################


@performance_bp.route('/performance/ranking')
def ranking():
    from sqlalchemy import func

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

    # Ordena por gols, depois assistências, depois participações
    ranking_total.sort(key=lambda x: (x['gols'], x['assist'], x['part']), reverse=True)

    return render_template('performance/ranking.html', ranking=ranking_total)
