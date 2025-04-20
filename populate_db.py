from flask import Flask
from models.models import db, Categoria, Posicao
import os

# Garantir o caminho certo para o banco
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'inter.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    categorias = ['Jogador', 'Treinador', 'Convidado', 'Presidente', 'Goleiro']
    for nome in categorias:
        if not Categoria.query.filter_by(nome=nome).first():
            db.session.add(Categoria(nome=nome))

    posicoes = ['Goleiro', 'Zagueiro', 'Lateral', 'Volante', 'Meia', 'Atacante','Centroavante', 'Ponta', 'Treinador','Presidente']
    for nome in posicoes:
        if not Posicao.query.filter_by(nome=nome).first():
            db.session.add(Posicao(nome=nome))

    db.session.commit()
    print("✅ Categorias e posições inseridas com sucesso!")
