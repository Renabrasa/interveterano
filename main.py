from flask import Flask, render_template,request
from models.models import db
from routes.plantel import plantel_bp
from routes.convidados import convidado_bp
from routes.calendario import calendario_bp
from routes.performance import performance_bp
from routes.financeiro import financeiro_bp
from routes.auth import auth_bp
import os
from routes.galeria import galeria_bp
from sqlalchemy import text
from routes.ajuste import ajuste_bp


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
app.register_blueprint(galeria_bp)
app.register_blueprint(ajuste_bp)


@app.route('/')
def home():
    return render_template('home.html')


# ================================
# EXECUÇÃO DO POPULATE
# ================================
# Executa no início para garantir que o campo exista no PostgreSQL
with app.app_context():
    with db.engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE performance ADD COLUMN gols_sofridos INTEGER DEFAULT 0"))
            print("✅ Coluna gols_sofridos criada com sucesso.")
        except Exception as e:
            print("⚠️ Coluna já existe ou erro ao criar:", e)



# ================================
# EXECUÇÃO LOCAL
# ================================
if __name__ == '__main__':
    app.run(debug=True)
