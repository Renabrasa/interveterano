from main import app
from models.models import db, Pessoa

with app.app_context():
    try:
        db.create_all()
        print("✅ Tabela 'Pessoa' criada com sucesso no banco de dados.")
    except Exception as e:
        print(f"❌ Erro ao criar a tabela Pessoa: {e}")
