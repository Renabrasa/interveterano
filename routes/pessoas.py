from flask import Blueprint, jsonify
from models.models import db, Pessoa

pessoa_bp = Blueprint('pessoa', __name__)

@pessoa_bp.route('/pessoas/transformar/<int:id>', methods=['POST'])
def transformar_convidado_em_jogador(id):
    pessoa = Pessoa.query.get_or_404(id)

    if pessoa.tipo not in ['convidado', None]:

        return jsonify({'erro': 'Apenas convidados podem ser transformados'}), 400

    pessoa.tipo = 'jogador'
    db.session.commit()
    return jsonify({'status': 'ok'})
