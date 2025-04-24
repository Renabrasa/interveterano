from flask import Blueprint
from models.models import db
from sqlalchemy import text

ajuste_bp = Blueprint('ajuste', __name__)

@ajuste_bp.route('/ajustar-tabelas')
def ajustar_tabelas():
    try:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE mensalidade ADD COLUMN isento_manual BOOLEAN DEFAULT FALSE"))
        return "✅ Coluna isento_manual criada com sucesso no banco do Render."
    except Exception as e:
        return f"⚠️ Erro ou já existe: {str(e)}"