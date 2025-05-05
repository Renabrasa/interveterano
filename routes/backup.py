# routes/backup.py

from flask import Blueprint, send_file
from io import BytesIO
import json
from models import db, Pessoa, Mensalidade, MovimentacaoFinanceira

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/backup/json')
def gerar_backup_json():
    dados = {
        "pessoas": [p.serializar() for p in Pessoa.query.all()],
        "mensalidades": [m.serializar() for m in Mensalidade.query.all()],
        "movimentacoes": [mv.serializar() for mv in MovimentacaoFinanceira.query.all()]
    }

    buffer = BytesIO()
    buffer.write(json.dumps(dados, indent=2, ensure_ascii=False).encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/json',
        as_attachment=True,
        download_name='backup_intervet.json'
    )
