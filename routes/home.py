from flask import Blueprint, render_template
from datetime import datetime
from models.models import db, Jogo, Performance

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def exibir_home():
    hoje = datetime.now()
    proximo_jogo = Jogo.query.filter(Jogo.data >= hoje).order_by(Jogo.data.asc()).first()
    ano_atual = hoje.year

    total_jogos = Jogo.query.filter(db.extract('year', Jogo.data) == ano_atual).count()
    total_gols = db.session.query(db.func.sum(Performance.gols)).scalar() or 0
    total_vitorias = Jogo.query.filter_by(resultado='vitória').filter(db.extract('year', Jogo.data) == ano_atual).count()

    return render_template('home.html',
                           proximo_jogo=proximo_jogo,
                           total_jogos=total_jogos,
                           total_gols=total_gols,
                           total_vitorias=total_vitorias)


@home_bp.route('/teste-jogo')
def teste_jogo():
    from datetime import datetime
    from models import Jogo

    hoje = datetime.now()
    jogo = Jogo.query.filter(Jogo.data >= hoje).order_by(Jogo.data.asc()).first()

    if jogo:
        return f"<h1>Próximo jogo encontrado:</h1><p>{jogo.titulo} - {jogo.data.strftime('%d/%m/%Y %H:%M')}</p>"
    else:
        return "<h1>Nenhum jogo futuro encontrado no banco.</h1>"
