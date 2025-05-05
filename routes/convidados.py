from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.models import db, Pessoa, Categoria, Posicao
from routes.auth import login_required
import base64
from sqlalchemy import func

convidado_bp = Blueprint('convidado', __name__, template_folder='../templates/convidado')

@convidado_bp.route('/convidados')
#@login_required
def exibir_convidados():
    convidados = Pessoa.query.filter_by(tipo='convidado', ativo=True).order_by(Pessoa.nome).all()
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()
    return render_template('convidado/convidados.html', convidados=convidados, categorias=categorias, posicoes=posicoes)


@convidado_bp.route('/convidados/adicionar', methods=['POST'])
@login_required
def adicionar_convidado():
    nome = request.form['nome']
    categoria_id = request.form['categoria']
    posicao_id = request.form['posicao']
    pe_preferencial = request.form['pe_preferencial']

    # Verifica duplicidade (ignora maiúsculas/minúsculas)
    existente = Pessoa.query.filter(
        func.lower(Pessoa.nome) == nome.lower(),
        Pessoa.tipo == 'convidado'
    ).first()

    if existente:
        flash('Já existe um convidado com esse nome!', 'erro')
        return redirect(url_for('convidado.exibir_convidados'))

    foto = request.files['foto']
    foto_base64 = None
    if foto:
        foto_base64 = base64.b64encode(foto.read()).decode('utf-8')

    categoria = Categoria.query.get(categoria_id)
    posicao = Posicao.query.get(posicao_id)

    novo = Pessoa(
        nome=nome,
        categoria=categoria.nome if categoria else '',
        posicao=posicao.nome if posicao else '',
        pe_preferencial=pe_preferencial,
        foto=foto_base64,
        tipo='convidado',
        ativo=True
)

    
    db.session.add(novo)
    db.session.commit()
    return redirect(url_for('convidado.exibir_convidados'))


@convidado_bp.route('/convidados/excluir/<int:id>')
@login_required
def excluir_convidado(id):
    pessoa = Pessoa.query.get_or_404(id)
    if pessoa.tipo != 'convidado':
        flash('Este registro não é um convidado válido.', 'erro')
        return redirect(url_for('convidado.exibir_convidados'))

    db.session.delete(pessoa)
    db.session.commit()
    return redirect(url_for('convidado.exibir_convidados'))


@convidado_bp.route('/convidados/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_convidado(id):
    pessoa = Pessoa.query.get_or_404(id)
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()

    if request.method == 'POST':
        pessoa.nome = request.form['nome']
        pessoa.categoria_id = request.form['categoria']
        pessoa.posicao_id = request.form['posicao']
        pessoa.pe_preferencial = request.form['pe_preferencial']

        foto = request.files['foto']
        if foto and foto.filename != '':
            pessoa.foto = base64.b64encode(foto.read()).decode('utf-8')

        db.session.commit()
        return redirect(url_for('convidado.exibir_convidados'))

    return render_template('convidado/editar.html', convidado=pessoa, categorias=categorias, posicoes=posicoes)


@convidado_bp.route('/convidado/<int:convidado_id>/remover_foto', methods=['POST'])
@login_required
def remover_foto(convidado_id):
    pessoa = Pessoa.query.get_or_404(convidado_id)
    if pessoa.tipo != 'convidado':
        return redirect(url_for('convidado.exibir_convidados'))

    pessoa.foto = None
    db.session.commit()
    flash('Foto removida com sucesso!', 'info')
    return redirect(url_for('convidado.editar_convidado', id=pessoa.id))
