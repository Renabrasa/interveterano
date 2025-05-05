from flask import Blueprint, jsonify
from models import db, Pessoa, Performance, Jogo, Categoria, Posicao, MovimentacaoFinanceira

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/backup/json')
def gerar_backup_json():
    def serialize(obj):
        return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}

    jogadores = Pessoa.query.filter_by(tipo='jogador').all()
    convidados = Pessoa.query.filter_by(tipo='convidado').all()
    performance = Performance.query.all()
    jogos = Jogo.query.all()
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()
    movimentacoes = MovimentacaoFinanceira.query.all()

    backup_data = {
        "jogadores": [serialize(j) for j in jogadores],
        "convidados": [serialize(c) for c in convidados],
        "performance": [serialize(p) for p in performance],
        "jogos": [serialize(jg) for jg in jogos],
        "categorias": [serialize(cat) for cat in categorias],
        "posicoes": [serialize(pos) for pos in posicoes],
        "movimentacoes": [serialize(mv) for mv in movimentacoes]
    }

    return jsonify(backup_data)
