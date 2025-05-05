from flask import Flask, render_template, request
from models.models import db
from routes.plantel import plantel_bp
from routes.convidados import convidado_bp
from routes.calendario import calendario_bp
from routes.performance import performance_bp
from routes.financeiro import financeiro_bp
from routes.auth import auth_bp
from routes.galeria import galeria_bp
from sqlalchemy import text
from routes.ajuste import ajuste_bp
from routes.pessoas import pessoa_bp
import os
from routes.admin import admin_bp


app = Flask(__name__)
app.secret_key = 'inter-veterano-super-segura-2025'

# ================================
# CONFIGURAÇÃO PARA POSTGRESQL NO NEON
# ================================
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL não configurada nas variáveis de ambiente.")
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ================================
# INICIALIZAÇÕES
# ================================
db.init_app(app)

with app.app_context():
    db.create_all()

# ================================
# REGISTRO DOS BLUEPRINTS
# ================================
app.register_blueprint(plantel_bp)
app.register_blueprint(convidado_bp)
app.register_blueprint(calendario_bp)
app.register_blueprint(performance_bp)
app.register_blueprint(financeiro_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(galeria_bp)
app.register_blueprint(ajuste_bp)
app.register_blueprint(pessoa_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def home():
    return render_template('home.html')

@app.errorhandler(502)
def erro_502(e):
    return render_template('erro502.html'), 502

# ================================
# EXECUÇÃO LOCAL
# ================================
if __name__ == '__main__':
    app.run(debug=True)
