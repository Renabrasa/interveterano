from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class Categoria(db.Model):
    __tablename__ = 'categoria'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)

class Posicao(db.Model):
    __tablename__ = 'posicao'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)

class Jogador(db.Model):
    __tablename__ = 'jogador'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    posicao_id = db.Column(db.Integer, db.ForeignKey('posicao.id'), nullable=False)
    pe_preferencial = db.Column(db.String(20), nullable=False)
    foto = db.Column(db.Text, nullable=True)  # base64 da imagem
    ativo = db.Column(db.Boolean, default=True, nullable=False)


    categoria = db.relationship('Categoria', backref=db.backref('jogadores', lazy=True))
    posicao = db.relationship('Posicao', backref=db.backref('jogadores', lazy=True))


#
#
#Modelos para convidados 
#
class Convidado(db.Model):
    __tablename__ = 'convidado'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    posicao_id = db.Column(db.Integer, db.ForeignKey('posicao.id'), nullable=False)
    pe_preferencial = db.Column(db.String(20), nullable=False)
    foto = db.Column(db.Text, nullable=True)

    categoria = db.relationship('Categoria', backref=db.backref('convidados', lazy=True))
    posicao = db.relationship('Posicao', backref=db.backref('convidados', lazy=True))
    
    
#
#
#Modelos para calendário
#    

class Jogo(db.Model):
    __tablename__ = 'jogo'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    data = db.Column(db.DateTime, nullable=False)
    local = db.Column(db.String(100), nullable=True)
    inter_mandante = db.Column(db.Boolean, default=False)
    resultado = db.Column(db.String(20))  # vitória, empate, derrota

    
#MOsaico com as fotos de cada jogo 

class FotoJogo(db.Model):
    __tablename__ = 'foto_jogo'
    id = db.Column(db.Integer, primary_key=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey('jogo.id'), nullable=False)
    imagem_base64 = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)

    jogo = db.relationship("Jogo", backref="fotos")




#
#Modelos para performance
#      

class Performance(db.Model):
    __tablename__ = 'performance'
    id = db.Column(db.Integer, primary_key=True)

    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=True)
    jogo_id = db.Column(db.Integer, db.ForeignKey('jogo.id'), nullable=False)

    gols = db.Column(db.Integer, default=0)
    gols_sofridos = db.Column(db.Integer, default=0)
    assistencias = db.Column(db.Integer, default=0)
    participou = db.Column(db.Boolean, default=True)

    pessoa = db.relationship('Pessoa', backref=db.backref('performances', lazy=True))
    jogo = db.relationship('Jogo', backref=db.backref('performances', lazy=True))

#
#
#Modelos para modulo financeiro
# 

class MovimentacaoFinanceira(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False)  # 'entrada' ou 'saida'
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    categoria = db.Column(db.String(50), nullable=False)  # exemplo: 'Mensalidade', 'Aluguel', etc
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=True)

    pessoa = db.relationship('Pessoa', backref='movimentacoes')



class Mensalidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pessoa_id = db.Column(db.Integer, db.ForeignKey('pessoa.id'), nullable=False)
    mes_referencia = db.Column(db.String(7), nullable=False)  # ex: 2024-05
    valor = db.Column(db.Float, nullable=False)
    pago = db.Column(db.Boolean, default=False)
    data_pagamento = db.Column(db.Date)
    isento_manual = db.Column(db.Boolean, default=False)

    pessoa = db.relationship('Pessoa',backref='mensalidades')


    

class ConfigFinanceiro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensalidade_padrao = db.Column(db.Float, default=30.00)
    saldo_inicial = db.Column(db.Float, default=0.0)


class Pessoa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    posicao = db.Column(db.String(50))  # zagueiro, meia, etc
    pe_preferencial = db.Column(db.String(10))
    foto = db.Column(db.String(200))
    tipo = db.Column(db.String(20), nullable=False)  # 'jogador', 'convidado', etc
    ativo = db.Column(db.Boolean, default=True)
    categoria = db.Column(db.String(50))  # opcional
    data_inativacao = db.Column(db.DateTime, nullable=True)
    data_reintegracao = db.Column(db.DateTime, nullable=True)
    data_nascimento = db.Column(db.Date, nullable=True)  # ✅ NOVO CAMPO


class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(100), nullable=False)
