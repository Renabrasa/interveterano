from main import app
from models.models import db, ConfigFinanceiro

with app.app_context():
    if not ConfigFinanceiro.query.first():
        db.session.add(ConfigFinanceiro(mensalidade_padrao=30.00))
        db.session.commit()
