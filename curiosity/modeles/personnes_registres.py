from curiosity import db
from flask import url_for

class Personne(db.Model):
    # les attributs des classes doivent avoir les mêmes noms que les champs de la base Mysql
    __tablename__ = 'personnes'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    nom = db.Column(db.String(64), index=True)
    prenom = db.Column(db.String(64), index=True)
    certitudeNP = db.Column(db.String(64))
    sexe = db.Column(db.String(12), nullable=False)
    anneeNaissance = db.Column(db.String(12))
    observations = db.Column(db.Text)
    dateDeces = db.Column(db.Date)
    # FK
    id_lieuxNaissance = db.Column(db.Integer, db.ForeignKey("lieux.id"))
    id_lieuDeces = db.Column(db.Integer, db.ForeignKey("lieux.id") )

    #---- DB.RELATIONSHIPS -----#
    # back_populates fait référence au nom de l'attribut du modèle en miroir mentionné.
    lieux_naissance = db.relationship("Lieu", foreign_keys = [id_lieuxNaissance])
    lieux_deces = db.relationship("Lieu", foreign_keys = [id_lieuDeces])
    registresPers = db.relationship("DetailRegistre", back_populates = "personnes")
    voyageAvecPers = db.relationship("VoyageAvec", back_populates="personnes" )
    authorshipPers = db.relationship("AuthorshipPersonne", back_populates="personnes")

    def __repr__(self):
        return '<Personne {}>'.format(self.nom)

    @staticmethod
    def create_person(nom, prenom, sexe, anneeNaissance, observations, id_lieuxNaissance, dateDeces, id_lieuDeces,certitudeNP,authorshipPers):
        # on vérifie qu'au moins un des deux champs (nom, prénom) est rempli
        errors = []
        if not nom:
            errors.append("Le nom est obligatoire")
        # vérifier que le champ genre est bien coché

        if not sexe:
            errors.append("Le champ sexe est obligatoire: 'Femme', 'Homme', 'Inconnu' ")
        # si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        # vérifier que la taille des caractères insérés (nom, prenonm, surnom) ne dépasse pas la limite acceptée par mysql
        if len(nom) > 64 or len(prenom) > 64 :
            errors.append("La taille des caractères du nom, ou du prénom a été dépassée. Alertez l'administrateur de la base")
        if len(errors) > 0:
            return False, errors

        # vérifier que la taille des caractères insérés (date) ne dépasse pas la limite acceptée par mysql

        if anneeNaissance :
            if len(anneeNaissance) != 4:
                errors.append("La taille des caractères est incorect pour l'année de naissance ")
            if not anneeNaissance.startswith("1"):
                errors.append("L'année de naissance est incorrecte")
            if len(errors) > 0:
                return False, errors
        else :
            anneeNaissance = None

        if prenom == "":
            prenom = None

        if observations == "":
            observations = None

        if id_lieuxNaissance =="":
            id_lieuxNaissance = None

        if id_lieuDeces =="":
            id_lieuDeces = None

        if certitudeNP =="":
            certitudeNP = None

        # vérifier si la personne existe: si le nom, le prénom, le sexe, l'année de naissance sont identiques.
        personne = Personne.query.filter(db.and_(Personne.nom == nom, Personne.prenom == prenom, Personne.anneeNaissance == anneeNaissance, Personne.id_lieuxNaissance==id_lieuxNaissance, Personne.sexe ==sexe)).count()
        if personne > 0:
            errors.append("Une où plusieurs personnes portant le même nom existent déjà.")

        if dateDeces == '':
            dateDeces = None

         # Si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        # S'il n'y a pas d'erreur, on crée une nouvelle personne dans la table Personnes
        created_person = Personne(
            nom=nom,
            prenom=prenom,
            sexe=sexe,
            anneeNaissance=anneeNaissance,
            observations=observations,
            id_lieuxNaissance=id_lieuxNaissance,
            dateDeces=dateDeces,
            id_lieuDeces=id_lieuDeces,
            certitudeNP=certitudeNP,
        )

        for authorship in authorshipPers:
            created_person.authorshipPers.append(authorship)

        try:
            # création de la nouvelle personne :
            db.session.add(created_person)
            db.session.commit() 

            # Renvoie d'informations vers l'utilisateur :
            return True, created_person

        except Exception as error_creation:
            return False, [str(error_creation)]

    @staticmethod
    def modify_person(id,nom, prenom, sexe, anneeNaissance, observations, id_lieuxNaissance, dateDeces, id_lieuDeces, certitudeNP, authorshipPers):
        # on vérifie qu'au moins un des deux champs (nom, prénom) est rempli
        errors = []
        if not nom:
            errors.append("Le nom est obligatoire")
        # vérifier que le champ genre est bien coché

        if not sexe:
            errors.append("Le champ sexe est obligatoire: 'Femme', 'Homme', 'Inconnu' ")
        # si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        # vérifier que la taille des caractères insérés (nom, prenonm, surnom) ne dépasse pas la limite acceptée par mysql
        if len(nom) > 64 or len(prenom) > 64:
            errors.append(
                "La taille des caractères du nom, ou du prénom a été dépassée. Alertez l'administrateur de la base")
        if len(errors) > 0:
            return False, errors

        # vérifier que la taille des caractères insérés (date) ne dépasse pas la limite acceptée par mysql

        if anneeNaissance:
            if len(anneeNaissance) != 4:
                errors.append("La taille des caractères est incorect pour l'année de naissance ")
            if not anneeNaissance.startswith("1"):
                errors.append("L'année de naissance est incorrecte")
            if len(errors) > 0:
                return False, errors
        else:
            anneeNaissance = None

        if prenom == "":
            prenom = None

        if observations == "":
            observations = None

        if id_lieuxNaissance == "":
            id_lieuxNaissance = None

        if id_lieuDeces == "":
            id_lieuDeces = None

        if certitudeNP == "":
            certitudeNP = None

        if dateDeces == '':
            dateDeces = None

        # Si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        personne = Personne.query.get(id)
        if personne.nom == nom and personne.prenom == prenom and personne.anneeNaissance == anneeNaissance and\
                    personne.id_lieuxNaissance == id_lieuxNaissance and Personne.sexe == sexe:
            errors.append("Une où plusieurs personnes portant le même nom existent déjà. Alertez l'administrateur de la base")

        if len(errors) > 0:
            return False, errors

        else:
            # on fait une affectation d'attributs à l'objet lieu
            personne.nom = nom
            personne.prenom = prenom
            personne.sexe = sexe
            personne.anneeNaissance = anneeNaissance
            personne.observations = observations
            personne.id_lieuxNaissance = id_lieuxNaissance
            personne.dateDeces = dateDeces
            personne.id_lieuDeces = id_lieuDeces
            personne.certitudeNP=certitudeNP

            for authorship in authorshipPers:
                personne.authorshipPers.append(authorship)

        try:
            # création de la nouvelle personne :

            db.session.commit()

            # Renvoie d'informations vers l'utilisateur :
            return True, personne

        except Exception as error_creation:
            return False, [str(error_creation)]

    @staticmethod
    def supprimer_personne(id_personne):
        """
        Fonction qui supprime la notice unique de la personne (à faire évoluterpour supprimer  aussi les voyages
        :param id_personne: l'identifiant de la personne à récupérer dans l'adresse de la notice
        :type id_personne: int
        :returns : Booleens
        """
        # récupération de l'objet personne
        personneUnique = Personne.query.get(id_personne)

        db.session.delete(personneUnique)
        db.session.commit()

    def personne_json(self):
        """
        Fonction qui transforme les informations sur une personne en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        if self.lieux_naissance:
            lieuNaissance = self.lieux_naissance.lieu_json()
        else:
            lieuNaissance = "non renseigné"

        if self.lieux_deces:
            lieuDeces = self.lieux_deces.lieu_json()
        else:
            lieuDeces = "non renseigné"

        personneJson = {
            "type": "personne",
            "id": self.id,
            "attributes" : {
                "secondName": self.nom,
                "firstName": self.prenom,
                "sex": self.sexe,
                "yearOfBirth": self.anneeNaissance,
                "observations": self.observations,
                "dateOfDeath": str(self.dateDeces),
                "authorsOfPersonRecord": [author.authorPers_json() for author in self.authorshipPers],
                "places": {
                    "placeOfBirth": lieuNaissance,
                    "placeOfDeath": lieuDeces
                },
            },

           "register":  [registre.register_json() for registre in self.registresPers],
            "links": {
                "html": url_for("notice", identifier=self.id, _external=True),
                "self": url_for("api_personne", identifier=self.id, _external=True)
            },

        }
        return personneJson

class Lieu (db.Model):
    __tablename__ = "lieux"
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    nomLieuFr = db.Column(db.String(64))
    nomLieuOrig = db.Column(db.String(64))
    pays = db.Column(db.String(64))
    region = db.Column(db.String(64))
    departement = db.Column(db.String(64))
    codeINSEE = db.Column(db.String(64))
    id_geonames = db.Column(db.String(64),unique=True)
    lat = db.Column(db.String(64), nullable=False)
    lng = db.Column(db.String(64), nullable=False)

    # ---- DB.RELATIONSHIPS -----#
    # db.relationships. back_populates fait référence au nom de l'attribut du modèle mentionné.
    lieuxDeclares = db.relationship("LieuDeclare", back_populates="lieux")

    # db.relationship avec primaryjoin pour les tables qui contiennent plusieurs FK du lieu
    lieuxNaissance = db.relationship("Personne", primaryjoin = "Lieu.id==Personne.id_lieuxNaissance",  back_populates="lieux_naissance")
    lieuxDeces = db.relationship("Personne", primaryjoin = "Lieu.id==Personne.id_lieuDeces",  back_populates="lieux_deces")



    def __repr__(self):
        return '<Lieu {}>'.format(self.nomLieuFr)

    @staticmethod
    def create_lieu(nomLieuFr, pays, region, departement, codeINSEE, id_geonames, lat, lng):
        # on vérifie qu'au moins un des deux champs (nom, prénom) est rempli
        errors = []
        if not nomLieuFr:
            errors.append("Le champ 'Nom du lieu' est obligatoire")
        # vérifier que le champ genre est bien coché

        if not lat and not lng:
            errors.append("Les champs latitude et longitude sont obligatoires")
        # si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        # vérifier que la taille des caractères insérés (nom, coordonénes) ne dépasse pas la limite acceptée par mysql
        if len(nomLieuFr) > 64 :
            errors.append(
                "La taille des caractères du nom du lieu, ou des coordonnées a été dépassée. Alertez l'administrateur de la base")
        if len(errors) > 0:
            return False, errors

        if region=='':
            region= None

        if departement =='':
            departement= None

        if codeINSEE == '':
            codeINSEE = None

        if id_geonames == '':
            id_geonames = None

        if pays == '':
            errors.append("Renseignez le pays")
            
        # vérifier si le lieu existe: test sur l'id geonames si renseigné
        if id_geonames:
            lieux = Lieu.query.filter(db.or_(Lieu.id_geonames == id_geonames)).count()
            if lieux > 0:
                errors.append("Un où plusieurs lieux qui ont le même identifiant geonames existent déjà.")
        else:
            # vérifier si le lieu existe: test sur le nom du lieu
            lieux = Lieu.query.filter(db.or_(Lieu.nomLieuFr == nomLieuFr)).count()
            if lieux > 0:
                errors.append("Un où plusieurs lieux portant le même nom existent déjà.")
        # Si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        # S'il n'y a pas d'erreur, on crée un nouveau lieu dans la table Lieux
        #nomLieuFr, pays, region, departement, codeINSEE, id_geonames, lat, lng)
        created_lieu = Lieu(
            nomLieuFr=nomLieuFr,
            pays=pays,
            region=region,
            departement=departement,
            codeINSEE=codeINSEE,
            id_geonames=id_geonames,
            lat=lat,
            lng=lng)

        try:
            # création du nouveau lieu :
            db.session.add(created_lieu)
            db.session.commit()

            # Renvoie d'informations vers l'utilisateur :
            return True, created_lieu

        except Exception as error_creation:
            return False, [str(error_creation)]

    @staticmethod
    def modifier_lieu(id, nomLieuFr, pays, region, departement, codeINSEE, id_geonames, lat, lng):
        errors = []
        # on vérifier d'abord la saisie des données obligatoires
        if not nomLieuFr:
            errors.append("Le champ 'Nom du lieu' est obligatoire")
        # vérifier que le champ genre est bien coché

        if not lat and not lng:
            errors.append("Les champs latitude et longitude sont obligatoires")
        # si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        if region == '':
            region = None

        if departement == '':
            departement = None

        if codeINSEE == '':
            codeINSEE = None

        if id_geonames == '':
            id_geonames = None

        if pays == '':
            errors.append("Renseignez le pays")

        #Récupère le lieu dans la base et vérifie que l'utilisateur modifie au moins un champs
        lieu= Lieu.query.get(id)

        if lieu.id==id and lieu.nomLieuFr==nomLieuFr and lieu.pays == pays and lieu.region ==region and lieu.departement==departement\
                and lieu.codeINSEE ==codeINSEE and lieu.id_geonames ==id_geonames and lieu.lat==lat and lieu.lng ==lng:
            errors.append("Aucune modification n'a été réalisée")

        # Si on a au moins une erreur
        if len(errors) > 0:
            return False, errors
        else:
            #on fait une affectation d'attributs à l'objet lieu
            lieu.nomLieuFr=nomLieuFr
            lieu.pays=pays
            lieu.region=region
            lieu.departement=departement
            lieu.codeINSEE=codeINSEE
            lieu.id_geonames=id_geonames
            lieu.lat=lat
            lieu.lng=lng

        try:
            # ajout dans la base de données
            db.session.add(lieu)
            db.session.commit()

            # Renvoie d'informations vers l'utilisateur :
            return True, lieu

        except Exception as error_modification:
            return False, [str(error_modification)]

    def lieu_json(self):
        """
        Fonction qui transforme les informations sur un lieu en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        lieuJson = {
            "frenchName": self.nomLieuFr,
            "originalName":self.nomLieuOrig,
            "region": self.region,
            "departement": self.departement,
            "codeINSEE":self.codeINSEE,
            "idGeonames": self.id_geonames,
            "latitude":self.lat,
            "longitude": self.lng
        }
        return lieuJson

class Categorie (db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    labelCategorie = db.Column(db.String(64))
    id_Thesaurus = db.Column(db.String(64))

    # ---- DB.RELATIONSHIPS -----#
    souscategories = db.relationship ('Souscategorie', back_populates = "categories")
    liensRegistre = db.relationship("LienRegistresCategories", back_populates = "categories")

    def __repr__(self):
        return '<Catégorie professionnelle: {}>'.format(self.labelCategorie)

    def categorie_json(self):
        """
        Fonction qui transforme les informations sur une catégorie en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        categorieJson = {
            "categorieLabel": self.labelCategorie,
        }
        return categorieJson

class Souscategorie (db.Model):
    __tablename__ = "souscategories"
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    labelSouscategorie = db.Column(db.String(64))
    id_thesaurus_souscat = db.Column(db.String(64))

    # FK
    id_categorie = db.Column(db.Integer, db.ForeignKey("categories.id"),nullable=False)

    # ---- DB.RELATIONSHIPS -----#
    categories = db.relationship("Categorie", back_populates = "souscategories")
    liensRegistre = db.relationship("LienRegistresCategories", back_populates="souscategories")

    def __repr__(self):
        return '<Souscategorie {}>'.format(self.labelSouscategorie)

    def souscategorie_json(self):
        """
        Fonction qui transforme les informations sur uyne souscategorie en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        soucategorieJson = {
            "subcategorieLabel": self.labelSouscategorie,
        }
        return soucategorieJson

class DetailRegistre (db.Model):
    __tablename__ = 'detailsRegistre'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    indexOrigine = db.Column(db.Integer, unique=True)
    nomOrigine = db.Column(db.String(64))
    prenomOrigine = db.Column(db.String(64))
    agePersonne = db.Column(db.Integer)
    anneeNaissCalcule = db.Column(db.Integer)
    taillePersonne = db.Column(db.DECIMAL)
    professionOrigine = db.Column(db.Text)
    dureeSejour = db.Column(db.String(12))
    description = db.Column(db.Text)
    accompagnePar = db.Column(db.Text)
    caracteristiquesPhysiques = db.Column(db.Text)
    autresCaracteristiques = db.Column(db.Text)
    epoux = db.Column(db.SmallInteger, nullable=False, default=0)
    nbEnfants = db.Column(db.SmallInteger)
    nbAutreMembre = db.Column(db.SmallInteger)
    nbPersSupplement = db.Column(db.SmallInteger)
    pseudonyme = db.Column(db.String(64))
    nomArchive = db.Column(db.String(64))
    cote = db.Column(db.String(64))
    natureDoc = db.Column(db.String(64))
    nrOrdre = db.Column(db.String(10))
    photoArchive = db.Column(db.String(64))
    commentaires = db.Column(db.Text)
    collecte = db.Column(db.String(128))

    #FK
    id_personne = db.Column(db.Integer, db.ForeignKey("personnes.id"), nullable=False)

    #---- DB.RELATIONSHIP -----#
    personnes = db.relationship("Personne",back_populates="registresPers")
    lieuxDeclares = db.relationship("LieuDeclare", back_populates = "registres")
    liensCategories = db.relationship("LienRegistresCategories", back_populates = "registres")
    caracteristiques = db.relationship("CaracteristiquePhysique", back_populates = "registres")
    voyageAvecRegistre = db.relationship("VoyageAvec", back_populates="registres" )
    authorshipRegistres = db.relationship("AuthorshipRegistre", back_populates="registres")
    photos = db.relationship("Photo", back_populates="registres")


    def __repr__(self):
        return '<DetailRegistre {}>'.format(self.id)\


    @staticmethod
    def create_register(id_personne, nomOrigine, prenomOrigine, agePersonne,anneeNaissCalcule,
                        taillePersonne, professionOrigine, dureeSejour, description, accompagnePar, caracteristiquesPhysiques,
                        autresCaracteristiques, epoux, nbEnfants, nbAutreMembre, nbPersSupplement, pseudonyme,
                        nomArchive, cote, natureDoc, nrOrdre, collecte, commentaires,
                        lieuxDeclares, liensCategories,caracteristiques,voyageAvecRegistre,authorshipRegistres, photos):


        errors = []

        if nomOrigine == '':
            nomOrigine = None

        if prenomOrigine == '':
            prenomOrigine = None

        if agePersonne == '':
            agePersonne = None

        if taillePersonne == '':
            taillePersonne = None

        if professionOrigine =='':
            professionOrigine = None

        if dureeSejour =='':
            dureeSejour = None

        if description =='':
            description = None

        if accompagnePar =='':
            accompagnePar = None

        if caracteristiquesPhysiques == '':
            caracteristiquesPhysiques = None

        if autresCaracteristiques =='':
            autresCaracteristiques = None

        if nbEnfants == '' :
            nbEnfants = None

        if nbAutreMembre == '' :
            nbAutreMembre = None

        if nbPersSupplement == '':
            nbPersSupplement= None

        if pseudonyme == '':
            pseudonyme = None

        if natureDoc =='':
            natureDoc =None

        if nrOrdre == '' :
            nrOrdre= None

        if commentaires =='':
            commentaires =None

        if collecte == '':
            collecte = None


        # Si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        # S'il n'y a pas d'erreur, on crée un nouvel objet Details Registre
        objectRegister = DetailRegistre(
            id_personne=id_personne,
            nomOrigine=nomOrigine,
            prenomOrigine=prenomOrigine,
            agePersonne=agePersonne,
            anneeNaissCalcule=anneeNaissCalcule,
            taillePersonne=taillePersonne,
            professionOrigine=professionOrigine,
            dureeSejour=dureeSejour,
            description = description,
            accompagnePar=accompagnePar,
            caracteristiquesPhysiques=caracteristiquesPhysiques,
            autresCaracteristiques=autresCaracteristiques,
            epoux=epoux,
            nbEnfants = nbEnfants,
            nbAutreMembre =nbAutreMembre,
            nbPersSupplement = nbPersSupplement,
            pseudonyme=pseudonyme,
            natureDoc=natureDoc,
            commentaires=commentaires,
            nomArchive=nomArchive,
            cote=cote,
            nrOrdre=nrOrdre,
            collecte=collecte
        )
        # on modifie l'objet en rajoutant les attributs de type liste d'objets lieux
        for lieu in lieuxDeclares:
            objectRegister.lieuxDeclares.append(lieu)

        for metier in liensCategories:
            objectRegister.liensCategories.append(metier)

        for caracteristique in caracteristiques:
            objectRegister.caracteristiques.append(caracteristique)

        for personne in voyageAvecRegistre:
            objectRegister.voyageAvecRegistre.append(personne)

        for authorship in authorshipRegistres:
            objectRegister.authorshipRegistres.append(authorship)

        for photo in photos:
            objectRegister.photos.append(photo)

        try:
            # création de l'objet en base de données :
            db.session.add(objectRegister)
            db.session.commit()

            # Renvoie d'informations vers l'utilisateur :
            return True, objectRegister

        except Exception as error_creation:
            return False, [str(error_creation)]

    @staticmethod
    def modifier_registre(id, id_personne, indexOrigine, nomOrigine, prenomOrigine, agePersonne, anneeNaissCalcule,
                        taillePersonne, professionOrigine, dureeSejour, description, accompagnePar,
                        caracteristiquesPhysiques, autresCaracteristiques, epoux, nbEnfants,
                        nbAutreMembre, nbPersSupplement, pseudonyme,nomArchive, cote, natureDoc,
                        nrOrdre, collecte, photos, commentaires,lieuxDeclares,voyageAvecRegistre,caracteristiques,liensCategories, authorshipRegistres):
        errors =[]
        if indexOrigine=='':
            indexOrigine =None

        if nomOrigine == '':
            nomOrigine = None

        if prenomOrigine == '':
            prenomOrigine = None

        if agePersonne == '':
            agePersonne = None

        if taillePersonne == '':
            taillePersonne = None

        if professionOrigine =='':
            professionOrigine = None

        if dureeSejour =='':
            dureeSejour = None

        if description =='':
            description = None

        if accompagnePar =='':
            accompagnePar = None

        if caracteristiquesPhysiques == '':
            caracteristiquesPhysiques = None

        if autresCaracteristiques =='':
            autresCaracteristiques = None

        if nbEnfants == '' :
            nbEnfants = None
        else:
            nbEnfants =int(nbEnfants)

        if nbAutreMembre == '' :
            nbAutreMembre = None
        else:
            nbAutreMembre=int(nbAutreMembre)

        if nbPersSupplement == '':
            nbPersSupplement= None
        else:
            nbPersSupplement=int(nbPersSupplement)

        if pseudonyme == '':
            pseudonyme = None

        if natureDoc =='':
            natureDoc =None

        if nrOrdre == '' :
            nrOrdre= None

        if commentaires =='':
            commentaires =None

        if collecte == '':
            collecte=None

        if epoux:
            epoux=int(epoux)
        else:
            epoux=0

        if id_personne =='':
            errors.append("L'identifiant de la personne est obligatoire")
        else:
            id_personne=int(id_personne)

        # Si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        registre=DetailRegistre.query.get(id)

        # Si on a au moins une erreur
        if len(errors) > 0:
            return False, errors

        else:
            # on fait une affectation d'attributs à l'objet lieu
            registre.indexOrigine = indexOrigine
            registre.nomOrigine = nomOrigine
            registre.prenomOrigine = prenomOrigine
            registre.agePersonne=agePersonne
            registre.anneeNaissCalcule=anneeNaissCalcule
            registre.taillePersonne=taillePersonne
            registre.professionOrigine = professionOrigine
            registre.dureeSejour = dureeSejour
            registre.description = description
            registre.accompagnePar = accompagnePar
            registre.caracteristiquesPhysiques = caracteristiquesPhysiques
            registre.autresCaracteristiques=autresCaracteristiques
            registre.epoux=epoux
            registre.nbEnfants=nbEnfants
            registre.nbAutreMembre=nbAutreMembre
            registre.nbPersSupplement=nbPersSupplement
            registre.pseudonyme=pseudonyme
            registre.nomArchive=nomArchive
            registre.cote=cote
            registre.natureDoc=natureDoc
            registre.nrOrdre=nrOrdre
            registre.commentaires=commentaires
            registre.id_personne=id_personne
            registre.collecte = collecte


            # supprime les lieux
            for lieu in registre.lieuxDeclares:
                db.session.delete(lieu)

            # recrée les lieux
            for newLieu in lieuxDeclares:
                registre.lieuxDeclares.append(newLieu)

            # suprimme les personnes qui voyage avec
            for personne in registre.voyageAvecRegistre:
                db.session.delete(personne)

            #recrée la liste d'oobjet voyageAvec
            for pers in voyageAvecRegistre:
                registre.voyageAvecRegistre.append(pers) #on rajoute un objet VoyageAvec à la liste d'objet

            #suppression de la liste d'objet caracteristiques
            for caracteristique in registre.caracteristiques:
                db.session.delete(caracteristique)

            # recrée la liste d'oobjet caracteristiques avec les nouvelles valeurs et les anciennent
            for element in caracteristiques:
                registre.caracteristiques.append(element)  # on rajoute un objet à la liste d'objet

            # suprimme les categories
            for categorie in registre.liensCategories:
                db.session.delete(categorie)

            # recrée la liste d'objets Categorie
            for newCat in liensCategories:
                registre.liensCategories.append(newCat)

            # supprime les objets photos
            for photo in registre.photos:
                db.session.delete(photo)

            # recrée la liste d'objets photos depuis le formulaire
            for newphoto in photos:
                registre.photos.append(newphoto)

            # ajoute au authorshipRegistres la nouvelle modification avec role=contributeur sans supprimer les anciens authorship
            for authorship in authorshipRegistres:
                registre.authorshipRegistres.append(authorship)

        try:
            # db.session.add() génère des erreurs. Ne pas l'utiliser. ajout dans la base de données de l'objet registre modifier avec les nouveux attributs
            db.session.commit()

            # Renvoie d'informations vers l'utilisateur :
            return True, registre


        except Exception as error_modification:
            return False, [str(error_modification)]


    @staticmethod
    def supprimer_registre(id_registre):
        """
        Fonction qui supprime un registre d'une personne
        :param id_personne: l'identifiant du registre à récupérer dans l'adresse de la notice
        :type id_registre: int
        :returns : Booleens
        """
        # récupération de l'objet registre
        registre = DetailRegistre.query.get(id_registre)

        db.session.delete(registre)
        db.session.commit()

    def register_json(self):
        """
        Fonction qui transforme les informations sur un registre en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        registreJson = {
            "registerId": self.id,
            "declaredSecondName": self.nomOrigine,
            "declaredFirstName": self.prenomOrigine,
            "age": self.agePersonne,
            "calculatedYearOfBirth": self.anneeNaissCalcule,
            "size": str(self.taillePersonne),
            "declaredProfession": self.professionOrigine,
            "durationOfStay": self.dureeSejour,
            "description": self.description,
            "declareToBeAccompaniedBy":self.accompagnePar,
            "reportedPhysicalCharacteristics": self.caracteristiquesPhysiques,
            "otherCharacteristics": self.autresCaracteristiques,
            "maried": self.epoux,
            "numberOfChildren" : self.nbEnfants,
            "numberOfOtherFamillyMembers" : self.nbAutreMembre,
            "numberOfOtherPeople":self.nbPersSupplement,
            "nickname" : self.pseudonyme,
            "archivalCenter": self.nomArchive,
            "archivalRecord" : self.cote,
            "typeDfDocument" : self.natureDoc,
            "orderNumber" : self.nrOrdre,
            "comments" : self.commentaires,
            "collectingDocuments" : self.collecte,
            "declaredPlaces" :  [lieuDeclare.lieuDeclarer_json() for lieuDeclare in self.lieuxDeclares],
            "physicalCharacteristics" : [caracteristiques.caracteristiquesPhys_json() for caracteristiques in self.caracteristiques],
            "photos" : [photo.photo_json() for photo in self.photos],
            "travelWith" : [compagnon.voyageAvec_json() for compagnon in self.voyageAvecRegistre],
            "categoriesAndSubcategoriesOfProfessions" : [liencatsoucat.lienRegistreCat_json() for liencatsoucat in self.liensCategories],
            "authorsOfRegisterRecord" : [author.authorRegister_json() for author in self.authorshipRegistres]

        }
        return registreJson

class LieuDeclare (db.Model):
    # classe correspondant à la table de lien entre le detail registre et la table lieux
    __tablename__ = 'lieuxDeclares'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    labelLieuDeclare = db.Column(db.String(64))
    date = db.Column(db.Date)
    typeLieu = db.Column(db.String(64))
    # FK
    id_registre = db.Column(db.Integer, db.ForeignKey("detailsRegistre.id"), nullable=False)
    id_lieu = db.Column(db.Integer, db.ForeignKey("lieux.id"))

    # ---- DB.RELATIONSHIPS -----#
    registres = db.relationship("DetailRegistre", back_populates = "lieuxDeclares")
    lieux = db.relationship("Lieu", back_populates = "lieuxDeclares")


    def __repr__(self):
        return '<LieuDeclare {}>'.format(self.id)

    @staticmethod
    def delete_lieuDeclare(id_lieuDeclare):
        lieuDeclare = LieuDeclare.query.get(id_lieuDeclare)
        db.session.delete(lieuDeclare)
        db.session.commit()


    def lieuDeclarer_json(self):
        """
        Fonction qui transforme les informations sur un lieu déclaré en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        if self.lieux:
            lieuNormalise = self.lieux.lieu_json()
        else:
            lieuNormalise = "non renseigné"

        lieuDeclarerJson = {
            "declaredPlace": self.labelLieuDeclare,
            "date": str(self.date),
            "typeOfPlace": self.typeLieu,
            "normalisedPlace": lieuNormalise
        }
        return lieuDeclarerJson

class LienRegistresCategories (db.Model):
    # classe correspondant à la table de lien entre le detail registre et les tables categories et sous-categories
    __tablename__ = 'lienRegistresCategories'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    #FK
    id_registre = db.Column(db.Integer, db.ForeignKey("detailsRegistre.id"), nullable=False)
    id_categorie = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    id_souscategorie = db.Column(db.Integer, db.ForeignKey("souscategories.id"))

    # ---- DB.RELATIONSHIP -----#
    registres = db.relationship("DetailRegistre", back_populates = "liensCategories")
    categories = db.relationship("Categorie", back_populates = "liensRegistre")
    souscategories = db.relationship("Souscategorie", back_populates = "liensRegistre")

    def __repr__(self):
        return '<LienRegistresCategories {}>'.format(self.id)

    @staticmethod
    def delete_lienRegistreCategorie(id_lienRegistreCat):
        lienCategorie = LienRegistresCategories.query.get(id_lienRegistreCat)
        db.session.delete(lienCategorie)
        db.session.commit()

    def lienRegistreCat_json(self):
        """
        Fonction qui transforme les informations sur lienregistrecategorie en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        if self.categories and self.souscategories:
            lienRegistreCatJson = {"categorie":self.categories.categorie_json(),
                                   "subcategorie": self.souscategories.souscategorie_json()
                                   }
        elif self.categories:
            lienRegistreCatJson =  {"categorie":self.categories.categorie_json()}

        else:
            lienRegistreCatJson = "non renseigné"

        return lienRegistreCatJson

class CaracteristiquePhysique (db.Model):
    # classe correspondant à la table des carracteristiques physiques
    __tablename__ = 'caracteristiquesPhysiques'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    # FK
    id_registre = db.Column(db.Integer, db.ForeignKey("detailsRegistre.id"), nullable=False)
    labelCaracteristique = db.Column(db.String(30))

    # ---- DB.RELATIONSHIPS -----#
    registres = db.relationship("DetailRegistre", back_populates="caracteristiques")

    def __repr__(self):
        return '<CaracteristiquePhysique {}>'.format(self.labelCaracteristique)

    @staticmethod
    def delete_caractersitiques(id_caracteristique):
        caracteristique = CaracteristiquePhysique.query.get(id_caracteristique)
        db.session.delete(caracteristique)
        db.session.commit()

    def caracteristiquesPhys_json(self):
        """
        Fonction qui transforme les informations sur caractéristique physique en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        caracteristiquesPhysJson = {
            "physicalCharacteristics": self.labelCaracteristique
        }
        return caracteristiquesPhysJson

class VoyageAvec (db.Model):
    #classe correspondant à la table voyageAvec
    __tablename__ = 'voyageAvec'
    id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)
    # FK
    id_registre = db.Column(db.Integer, db.ForeignKey("detailsRegistre.id"), nullable=False)
    id_personne = db.Column(db.Integer, db.ForeignKey("personnes.id"), nullable=False)

    # ---- DB.RELATIONSHIP -----#
    registres = db.relationship("DetailRegistre", back_populates="voyageAvecRegistre")
    personnes = db.relationship("Personne", back_populates="voyageAvecPers")

    def __repr__(self):
        return '<Voyage avec {}>'.format(self.id)

    @staticmethod
    def delete_voyageAvec(id_voyageAvec):
        voyageAvec = VoyageAvec.query.get(id_voyageAvec)
        db.session.delete(voyageAvec)
        db.session.commit()

    def voyageAvec_json(self):
        """
        Fonction qui transforme les informations sur voyage avec en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        if self.personnes and self.registres:
            personneAccompagnante = self.personnes.personne_json()
        else:
            personneAccompagnante = "non renseigné"

        return personneAccompagnante

class Photo (db.Model):
     #classe correspondant à la table photos
     __tablename__ = 'photos'
     id = db.Column(db.Integer, unique=True, nullable=False, primary_key=True, autoincrement=True)

     # FK
     id_registre = db.Column(db.Integer, db.ForeignKey("detailsRegistre.id"), nullable=False)
     label_photo = db.Column(db.String(64))

     # ---- DB.RELATIONSHIP -----#
     registres = db.relationship("DetailRegistre", back_populates="photos")

     def __repr__(self):
         return '<Photo {}>'.format(self.id)

     @staticmethod
     def delete_photos(id_photo):
         photo = Photo.query.get(id_photo)
         db.session.delete(photo)
         db.session.commit()

     def photo_json(self):
        """
        Fonction qui transforme les informations sur une photo en un dictionnaire pour un export en json via l'API
        :return: dict
        """
        photoJson = {
            "photoLabel": self.label_photo
        }
        return photoJson

