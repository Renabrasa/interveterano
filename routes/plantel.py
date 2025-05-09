from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.models import db, Pessoa, Categoria, Posicao
from routes.auth import login_required
import base64
from sqlalchemy import func
from datetime import datetime,date


plantel_bp = Blueprint('plantel', __name__, template_folder='../templates/plantel')



def calcular_idade(nascimento):
    hoje = date.today()
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))





@plantel_bp.route('/plantel')
def exibir_plantel():
    # [X]
    jogadores_ativos = Pessoa.query.filter_by(tipo='jogador', ativo=True).filter(
        Pessoa.data_inativacao == None
    ).order_by(Pessoa.nome).all()

    jogadores_desligados = Pessoa.query.filter_by(tipo='jogador', ativo=True).filter(
        Pessoa.data_inativacao != None
    ).order_by(Pessoa.nome).all()
    # [Y]

    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()

    return render_template(
        'plantel.html',
        jogadores_ativos=jogadores_ativos,
        jogadores_desligados=jogadores_desligados,
        categorias=categorias,
        posicoes=posicoes,
        calcular_idade=calcular_idade
    )




@plantel_bp.route('/plantel/adicionar', methods=['POST'])
@login_required
def adicionar_jogador():
    nome = request.form['nome']
    categoria_id = request.form['categoria']
    posicao_id = request.form['posicao']
    pe_preferencial = request.form['pe_preferencial']

    jogador_existente = Pessoa.query.filter(
        func.lower(Pessoa.nome) == nome.lower(),
        Pessoa.tipo == 'jogador'
    ).first()

    if jogador_existente:
        flash('Já existe um jogador com esse nome!', 'erro')
        return redirect(url_for('plantel.exibir_plantel'))

    # Buscar os nomes da categoria e posição
    categoria_nome = request.form['categoria']
    posicao_nome = request.form['posicao']


    # Foto
    foto = request.files['foto']
    foto_base64 = None
    if foto and foto.filename != '':
        foto_base64 = base64.b64encode(foto.read()).decode('utf-8')

    # Datas
    data_inativacao_str = request.form.get('data_inativacao')
    data_inativacao = datetime.strptime(data_inativacao_str, '%Y-%m-%d') if data_inativacao_str else None

    data_nascimento_str = request.form.get('data_nascimento')
    data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date() if data_nascimento_str else None

    nova_pessoa = Pessoa(
        nome=nome,
        categoria=categoria_nome,
        posicao=posicao_nome,
        pe_preferencial=pe_preferencial,
        foto=foto_base64,
        tipo='jogador',
        ativo=True,
        data_inativacao=data_inativacao,
        data_nascimento=data_nascimento 
    )
    db.session.add(nova_pessoa)
    db.session.commit()

    flash('Jogador cadastrado com sucesso!', 'sucesso')
    return redirect(url_for('plantel.exibir_plantel'))


@plantel_bp.route('/editar/<int:id>', methods=['POST'], endpoint='atualizar_jogador')
@login_required
def atualizar_jogador(id):
    jogador = Pessoa.query.get_or_404(id)

    jogador.nome = request.form['nome']
    jogador.categoria = request.form['categoria']  # nome, não ID
    jogador.posicao = request.form['posicao']      # nome, não ID
    jogador.pe_preferencial = request.form['pe_preferencial']

    data_nascimento_str = request.form.get('data_nascimento')
    jogador.data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date() if data_nascimento_str else None

    data_inativacao_str = request.form.get('data_inativacao')
    jogador.data_inativacao = datetime.strptime(data_inativacao_str, '%Y-%m-%d').date() if data_inativacao_str else None

    # Foto nova
    foto = request.files.get('foto')
    if foto and foto.filename:
        jogador.foto = base64.b64encode(foto.read()).decode('utf-8')

    db.session.commit()
    flash('Jogador atualizado com sucesso!', 'sucesso')
    return redirect(url_for('plantel.exibir_plantel'))





@plantel_bp.route('/plantel/excluir/<int:id>', methods=['GET'])
@login_required
def excluir_jogador(id):
    jogador = Pessoa.query.get_or_404(id)
    jogador.ativo = False
    jogador.data_inativacao = datetime.now()
    db.session.commit()
    flash('Jogador inativado com sucesso.', 'sucesso')
    return redirect(url_for('plantel.exibir_plantel'))




@plantel_bp.route('/plantel/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_jogador(id):
    jogador = Pessoa.query.get_or_404(id)
    categorias = Categoria.query.all()
    posicoes = Posicao.query.all()

    if request.method == 'POST':
        jogador.nome = request.form['nome']

        # Pega os nomes da categoria e posição a partir dos IDs recebidos
        categoria = Categoria.query.get(request.form['categoria'])
        posicao = Posicao.query.get(request.form['posicao'])

        jogador.categoria = categoria.nome if categoria else ''
        jogador.posicao = posicao.nome if posicao else ''
        jogador.pe_preferencial = request.form['pe_preferencial']
        data_input = request.form.get('data_inativacao')
        if data_input:
            jogador.data_inativacao = datetime.strptime(data_input, '%Y-%m-%d')
        else:
            jogador.data_inativacao = None


        foto = request.files['foto']
        if foto and foto.filename != '':
            jogador.foto = base64.b64encode(foto.read()).decode('utf-8')

        db.session.commit()
        flash('Jogador atualizado com sucesso!', 'sucesso')
        return redirect(url_for('plantel.exibir_plantel'))

    return render_template("editar.html", jogador=jogador, categorias=categorias, posicoes=posicoes)



@plantel_bp.route('/jogador/<int:jogador_id>/remover_foto', methods=['POST'])
@login_required
def remover_foto(jogador_id):
    jogador = Pessoa.query.get_or_404(jogador_id)
    jogador.foto = None
    db.session.commit()
    flash('Foto removida com sucesso!', 'info')
    return redirect(url_for('plantel.editar_jogador', id=jogador.id))

@plantel_bp.route('/plantel/desligar/<int:pessoa_id>', methods=['POST'])
@login_required
def desligar_jogador(pessoa_id):
    jogador = Pessoa.query.get_or_404(pessoa_id)
    jogador.data_inativacao = datetime.now()
    db.session.commit()
    flash(f"{jogador.nome} foi desligado do Inter.", "info")
    return redirect(url_for('plantel.exibir_plantel'))


@plantel_bp.route('/plantel/reintegrar/<int:pessoa_id>', methods=['POST'])
@login_required
def reintegrar_jogador(pessoa_id):
    jogador = Pessoa.query.get_or_404(pessoa_id)
    jogador.data_inativacao = None
    jogador.data_reintegracao = datetime.now()
    db.session.commit()
    flash(f"{jogador.nome} foi reintegrado ao Inter.", "sucesso")
    return redirect(url_for('plantel.exibir_plantel'))
