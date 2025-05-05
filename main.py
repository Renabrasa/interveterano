from flask import Flask, render_template
from models.models import db
from config import Config

# Blueprints
from routes.plantel import plantel_bp
from routes.convidados import convidado_bp
from routes.calendario import calendario_bp
from routes.performance import performance_bp
from routes.financeiro import financeiro_bp
from routes.auth import auth_bp
from routes.galeria import galeria_bp
from routes.pessoas import pessoa_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object(Config)

# Inicializa DB
db.init_app(app)

with app.app_context():
    db.create_all()

# Registro de Blueprints
app.register_blueprint(plantel_bp)
app.register_blueprint(convidado_bp)
app.register_blueprint(calendario_bp)
app.register_blueprint(performance_bp)
app.register_blueprint(financeiro_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(galeria_bp)
app.register_blueprint(pessoa_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def home():
    return render_template('home.html')

@app.errorhandler(502)
def erro_502(e):
    return render_template('erro502.html'), 502

# Para rodar localmente
if __name__ == '__main__':
    app.run()
