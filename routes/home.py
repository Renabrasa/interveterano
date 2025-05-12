from flask import Blueprint, render_template
from datetime import datetime
from models.models import db, Jogo, Performance

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
def exibir_home():
    hoje = datetime.now()

    # Próximo jogo ainda futuro
    proximo_jogo = Jogo.query.filter(Jogo.data >= hoje).order_by(Jogo.data.asc()).first()

    # Contar apenas jogos já realizados neste ano
    total_jogos = Jogo.query.filter(
        db.extract('year', Jogo.data) == hoje.year,
        Jogo.data <= hoje
    ).count()

    # Soma de gols continua igual
    total_gols = db.session.query(db.func.sum(Performance.gols)).scalar() or 0

    # Contar vitórias apenas nos jogos que já aconteceram
    total_vitorias = Jogo.query.filter(
        Jogo.resultado == 'vitória',
        db.extract('year', Jogo.data) == hoje.year,
        Jogo.data <= hoje
    ).count()

    return render_template(
        'home.html',
        proximo_jogo=proximo_jogo,
        total_jogos=total_jogos,
        total_gols=total_gols,
        total_vitorias=total_vitorias
    )



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
