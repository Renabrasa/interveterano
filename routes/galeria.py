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

    imagens = [Image.open(BytesIO(base64.b64decode(foto.imagem_base64))) for foto in fotos]


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



from flask import send_file, redirect, url_for, flash
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64
import os

@galeria_bp.route('/galeria/colagem-canva/<int:jogo_id>')
def exportar_colagem_canva(jogo_id):
    fotos = FotoJogo.query.filter_by(jogo_id=jogo_id).limit(12).all()
    if not fotos:
        flash('Nenhuma foto disponível para gerar colagem.', 'erro')
        return redirect(url_for('galeria.detalhes_galeria', jogo_id=jogo_id))
    
    # Obter dados do jogo
    jogo = Jogo.query.get_or_404(jogo_id)
    
    # Processar imagens
    imagens, proporcoes = [], []
    for foto in fotos:
        try:
            img_data = base64.b64decode(foto.imagem_base64)
            img = Image.open(BytesIO(img_data)).convert("RGB")
            imagens.append(img)
            proporcoes.append("paisagem" if img.width > img.height else "retrato")
        except Exception as e:
            print("Erro ao processar imagem:", e)
    
    # Configurar canvas
    largura_canvas = 1200
    altura_canvas = 1500  # Altura inicial, será ajustada com base no conteúdo
    espacamento = 10      # Reduzido para minimizar espaço em branco
    margem = 12           # Reduzido para maximizar área útil
    
    # Criar canvas com cor de fundo semelhante ao exemplo (vermelho escuro)
    canvas = Image.new("RGB", (largura_canvas, altura_canvas), (153, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Adicionar logo na parte superior
    logo_path = os.path.join("static", "img", "logoredondo.png")
    logo_size = 120
    logo_y = margem
    
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA").resize((logo_size, logo_size))
            canvas.paste(logo, ((largura_canvas - logo_size) // 2, logo_y), logo)
        except Exception as e:
            print(f"Erro ao processar logo: {e}")
    
    # Adicionar título
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 32)
        except:
            font = ImageFont.load_default()
    
    titulo_y = logo_y + logo_size + 10  # Reduzido o espaçamento
        # Define nomes dos times
    time_casa = "INTER"
    time_visitante = jogo.titulo.upper() if jogo.titulo else "ADVERSÁRIO"
    titulo_formatado = f"{time_casa}  X  {time_visitante}"

    # Escreve título centralizado abaixo do logo
    text_bbox = draw.textbbox((0, 0), titulo_formatado, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    draw.text(((largura_canvas - text_width) // 2, titulo_y), titulo_formatado, fill="white", font=font)

    
    # Iniciar posicionamento das imagens
    current_y = titulo_y + text_height + 15  # Reduzido o espaçamento
    
    # Classificar imagens
    paisagens = [i for i, p in enumerate(proporcoes) if p == "paisagem"]
    retratos = [i for i, p in enumerate(proporcoes) if p == "retrato"]
    
    # Função especializada para ajustar imagens preservando a parte superior (rostos)
    def ajustar_imagem(img, max_width, max_height):
        """
        Redimensiona a imagem para preencher o espaço disponível, preservando a parte superior
        onde geralmente estão os rostos nas fotos.
        """
        # Calcular as proporções
        ratio_width = max_width / img.width
        ratio_height = max_height / img.height
        
        # Para evitar corte de cabeças, usamos o seguinte critério:
        # - Para fotos de retrato (mais altas que largas), preservamos a parte superior
        # - Para fotos de paisagem, centralizamos horizontalmente
        
        is_portrait = img.height > img.width
        
        # Usa o menor ratio para garantir que toda a imagem caiba no espaço (sem cortes)
        ratio = min(ratio_width, ratio_height)
        
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)
        
        # Redimensiona a imagem mantendo proporção
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Cria uma nova imagem com o tamanho exato desejado
        final_img = Image.new("RGB", (max_width, max_height), (153, 0, 0))
        
        # Define a posição de colagem
        paste_x = (max_width - new_width) // 2  # Sempre centralizado horizontalmente
        
        # Se for retrato, prioriza a parte superior (cabeças)
        # Se for paisagem, centraliza verticalmente
        if is_portrait:
            paste_y = 0  # Alinha com o topo para preservar rostos
        else:
            paste_y = (max_height - new_height) // 2  # Centraliza verticalmente
        
        # Cola a imagem redimensionada na posição calculada
        final_img.paste(resized_img, (paste_x, paste_y))
        return final_img
    
    # Função para montar layouts específicos com base na quantidade de imagens
    def criar_layout():
        nonlocal current_y
        remaining_imgs = list(range(len(imagens)))
        
        # Layout 1: Layout de destaque (1 grande + 2 pequenas à direita)
        if len(imagens) >= 3:
            # Selecionar imagem destaque (preferência para paisagem)
            destaque_idx = paisagens[0] if paisagens else 0
            remaining_imgs.remove(destaque_idx)
            
            # Dimensões para o layout de destaque
            destaque_width = int(largura_canvas * 0.68) - margem - espacamento
            destaque_height = int(destaque_width * 0.7)  # Proporção ajustável
            
            pequenas_width = int(largura_canvas * 0.32) - margem - espacamento
            pequenas_height = (destaque_height - espacamento) // 2
            
            # Colocar imagem destaque
            img_destaque = ajustar_imagem(imagens[destaque_idx], destaque_width, destaque_height)
            canvas.paste(img_destaque, (margem, current_y))
            
            # Colocar duas imagens pequenas à direita
            for i in range(2):
                if not remaining_imgs:
                    break
                    
                small_idx = remaining_imgs.pop(0)
                img_small = ajustar_imagem(imagens[small_idx], pequenas_width, pequenas_height)
                small_x = margem + destaque_width + espacamento
                small_y = current_y + (i * (pequenas_height + espacamento))
                canvas.paste(img_small, (small_x, small_y))
            
            current_y += destaque_height + espacamento
        
        # Layout 2: Linha de 3 imagens iguais
        if len(remaining_imgs) >= 3:
            img_width = (largura_canvas - 2*margem - 2*espacamento) // 3
            img_height = int(img_width * 1.0)  # Proporção aumentada para preencher mais espaço
            
            for i in range(3):
                if not remaining_imgs:
                    break
                    
                idx = remaining_imgs.pop(0)
                img = ajustar_imagem(imagens[idx], img_width, img_height)
                x = margem + i * (img_width + espacamento)
                canvas.paste(img, (x, current_y))
            
            current_y += img_height + espacamento
        
        # Layout 3: Linha com 1 imagem grande à esquerda e 1 pequena à direita (se houver mais imagens)
        if len(remaining_imgs) >= 2:
            left_width = int(largura_canvas * 0.68) - margem - espacamento
            right_width = int(largura_canvas * 0.32) - margem - espacamento
            row_height = int(left_width * 0.65)  # Proporção aumentada para ocupar mais espaço vertical
            
            # Selecionar imagem para esquerda (preferência para paisagem)
            left_idx = next((i for i in remaining_imgs if i in paisagens), remaining_imgs[0])
            remaining_imgs.remove(left_idx)
            
            img_left = ajustar_imagem(imagens[left_idx], left_width, row_height)
            canvas.paste(img_left, (margem, current_y))
            
            right_idx = remaining_imgs.pop(0)
            img_right = ajustar_imagem(imagens[right_idx], right_width, row_height)
            right_x = margem + left_width + espacamento
            canvas.paste(img_right, (right_x, current_y))
            
            current_y += row_height + espacamento
        
        # Layout 4: Imagem de grupo ou restantes
        if remaining_imgs:
            if len(remaining_imgs) == 1:
                # Uma imagem grande ocupando toda a largura
                idx = remaining_imgs.pop(0)
                img_width = largura_canvas - 2*margem
                img_height = int(img_width * 0.65)  # Proporção aumentada para mais espaço vertical
                
                img = ajustar_imagem(imagens[idx], img_width, img_height)
                canvas.paste(img, (margem, current_y))
                current_y += img_height + espacamento
            else:
                # Grid para imagens restantes - otimizado para preencher mais espaço
                if len(remaining_imgs) == 2:
                    # Para 2 imagens, colocar lado a lado com tamanho igual
                    img_width = (largura_canvas - 2*margem - espacamento) // 2
                    img_height = int(img_width * 1.0)  # Proporção quadrada
                    
                    for i, idx in enumerate(remaining_imgs):
                        img = ajustar_imagem(imagens[idx], img_width, img_height)
                        x = margem + i * (img_width + espacamento)
                        canvas.paste(img, (x, current_y))
                    
                    current_y += img_height + espacamento
                else:
                    # Grid dinâmico para 3+ imagens
                    # Ajusta o número de colunas com base na quantidade de imagens
                    cols = min(3, len(remaining_imgs))
                    img_width = (largura_canvas - 2*margem - (cols-1)*espacamento) // cols
                    img_height = int(img_width * 1.0)  # Proporção quadrada para maximizar espaço
                    
                    row = 0
                    col = 0
                    
                    for idx in remaining_imgs:
                        img = ajustar_imagem(imagens[idx], img_width, img_height)
                        x = margem + col * (img_width + espacamento)
                        y = current_y + row * (img_height + espacamento)
                        canvas.paste(img, (x, y))
                        
                        col += 1
                        if col >= cols:
                            col = 0
                            row += 1
                    
                    current_y += (row + 1) * img_height + row * espacamento + espacamento
    
    # Criar layout baseado nas imagens disponíveis
    criar_layout()
    
    # Ajustar altura final do canvas e remover espaço preto
    final_height = min(current_y + margem,canvas.height)
    
    # Recortar o canvas para o tamanho exato - sem espaço preto extra
    canvas_final = canvas.crop((0, 0, largura_canvas, final_height))
    
    # Salvar e retornar a imagem
    buffer = BytesIO()
    canvas_final.save(buffer, format="PNG")
    buffer.seek(0)
    
    return send_file(buffer, mimetype="image/png", download_name=f'colagem_{jogo.titulo.replace(" ", "_")}_{jogo_id}.png', as_attachment=False)

@galeria_bp.route('/galeria/visualizar-colagem/<int:jogo_id>')
def visualizar_colagem_canva(jogo_id):
    jogo = Jogo.query.get_or_404(jogo_id)
    return render_template('galeria/colagem_visualizacao.html', jogo=jogo)
