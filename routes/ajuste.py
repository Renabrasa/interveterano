from flask import Blueprint
from models.models import db, FotoJogo  # ✅ Importa o modelo necessário

ajuste_bp = Blueprint('ajuste_bp', __name__)

@ajuste_bp.route('/ajustar-galeria')
def ajustar_galeria():
    try:
        db.create_all()  # Cria todas as tabelas pendentes, incluindo foto_jogo
        return "✅ Tabela 'foto_jogo' criada com sucesso no banco do Render."
    except Exception as e:
        return f"⚠️ Erro ao criar tabela: {str(e)}"
