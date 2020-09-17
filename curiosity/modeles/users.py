from curiosity import db
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from curiosity import login

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, unique=True, nullable=False, autoincrement=True, primary_key=True)
    nom = db.Column(db.String(64), index=True, nullable=False)
    prenom = db.Column(db.String(64), index=True, nullable=False)
    username_geoname = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password = db.Column(db.String(128))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class AuthorshipPersonne(db.Model):
    __tablename__  ='authorship_personne'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    personne_id = db.Column(db.Integer, db.ForeignKey('personnes.id'))
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    date = db.Column(db.TIMESTAMP, default=datetime.datetime.utcnow,index=True)


    def __repr__(self):
        return '<Auteur de la fiche Personne {}>'.format(self.username)