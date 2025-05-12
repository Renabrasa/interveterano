from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.models import db, Pessoa, Categoria, Posicao
from routes.auth import login_required
import base64
from sqlalchemy import func

convidado_bp = Blueprint('convidado', __name__, template_folder='../templates/convidado')

@convidado_bp.route('/convidados')
def exibir_convidados():
    convidados_ativos = Pessoa.query.filter(Pessoa.categoria == 'Convidado', Pessoa.ativo == True, Pessoa.data_inativacao == None).order_by(Pessoa.nome).all()
    convidados_desligados = Pessoa.query.filter(Pessoa.categoria == 'Convidado', Pessoa.ativo == True, Pessoa.data_inativacao != None).order_by(Pessoa.nome).all()

    categorias = Categoria.query.filter(Categoria.nome == 'Convidado').all()
    posicoes = Posicao.query.all()

    return render_template(
        'convidados.html',
        convidados_ativos=convidados_ativos,
        convidados_desligados=convidados_desligados,
        categorias=categorias,
        posicoes=posicoes      
    )




@convidado_bp.route('/convidados/adicionar', methods=['POST'])
def adicionar_convidado():
    nome = request.form['nome']
    categoria_id = request.form.get('categoria')
    posicao_id = request.form.get('posicao')
    pe_preferencial = request.form.get('pe_preferencial')

    # Buscar nome da categoria e da posição
    categoria = Categoria.query.get(categoria_id)
    posicao = Posicao.query.get(posicao_id)

    nova_pessoa = Pessoa(
        nome=nome,
        tipo='jogador',  # permanece como jogador
        categoria=categoria.nome if categoria else '',
        posicao=posicao.nome if posicao else '',
        pe_preferencial=pe_preferencial,
        ativo=True
    )

    # salvar imagem se existir
    foto = request.files.get('foto')
    if foto:
        nova_pessoa.foto = base64.b64encode(foto.read()).decode('utf-8')

    db.session.add(nova_pessoa)
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
    convidado = Pessoa.query.get_or_404(id)
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()

    if request.method == 'POST':
        convidado.nome = request.form['nome']
        categoria = Categoria.query.get(request.form['categoria'])
        posicao = Posicao.query.get(request.form['posicao'])

        convidado.categoria = categoria.nome if categoria else ''
        convidado.posicao = posicao.nome if posicao else ''
        convidado.pe_preferencial = request.form['pe_preferencial']
        convidado.tipo = 'convidado' if convidado.categoria.lower() == 'convidado' else 'jogador'

        foto = request.files.get('foto')
        if foto and foto.filename:
            convidado.foto = base64.b64encode(foto.read()).decode('utf-8')

        db.session.commit()
        flash('Cadastro atualizado com sucesso!', 'sucesso')
        if convidado.tipo == 'jogador':
            return redirect(url_for('plantel.exibir_plantel'))
        return redirect(url_for('convidado.exibir_convidados'))

    return render_template('convidado/editar.html', jogador=convidado, categorias=categorias, posicoes=posicoes)






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
