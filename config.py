import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta')
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://seulogin_usuario:suasenhasecreta123@br000.mysql.hostgator.com/seulogin_meubanco'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
