from curiosity import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from curiosity import login
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, unique=True, nullable=False, autoincrement=True, primary_key=True)
    nom = db.Column(db.String(64), index=True, nullable=False)
    prenom = db.Column(db.String(64), index=True, nullable=False)
    username_geoname = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password = db.Column(db.String(128))

    # ---- DB.RELATIONSHIP -----#
    authorshipPers = db.relationship("AuthorshipPersonne", back_populates="users")
    authorshipRegistres = db.relationship("AuthorshipRegistre", back_populates="users")


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
    date = db.Column(db.DATETIME, default=datetime.today, index=True)
    role = db.Column(db.String(12))
    # FK
    personne_id = db.Column(db.Integer, db.ForeignKey('personnes.id'))
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    # ---- DB.RELATIONSHIP -----#
    personnes = db.relationship("Personne", back_populates="authorshipPers")
    users= db.relationship("User", back_populates="authorshipPers" )

    def __repr__(self):
        return '<Auteur de la fiche Personne {}>'.format(self.id)

    @staticmethod
    def delete_authorsphiPers(id_authorshipPers):
        authorshipPers = AuthorshipPersonne.query.get(id_authorshipPers)
        db.session.delete(authorshipPers)
        db.session.commit()

    def authorPers_json(self):
        """
        Fonction qui transforme les informations sur l'auteur d'une notice personne en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        authorshipPersJson = {
            "date": str(self.date),
            "role": self.role,
            "secondName" : self.users.nom,
            "firstName" : self.users.prenom
        }
        return authorshipPersJson


class AuthorshipRegistre(db.Model):
    __tablename__ = 'authorship_registre'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    date = db.Column(db.DATETIME, default=datetime.today, index=True)
    role = db.Column(db.String(12))
    # FK
    registre_id = db.Column(db.Integer, db.ForeignKey('detailsRegistre.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # ---- DB.RELATIONSHIP -----#
    registres = db.relationship("DetailRegistre", back_populates="authorshipRegistres")
    users = db.relationship("User", back_populates="authorshipRegistres")

    def __repr__(self):
        return '<Auteur de la fiche Registre {}>'.format(self.id)

    @staticmethod
    def delete_authorsphiRegistre(id_authorshipRegistre):
        authorshipRegistre = AuthorshipRegistre.query.get(id_authorshipRegistre)
        db.session.delete(authorshipRegistre)
        db.session.commit()

    def authorRegister_json(self):
        """
        Fonction qui transforme les informations sur l'auteur d'une notice personne en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        authorshipRegisterJson = {
            "date": str(self.date),
            "role": self.role,
            "secondName" : self.users.nom,
            "firstName" : self.users.prenom
        }
        return authorshipRegisterJson
