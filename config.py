import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'chave-secreta')
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://rena1558_interadmin:Intervet2025@interveterano.com/rena1558_intervetdb'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
