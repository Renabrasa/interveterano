from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from models.models import db, Jogo, FotoJogo
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from datetime import datetime, date
from PIL import Image, ImageDraw
import random
import os

galeria_bp = Blueprint('galeria', __name__, template_folder='../templates/galeria')

@galeria_bp.route('/galeria')
def galeria():
    hoje = datetime.now().date()
    jogos_passados = Jogo.query.filter(Jogo.data <= hoje).order_by(Jogo.data.desc()).all()
    return render_template('galeria/galeria.html', jogos=jogos_passados)


@galeria_bp.route('/galeria/<int:jogo_id>')
def detalhes_galeria(jogo_id):
    jogo = Jogo.query.get_or_404(jogo_id)
    fotos = jogo.fotos
    return render_template('galeria/detalhes_galeria.html', jogo=jogo, fotos=fotos)



@galeria_bp.route('/galeria/enviar/<int:jogo_id>', methods=['GET', 'POST'])
def envio_fotos(jogo_id):
    jogo = Jogo.query.get_or_404(jogo_id)
    if request.method == 'POST':
        fotos_existentes = FotoJogo.query.filter_by(jogo_id=jogo_id).count()
        fotos = request.files.getlist('fotos')

        if fotos_existentes >= 11:
            flash('Este jogo já possui 10 fotos. Não é possível enviar mais.', 'erro')
            return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))

        if fotos_existentes + len(fotos) > 11:
            flash(f'Você pode enviar no máximo {11 - fotos_existentes} foto(s) neste jogo.', 'erro')
            return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))

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

    imagens = [Image.open(BytesIO(base64.b64decode(f.imagem_base64))).convert("RGBA") for f in fotos]

    # Tamanho padrão das fotos
    thumb_size = (200, 200)
    margin = 20
    max_width = 1200
    padding_top = 160

    # Calcular quantas fotos por linha
    fotos_por_linha = max((max_width - margin) // (thumb_size[0] + margin), 1)
    linhas = (len(imagens) + fotos_por_linha - 1) // fotos_por_linha

    largura_total = max_width
    altura_total = padding_top + (thumb_size[1] + margin) * linhas + margin

    # Criar fundo grená
    fundo = Image.new('RGB', (largura_total, altura_total), (128, 0, 0))

    # Inserir logo
    logo_path = os.path.join('static', 'img', 'logoredondo.png')
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA").resize((100, 100))
        fundo.paste(logo, ((largura_total - logo.width) // 2, 30), logo)

    # Inserir fotos organizadas em grid
    x = margin
    y = padding_top
    for idx, img in enumerate(imagens):
        img.thumbnail(thumb_size)
        fundo.paste(img, (x, y), img)

        x += thumb_size[0] + margin
        if (idx + 1) % fotos_por_linha == 0:
            x = margin
            y += thumb_size[1] + margin

    # Exportar
    buffer = BytesIO()
    fundo.save(buffer, format='PNG')
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png', download_name=f'mosaico_jogo_{jogo_id}.png')




@galeria_bp.route('/galeria/excluir/<int:foto_id>/<int:jogo_id>', methods=['POST'])
def excluir_foto(foto_id, jogo_id):
    foto = FotoJogo.query.get_or_404(foto_id)
    db.session.delete(foto)
    db.session.commit()
    flash('Foto removida com sucesso.', 'sucesso')
    return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))


@galeria_bp.route('/galeria/colagem/<int:jogo_id>/<int:quantidade>')
def exportar_colagem(jogo_id, quantidade):
    fotos = FotoJogo.query.filter_by(jogo_id=jogo_id).limit(quantidade).all()
    if not fotos or len(fotos) < quantidade:
        flash(f'É necessário pelo menos {quantidade} foto(s) para gerar esta colagem.', 'erro')
        return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))

    from PIL import ImageDraw, ImageFont

    imagens = [Image.open(BytesIO(base64.b64decode(f.imagem_base64))).convert("RGBA") for f in fotos]

    # Definições por layout
    layouts = {
        4: (2, 2),
        6: (3, 2),
        9: (3, 3),
        12: (4, 3)
    }

    colunas, linhas = layouts.get(quantidade, (3, 2))
    margem = 20
    topo = 130
    largura = 1200
    altura = 800

    thumb_w = (largura - margem * (colunas + 1)) // colunas
    thumb_h = (altura - topo - margem * (linhas + 1)) // linhas

    fundo = Image.new("RGB", (largura, altura), (128, 0, 0))  # grená

    # Logo
    logo_path = os.path.join("static", "img", "logoredondo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA").resize((100, 100))
        fundo.paste(logo, ((largura - logo.width) // 2, 10), logo)

    # Título
    jogo = Jogo.query.get_or_404(jogo_id)
    draw = ImageDraw.Draw(fundo)
    try:
        fonte = ImageFont.truetype("arial.ttf", 24)
    except:
        fonte = ImageFont.load_default()
    titulo = jogo.titulo
    data = jogo.data.strftime('%d/%m/%Y')
    bbox = draw.textbbox((0, 0), titulo, font=fonte)
    tw = bbox[2] - bbox[0]
    draw.text(((largura - tw) / 2, 115), titulo, fill="white", font=fonte)

    # Inserir fotos
    x = margem
    y = topo + margem
    idx = 0
    for linha in range(linhas):
        x = margem
        for coluna in range(colunas):
            if idx >= len(imagens):
                break
            thumb = imagens[idx].resize((thumb_w, thumb_h))
            fundo.paste(thumb, (x, y), thumb)
            x += thumb_w + margem
            idx += 1
        y += thumb_h + margem

    buffer = BytesIO()
    fundo.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", download_name=f'colagem_{quantidade}_fotos.png')


@galeria_bp.route('/galeria/colagem-canva/<int:jogo_id>')
def exportar_colagem_canva(jogo_id):
    from PIL import ImageDraw, ImageFont

    fotos = FotoJogo.query.filter_by(jogo_id=jogo_id).limit(12).all()
    if not fotos:
        flash('Nenhuma foto disponível para gerar colagem.', 'erro')
        return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))

    imagens = [Image.open(BytesIO(base64.b64decode(f.imagem_base64))).convert("RGBA") for f in fotos]

    def get_layout(qtd):
        if qtd <= 4:
            return [
                ((50, 200), (700, 400)),
                ((770, 200), (380, 190)),
                ((770, 400), (180, 200)),
                ((960, 400), (190, 200)),
            ]
        elif qtd <= 6:
            return [
                ((20, 180), (580, 400)),
                ((620, 180), (260, 200)),
                ((900, 180), (280, 200)),
                ((620, 400), (280, 180)),
                ((20, 600), (380, 260)),
                ((420, 600), (760, 260)),
            ]
        elif qtd <= 9:
            return [
                ((20, 180), (360, 220)), ((400, 180), (400, 220)), ((820, 180), (360, 220)),
                ((20, 420), (260, 200)), ((300, 420), (260, 200)), ((580, 420), (260, 200)),
                ((860, 420), (320, 200)), ((150, 640), (420, 220)), ((600, 640), (420, 220)),
            ]
        else:
            return [
                ((20, 180), (250, 180)), ((280, 180), (250, 180)), ((540, 180), (380, 180)), ((930, 180), (250, 180)),
                ((20, 370), (510, 250)), ((540, 370), (320, 250)), ((870, 370), (310, 250)),
                ((20, 630), (280, 240)), ((310, 630), (280, 240)), ((600, 630), (280, 240)), ((890, 630), (280, 240)),
                ((760, 370), (80, 250))
            ]

    def crop_center_resize(img, size):
        aspect = img.width / img.height
        target_aspect = size[0] / size[1]
        if aspect > target_aspect:
            new_width = int(target_aspect * img.height)
            offset = (img.width - new_width) // 2
            img = img.crop((offset, 0, offset + new_width, img.height))
        else:
            new_height = int(img.width / target_aspect)
            offset = (img.height - new_height) // 2
            img = img.crop((0, offset, img.width, offset + new_height))
        return img.resize(size)

    qtd = min(len(imagens), 12)
    layout = get_layout(qtd)
    canvas = Image.new("RGB", (1200, 900), (128, 0, 0))

    # Logo
    logo_path = os.path.join("static", "img", "logoredondo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA").resize((100, 100))
        canvas.paste(logo, ((1200 - 100) // 2, 20), logo)

    # Título
    jogo = Jogo.query.get_or_404(jogo_id)
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except:
        font = ImageFont.load_default()
    titulo = jogo.titulo
    bbox = draw.textbbox((0, 0), titulo, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((1200 - tw) / 2, 130), titulo, fill="white", font=font)

    for idx, (pos, tam) in enumerate(layout):
        if idx >= qtd: break
        img = crop_center_resize(imagens[idx], tam)
        canvas.paste(img, pos, img)

    buffer = BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", download_name=f'colagem_canva_{jogo_id}.png', as_attachment=True)



@galeria_bp.route('/galeria/colagem-canva/ver/<int:jogo_id>')
def visualizar_colagem_canva(jogo_id):
    fotos = FotoJogo.query.filter_by(jogo_id=jogo_id).limit(11).all()
    if not fotos:
        flash('Nenhuma foto disponível para a colagem.', 'erro')
        return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))

    imagens_base64 = []
    for foto in fotos:
        imagem = Image.open(BytesIO(base64.b64decode(foto.imagem_base64))).convert("RGBA")
        buffer = BytesIO()
        imagem.save(buffer, format='PNG')
        base64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
        imagens_base64.append(f"data:image/png;base64,{base64_img}")

    return render_template('galeria/colagem_visualizacao.html', imagens_base64=imagens_base64, jogo_id=jogo_id)
