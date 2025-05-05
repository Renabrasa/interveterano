from flask import Blueprint, render_template, redirect, url_for, flash
from models.models import db, Pessoa, Performance, Mensalidade,Jogador,Convidado



admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/ferramentas', endpoint='ferramentas')
def ferramentas():
    return render_template('admin/ferramentas.html')


@admin_bp.route('/ferramentas/migrar_performance', methods=['POST'])
def migrar_performance():
    performances = Performance.query.filter(Performance.jogador_id != None).all()
    migrados = 0
    for p in performances:
        jogador = Jogador.query.get(p.jogador_id)
        pessoa = Pessoa.query.filter_by(nome=jogador.nome, tipo='jogador').first()
        if pessoa:
            p.pessoa_id = pessoa.id
            migrados += 1
    db.session.commit()
    flash(f'{migrados} performances migradas.', 'sucesso')
    return redirect(url_for('admin.ferramentas'))


@admin_bp.route('/ferramentas/migrar_jogadores', methods=['POST'])
def migrar_jogadores():
    
    count = 0
    for j in Jogador.query.all():
        if not Pessoa.query.filter_by(nome=j.nome, tipo='jogador').first():
            nova = Pessoa(
                nome=j.nome,
                categoria=j.categoria.nome if j.categoria else '',
                posicao=j.posicao.nome if j.posicao else '',
                pe_preferencial=j.pe_preferencial,
                foto=j.foto,
                tipo='jogador',
                ativo=True
            )
            db.session.add(nova)
            count += 1
    db.session.commit()
    flash(f'{count} jogadores migrados.', 'sucesso')
    return redirect(url_for('admin.ferramentas'))


@admin_bp.route('/ferramentas/migrar_convidados', methods=['POST'])
def migrar_convidados():
    from models.models import Convidado, Pessoa
    count = 0
    for c in Convidado.query.all():
        if not Pessoa.query.filter_by(nome=c.nome, tipo='convidado').first():
            nova = Pessoa(
                nome=c.nome,
                categoria=c.categoria.nome if c.categoria else '',
                posicao=c.posicao.nome if c.posicao else '',
                pe_preferencial=c.pe_preferencial,
                foto=c.foto,
                tipo='convidado',
                ativo=True
            )
            db.session.add(nova)
            count += 1
    db.session.commit()
    flash(f'{count} convidados migrados.', 'sucesso')
    return redirect(url_for('admin.ferramentas'))

@admin_bp.route('/ferramentas/migrar_mensalidades', methods=['POST'])
def migrar_mensalidades():
    from models.models import Pessoa, Mensalidade
    count = 0

    for m in Mensalidade.query.filter(Mensalidade.pessoa_id == None).all():
        if not m.pessoa:
            continue  # ignora registros sem vínculo nomeado

        pessoa = Pessoa.query.filter_by(nome=m.pessoa.nome, tipo='jogador').first()
        if pessoa:
            m.pessoa_id = pessoa.id
            count += 1

    db.session.commit()
    flash(f'{count} mensalidades migradas com sucesso.', 'sucesso')
    return redirect(url_for('admin.ferramentas'))


@admin_bp.route('/ferramentas/limpar_mensalidades_invalidas', methods=['POST'])
def limpar_mensalidades_invalidas():
    from models.models import Mensalidade
    registros = Mensalidade.query.filter(Mensalidade.pessoa_id == None).all()
    total = 0
    for r in registros:
        db.session.delete(r)
        total += 1
    db.session.commit()
    flash(f'{total} mensalidades inválidas removidas.', 'sucesso')
    return redirect(url_for('admin.ferramentas'))

@admin_bp.route('/ferramentas/limpeza')
def limpeza_codigo():
    import os

    referencias = []
    caminho_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    for pasta_raiz, _, arquivos in os.walk(caminho_base):
        for arquivo in arquivos:
            if arquivo.endswith(('.py', '.html', '.js')):
                caminho_completo = os.path.join(pasta_raiz, arquivo)
                try:
                    with open(caminho_completo, 'r', encoding='utf-8') as f:
                        linhas = f.readlines()
                        for i, linha in enumerate(linhas):
                            linhax = linha.strip()
                        if (
                            not linhax.startswith('#') and
                            (
                                'from models' in linhax and ('Jogador' in linhax or 'Convidado' in linhax) or
                                'Jogador.query' in linhax or
                                'Convidado.query' in linhax or
                                '.query.join(Jogador' in linhax or
                                '.query.join(Convidado' in linhax or
                                'join(Jogador' in linhax or
                                'join(Convidado' in linhax or
                                'class Jogador' in linhax or
                                'class Convidado' in linhax
                            )
                        ):

                                referencias.append({
                                    'arquivo': caminho_completo.replace(caminho_base + os.sep, ''),
                                    'linha': i + 1,
                                    'conteudo': linha.strip()
                                })
                except Exception as e:
                    continue  # ignora arquivos com erro

    return render_template('admin/limpeza.html', referencias=referencias)
