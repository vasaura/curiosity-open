from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_images import Images
from datetime import timedelta

# le nom de la variable appli m'appartient
appli = Flask(__name__)
# importer la configuration de l'application
appli.config.from_object(Config)

# permet de visualiser les requetes en format sql. A supprimer an production car elle génère trop de logs.
#appli.config['SQLALCHEMY_ECHO'] = True

# se déconnecter au bout de 40 mminutes d'inactivité
appli.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=40)


# définition de l'objet qui représente la base de données
db = SQLAlchemy(appli)
# définition de l'objet qui représente l'opérateur de migration
migrate = Migrate(appli, db)

login = LoginManager(appli)
bootstrap = Bootstrap(appli)
images = Images(appli)
# la valeur 'login' porte le même nom que la fonction de la route qui permet de créer le login
# cette configuration permet ensuite ouvrir des pages web de manière séléctive aux users.
login.login_view = 'login'


# on importe les routes à la fin
from curiosity import routes
from curiosity.modeles import personnes_registres, users
