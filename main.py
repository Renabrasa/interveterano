from flask import Flask, render_template,request
from models.models import db
from routes.plantel import plantel_bp
from routes.convidados import convidado_bp
from routes.calendario import calendario_bp
from routes.performance import performance_bp
from routes.financeiro import financeiro_bp
from routes.auth import auth_bp
import os

app = Flask(__name__)
app.secret_key = 'inter-veterano-super-segura-2025'

# ================================
# CONFIGURAÇÃO PARA POSTGRESQL NO RENDER
# ================================
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql://interadmin:S12In5Kcd2ZDtCFLH177JUZ4cWIyi4DH'
    '@dpg-d02n42adbo4c73f097sg-a/interveterano_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ================================
# INICIALIZAÇÕES
# ================================
db.init_app(app)

app.register_blueprint(plantel_bp)
app.register_blueprint(convidado_bp)
app.register_blueprint(calendario_bp)
app.register_blueprint(performance_bp)
app.register_blueprint(financeiro_bp)
app.register_blueprint(auth_bp)

@app.route('/')
def home():
    return render_template('home.html')


# ================================
# EXECUÇÃO DO POPULATE
# ================================


@app.route('/rodar-populate')
def rodar_populate():
    chave = request.args.get('chave')
    if chave != 'intersegura2025':
        return "Acesso não autorizado", 403

    from models.models import db, Categoria, Posicao

    db.create_all()

    categorias = ['Jogador', 'Treinador', 'Convidado', 'Presidente', 'Goleiro']
    for nome in categorias:
        if not Categoria.query.filter_by(nome=nome).first():
            db.session.add(Categoria(nome=nome))

    posicoes = ['Goleiro', 'Zagueiro', 'Lateral', 'Volante', 'Meia', 'Atacante','Centroavante', 'Ponta', 'Treinador','Presidente']
    for nome in posicoes:
        if not Posicao.query.filter_by(nome=nome).first():
            db.session.add(Posicao(nome=nome))

    db.session.commit()
    return "✅ Banco populado com sucesso!"



# ================================
# EXECUÇÃO LOCAL
# ================================
if __name__ == '__main__':
    app.run(debug=True)
