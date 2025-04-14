from flask import Flask, render_template
from models.models import db
from routes.plantel import plantel_bp
from routes.convidados import convidado_bp
from routes.calendario import calendario_bp
from routes.performance import performance_bp
from routes.financeiro import financeiro_bp
from routes.auth import auth_bp


import os

app = Flask(__name__)
app.secret_key = 'inter-veterano-super-segura-2025'  # ou qualquer string segura

# Caminho absoluto para o banco SQLite na pasta 'instance'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'inter.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa banco e blueprint
db.init_app(app)
app.register_blueprint(plantel_bp)
app.register_blueprint(convidado_bp)
app.register_blueprint(calendario_bp)
app.register_blueprint(performance_bp)
app.register_blueprint(financeiro_bp)
app.register_blueprint(auth_bp)

# Rota home
@app.route('/')
def home():
    return render_template('home.html')

# Executa a aplicação
if __name__ == '__main__':
    app.run(debug=True)
