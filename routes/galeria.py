from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from models.models import db, Jogo, FotoJogo
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from PIL import Image, ImageDraw
import random
import os

galeria_bp = Blueprint('galeria', __name__, template_folder='../templates/galeria')

@galeria_bp.route('/galeria')
def galeria():
    jogos = Jogo.query.all()
    jogos_com_fotos = [jogo for jogo in jogos if jogo.fotos]
    return render_template('galeria/galeria.html', jogos=jogos_com_fotos)

@galeria_bp.route('/galeria/<int:jogo_id>')
def detalhes_galeria(jogo_id):
    jogo = Jogo.query.get_or_404(jogo_id)
    return render_template('galeria/detalhes_galeria.html', jogo=jogo)

@galeria_bp.route('/galeria/enviar/<int:jogo_id>', methods=['GET', 'POST'])
def envio_fotos(jogo_id):
    jogo = Jogo.query.get_or_404(jogo_id)
    if request.method == 'POST':
        fotos = request.files.getlist('fotos')
        for foto in fotos:
            if foto:
                imagem = foto.read()
                base64_img = base64.b64encode(imagem).decode('utf-8')
                nova_foto = FotoJogo(jogo_id=jogo_id, imagem_base64=base64_img)
                db.session.add(nova_foto)
        db.session.commit()
        flash('Fotos enviadas com sucesso!', 'sucesso')
        return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))
    return render_template('galeria/envio.html', jogo=jogo)

@galeria_bp.route('/galeria/exportar/<int:jogo_id>')
def exportar_mosaico(jogo_id):
    fotos = FotoJogo.query.filter_by(jogo_id=jogo_id).all()
    if not fotos:
        flash('Nenhuma foto para exportar.', 'erro')
        return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))

    imagens = [Image.open(BytesIO(base64.b64decode(f.imagem_base64))) for f in fotos]
    largura_total = 1000
    altura_total = 800
    fundo = Image.new('RGB', (largura_total, altura_total), (128, 0, 0))

    logo_path = os.path.join('static', 'img', 'logoredondo.png')
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).resize((80, 80))
        fundo.paste(logo, (20, 20), logo if logo.mode == 'RGBA' else None)

    for img in imagens:
        img.thumbnail((180, 180))
        x = random.randint(100, largura_total - 200)
        y = random.randint(100, altura_total - 200)
        fundo.paste(img, (x, y))

    buffer = BytesIO()
    fundo.save(buffer, format='PNG')
    buffer.seek(0)

    return send_file(buffer, mimetype='image/png', download_name=f'mosaico_jogo_{jogo_id}.png')
