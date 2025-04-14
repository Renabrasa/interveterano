from flask import Blueprint, render_template, request, redirect, url_for,session
from models.models import db, Jogador, Categoria, Posicao
from flask import flash
from routes.auth import login_required


plantel_bp = Blueprint('plantel', __name__, template_folder='../templates/plantel')

# ✅ Função de verificação de login
def login_obrigatorio():
    if 'usuario' not in session:
        session['destino'] = request.endpoint
        return redirect(url_for('auth.login'))


@plantel_bp.route('/plantel')
@login_required
def exibir_plantel():
    retorno = login_obrigatorio()
    if retorno: return retorno
    
    jogadores = Jogador.query.filter_by(ativo=True).all()
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()
    return render_template('plantel.html', jogadores=jogadores, categorias=categorias, posicoes=posicoes)

import base64

@plantel_bp.route('/plantel/adicionar', methods=['POST'])
def adicionar_jogador():
    from sqlalchemy import func
    nome = request.form['nome']
    categoria_id = request.form['categoria']
    posicao_id = request.form['posicao']
    pe_preferencial = request.form['pe_preferencial']
    
    # Verifica se já existe jogador com mesmo nome (ignora maiúsculas/minúsculas)
    jogador_existente = Jogador.query.filter(func.lower(Jogador.nome) == nome.lower()).first()
    if jogador_existente:
        from flask import flash
        flash('Já existe um jogador com esse nome!', 'erro')
        return redirect(url_for('plantel.exibir_plantel'))

    foto = request.files['foto']
    foto_base64 = None
    if foto:
        foto_base64 = base64.b64encode(foto.read()).decode('utf-8')

    novo_jogador = Jogador(
        nome=nome,
        categoria_id=categoria_id,
        posicao_id=posicao_id,
        pe_preferencial=pe_preferencial,
        foto=foto_base64
    )
    db.session.add(novo_jogador)
    db.session.commit()
    return redirect(url_for('plantel.exibir_plantel'))



@plantel_bp.route('/plantel/excluir/<int:id>', methods=['GET'])
def excluir_jogador(id):
    jogador = Jogador.query.get_or_404(id)
    jogador.ativo = False
    db.session.commit()
    flash('Jogador removido do plantel (soft delete).', 'sucesso')
    return redirect(url_for('plantel.exibir_plantel'))



@plantel_bp.route('/plantel/editar/<int:id>', methods=['GET', 'POST'])
def editar_jogador(id):
    jogador = Jogador.query.get_or_404(id)
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()

    if request.method == 'POST':
        jogador.nome = request.form['nome']
        jogador.categoria_id = request.form['categoria']
        jogador.posicao_id = request.form['posicao']
        jogador.pe_preferencial = request.form['pe_preferencial']

        foto = request.files['foto']
        if foto and foto.filename != '':
            jogador.foto = base64.b64encode(foto.read()).decode('utf-8')

        db.session.commit()
        return redirect(url_for('plantel.exibir_plantel'))

    return render_template('plantel/editar.html', jogador=jogador, categorias=categorias, posicoes=posicoes)

