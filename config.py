import os

# séparer l'application de la configuration par la création de ce fichier config.py
# installer la l'extention Flask-WTF: pip install flask-wtf

class Config(object):
    # les items de configurations peuvent être utiliser avec la syntaxe d'un dictionnaire.
    # récupère la valeur de la clé 'SECRET_KEY' qui est you-will-never-guess
    # l'equivalement de SECRET_KEY = os.environ.get('SECRET_KEY', 'you-will-never-guess')flask run
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'



    # configuration de la partie MYSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    IMAGES_PATH = ["curiosity/static/images/"]

    # pour la gestion des logs
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')