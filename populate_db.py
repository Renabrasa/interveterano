from flask import Flask
from models.models import db, Categoria, Posicao

app = Flask(__name__)
app.secret_key = 'inter-veterano-super-segura-2025'

# Configuração do banco PostgreSQL no Render
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql://interadmin:S12In5Kcd2ZDtCFLH177JUZ4cWIyi4DH'
    '@dpg-d02n42adbo4c73f097sg-a/interveterano_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()  # Garante que todas as tabelas sejam criadas

    categorias = ['Jogador', 'Treinador', 'Convidado', 'Presidente', 'Goleiro']
    for nome in categorias:
        if not Categoria.query.filter_by(nome=nome).first():
            db.session.add(Categoria(nome=nome))

    posicoes = [
        'Goleiro', 'Zagueiro', 'Lateral', 'Volante', 'Meia',
        'Atacante', 'Centroavante', 'Ponta', 'Treinador', 'Presidente'
    ]
    for nome in posicoes:
        if not Posicao.query.filter_by(nome=nome).first():
            db.session.add(Posicao(nome=nome))

    db.session.commit()
    print("✅ Categorias e posições inseridas com sucesso no PostgreSQL!")
