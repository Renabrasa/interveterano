from flask import Blueprint, jsonify,request, redirect, url_for, render_template
from models.models import db, Pessoa
from datetime import datetime


pessoa_bp = Blueprint('pessoa', __name__)

@pessoa_bp.route('/pessoas/transformar/<int:id>', methods=['POST'])
def transformar_convidado_em_jogador(id):
    pessoa = Pessoa.query.get_or_404(id)

    if pessoa.categoria.lower() != 'convidado':
        return jsonify({'erro': 'Apenas pessoas com categoria "convidado" podem ser transformadas'}), 400

    nova_data = request.form.get('data_inicio_jogador')
    if not nova_data:
        return jsonify({'erro': 'Informe a data de início como jogador'}), 400

    pessoa.categoria = 'jogador'
    pessoa.data_inicio_jogador = datetime.strptime(nova_data, '%Y-%m-%d').date()
    db.session.commit()
    return redirect(url_for('convidado.exibir_convidados'))
