from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.models import db, Convidado, Categoria, Posicao
from routes.auth import login_required

convidado_bp = Blueprint('convidado', __name__, template_folder='../templates/convidado')

# ✅ Função de verificação de login
def login_obrigatorio():
    if 'usuario' not in session:
        session['destino'] = request.endpoint
        return redirect(url_for('auth.login'))


@convidado_bp.route('/convidados')
@login_required
def exibir_convidados():
        
    convidados = Convidado.query.all()
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()
    return render_template('convidado/convidados.html', convidados=convidados, categorias=categorias, posicoes=posicoes)

import base64

@convidado_bp.route('/convidados/adicionar', methods=['POST'])
@login_required
def adicionar_convidado():
    from sqlalchemy import func
    

    nome = request.form['nome']
    categoria_id = request.form['categoria']
    posicao_id = request.form['posicao']
    pe_preferencial = request.form['pe_preferencial']

    # Validação para impedir duplicidade (sem diferenciar maiúsculas/minúsculas)
    convidado_existente = Convidado.query.filter(func.lower(Convidado.nome) == nome.lower()).first()
    if convidado_existente:
        flash('Já existe um convidado com esse nome!', 'erro')
        return redirect(url_for('convidado.exibir_convidados'))

    foto = request.files['foto']
    foto_base64 = None
    if foto:
        foto_base64 = base64.b64encode(foto.read()).decode('utf-8')

    novo = Convidado(
        nome=nome,
        categoria_id=categoria_id,
        posicao_id=posicao_id,
        pe_preferencial=pe_preferencial,
        foto=foto_base64
    )
    db.session.add(novo)
    db.session.commit()
    return redirect(url_for('convidado.exibir_convidados'))



@convidado_bp.route('/convidados/excluir/<int:id>')
@login_required
def excluir_convidado(id):
    convidado = Convidado.query.get_or_404(id)
    db.session.delete(convidado)
    db.session.commit()
    return redirect(url_for('convidado.exibir_convidados'))

@convidado_bp.route('/convidados/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_convidado(id):
    convidado = Convidado.query.get_or_404(id)
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()

    if request.method == 'POST':
        convidado.nome = request.form['nome']
        convidado.categoria_id = request.form['categoria']
        convidado.posicao_id = request.form['posicao']
        convidado.pe_preferencial = request.form['pe_preferencial']

        foto = request.files['foto']
        if foto and foto.filename != '':
            convidado.foto = base64.b64encode(foto.read()).decode('utf-8')

        db.session.commit()
        return redirect(url_for('convidado.exibir_convidados'))

    return render_template('convidado/editar.html', convidado=convidado, categorias=categorias, posicoes=posicoes)

@convidado_bp.route('/convidado/<int:convidado_id>/remover_foto', methods=['POST'])
@login_required
def remover_foto(convidado_id):
    convidado = Convidado.query.get_or_404(convidado_id)
    convidado.foto = None
    db.session.commit()
    flash('Foto removida com sucesso!', 'info')
    return redirect(url_for('convidado.editar_convidado', id=convidado.id))
