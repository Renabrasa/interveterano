from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.models import db,Jogo, Performance, Categoria,Posicao,Pessoa
from sqlalchemy import func
from routes.auth import login_required
from sqlalchemy.orm import joinedload
from flask import jsonify
from datetime import datetime

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
    hoje = datetime.now()
    pessoas = Pessoa.query.filter_by(ativo=True).all()
    jogos = Jogo.query.filter(Jogo.data <= hoje).order_by(Jogo.data.desc()).all()
    performances = Performance.query.all()

    # Garante que pessoas_json será renderizado corretamente
    pessoas_json = [
        {
            "id": p.id,
            "nome": p.nome,
            "categoria": p.categoria,
            "posicao": p.posicao
        }
        for p in pessoas
    ]

    return render_template(
        'performance/performance.html',
        pessoas=pessoas,
        jogos=jogos,
        performances=performances,
        pessoas_json=pessoas_json,
        hoje=hoje.date()
    ) 

    

# ---------------------
# ADICIONAR (PROTEGIDA)
# ---------------------
@performance_bp.route('/performance/adicionar', methods=['POST'])
@login_required
def adicionar_performance():
    jogo_id = request.form['jogo_id']
    participante_id = request.form['participante_id']
    gols = int(request.form['gols'])
    gols_sofridos = int(request.form.get('gols_sofridos') or 0)
    assistencias = int(request.form['assistencias'])
    participou = request.form.get('participou') == 'on'

    # Verifica se já existe performance para a mesma pessoa e jogo
    existente = Performance.query.filter_by(
        jogo_id=jogo_id,
        pessoa_id=participante_id
    ).first()

    if existente:
        return "<script>alert('Este participante já tem performance registrada neste jogo.'); window.location.href='/performance';</script>"

    nova = Performance(
        jogo_id=jogo_id,
        pessoa_id=participante_id,
        gols=gols,
        gols_sofridos=gols_sofridos,
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
@login_required
def editar_performance(id):
    perf = Performance.query.get_or_404(id)

    participante_id = request.form['participante_id']
    jogo_id = request.form['jogo_id']
    gols = int(request.form['gols'])
    gols_sofridos = int(request.form.get('gols_sofridos') or 0)
    assistencias = int(request.form['assistencias'])
    participou = request.form.get('participou') == 'on'

    # Verifica se já existe outra performance com mesmo participante e jogo
    duplicado = Performance.query.filter(
        Performance.jogo_id == jogo_id,
        Performance.pessoa_id == participante_id,
        Performance.id != id
    ).first()

    if duplicado:
        flash('Este participante já está registrado neste jogo.', 'erro')
        return redirect(url_for('performance.index'))

    # Atualiza os dados
    perf.jogo_id = jogo_id
    perf.pessoa_id = participante_id
    perf.gols = gols
    perf.gols_sofridos = gols_sofridos
    perf.assistencias = assistencias
    perf.participou = participou

    db.session.commit()
    return redirect(url_for('performance.index'))


# ---------------------
# EXCLUIR (PROTEGIDA)
# ---------------------
@performance_bp.route('/performance/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_performance(id):
    

    perf = Performance.query.get_or_404(id)
    db.session.delete(perf)
    db.session.commit()
    return redirect(url_for('performance.index'))


#
# Rotas para goleiros
#

@performance_bp.route('/performance/goleiro/<int:jogador_id>/gols_sofridos')
@login_required
def grafico_gols_sofridos(jogador_id):
    dados = db.session.query(
        Jogo.data,
        Jogo.titulo,
        Performance.gols
    ).join(Jogo).join(Jogador).join(Categoria).filter(
        Performance.jogador_id == jogador_id,
        (Jogador.posicao == 'Goleiro') | (Categoria.nome == 'Goleiro')
    ).order_by(Jogo.data).all()

    resultado = [
        {'data': data.strftime('%d/%m'), 'titulo': titulo, 'gols': gols}
        for data, titulo, gols in dados
    ]
    return jsonify(resultado)




# ---------------------
# GRÁFICOS (LIVRE)
# ---------------------
@performance_bp.route('/api/performance/graficos')
def dados_graficos():
    from models.models import Pessoa

    # GOLS > 0
    gols = db.session.query(Pessoa.nome, func.sum(Performance.gols))\
        .join(Pessoa, Performance.pessoa_id == Pessoa.id)\
        .filter(Performance.gols > 0)\
        .group_by(Pessoa.id)\
        .all()

    # ASSISTÊNCIAS > 0
    assistencias = db.session.query(Pessoa.nome, func.sum(Performance.assistencias))\
        .join(Pessoa, Performance.pessoa_id == Pessoa.id)\
        .filter(Performance.assistencias > 0)\
        .group_by(Pessoa.id)\
        .all()

    # PARTICIPAÇÕES
    participacoes = db.session.query(Pessoa.nome, func.count(Performance.id))\
        .join(Pessoa, Performance.pessoa_id == Pessoa.id)\
        .filter(Performance.participou == True)\
        .group_by(Pessoa.id)\
        .all()

    # RESULTADOS (vitórias, empates, derrotas)
    vitorias = db.session.query(func.count()).filter(Jogo.resultado == 'vitória').scalar()
    empates = db.session.query(func.count()).filter(Jogo.resultado == 'empate').scalar()
    derrotas = db.session.query(func.count()).filter(Jogo.resultado == 'derrota').scalar()

    # GOLEIROS: Pessoa com posicao ou categoria = Goleiro
    goleiros = db.session.query(Pessoa.nome, func.sum(Performance.gols_sofridos))\
        .join(Pessoa, Performance.pessoa_id == Pessoa.id)\
        .filter(
            (Pessoa.posicao.ilike('goleiro')) | (Pessoa.categoria.ilike('goleiro')),
            Performance.gols_sofridos > 0
        )\
        .group_by(Pessoa.id)\
        .all()

    def formatar(lista):
        return {'labels': [i[0] for i in lista], 'valores': [i[1] for i in lista]}

    return jsonify({
        'gols': formatar(gols),
        'assistencias': formatar(assistencias),
        'participacoes': formatar(participacoes),
        'resultados': {
            'labels': ['Vitórias', 'Empates', 'Derrotas'],
            'valores': [vitorias, empates, derrotas]
        },
        'goleiros': formatar(goleiros)
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
    pessoas_stats = db.session.query(
        Pessoa.id,
        Pessoa.nome,
        Pessoa.foto,
        Pessoa.posicao,
        Pessoa.categoria,
        func.coalesce(func.sum(Performance.gols), 0).label('gols'),
        func.coalesce(func.sum(Performance.assistencias), 0).label('assistencias'),
        func.count(Performance.id).label('part')
    ).join(Performance, Performance.pessoa_id == Pessoa.id)\
     .filter(Pessoa.ativo == True)\
     .filter(Performance.pessoa_id != None)\
     .group_by(Pessoa.id)\
     .all()

    ranking_total = []

    for id, nome, foto, posicao, categoria, gols, assist, part in pessoas_stats:
        ranking_total.append({
            'nome': nome,
            'foto': foto,
            'categoria': categoria.capitalize() if categoria else '',
            'gols': gols,
            'assist': assist,
            'part': part,
            'posicao': posicao or ''
        })

    ranking_total.sort(key=lambda x: (x['gols'], x['assist'], x['part']), reverse=True)

    return render_template('performance/ranking.html', ranking=ranking_total)






