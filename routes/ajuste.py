from flask import Blueprint
from models.models import db
from sqlalchemy import text

ajuste_bp = Blueprint('ajuste', __name__)

@ajuste_bp.route('/ajustar-tabelas')
def ajustar_tabelas():
    try:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE performance ADD COLUMN gols_sofridos INTEGER DEFAULT 0"))
        return "✅ Coluna gols_sofridos criada no banco do Render."
    except Exception as e:
        return f"⚠️ Erro ou coluna já existe: {str(e)}"