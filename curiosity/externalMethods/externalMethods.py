from datetime import datetime
from flask import jsonify
from curiosity.modeles.personnes_registres import Lieu, LieuDeclare, LienRegistresCategories
import csv
from curiosity import db
from io import StringIO

def validate(date_text):
    """
    fonction qui valide le format des dates saisies par l'utilisateur
    :param date_text: la date en format texte
    :return: Boolean
    """
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def json_response(statusCode, codeRetour, message, nomLieuComplet):
    """
    Fonction qui permet de construire une réponse http deu serveur
    :param statusCode: integer. l'un des codes de retour http: 201, 202 ou 404
    :param codeRetour: str. l'un des messages: OK, KO
    :param message: str. message détaillé de réponse
    :param nomLieuComplet: str: concaténation entre le nom du lieu, le pays, le départ et l'id du lieu nouvellement créé
    :return: json: la réponse avec les 4 éléments
    """
    # la méthode jsonify retourne un objet de type Response
    response = jsonify({"codeRetour":codeRetour,
                        "message":message,
                        "nouveauLieuComplet": nomLieuComplet})
    response.status_code = statusCode
    return response

def extractLieuxComplet():
    """
    methode qui construit une liste de lieux complets pour tous les lieux
     Chaque lieu complet regroupe le nom, le départ, le pays et l'id en un seul str
    :return: list
    """
    lieux = Lieu.query.all()
    listeNomLieu = []
    for lieu in lieux:
        nomLieuComplet = ""
        if lieu.nomLieuFr:
            nomLieuComplet = nomLieuComplet + lieu.nomLieuFr
        if lieu.departement:
            nomLieuComplet = nomLieuComplet + ", " + lieu.departement
        if lieu.pays:
            nomLieuComplet = nomLieuComplet + ", " + lieu.pays
        if lieu.id:
            nomLieuComplet = nomLieuComplet + ", " + str(lieu.id)
        listeNomLieu.append(nomLieuComplet)
    return listeNomLieu
def extractLieuxEnregistrementComplet():
    """
    methode qui construit une liste de lieux complets pour les lieux d'enregistrement
     Chaque lieu complet regroupe le nom, le départ, le pays et l'id en un seul str
    :return: list
    """

    lieuxEnregistrement = db.session.query(Lieu). \
        join(LieuDeclare, Lieu.id == LieuDeclare.id_lieu).\
        filter(LieuDeclare.typeLieu == "Enregistrement")

    listeNomLieuEnregistrement = []
    for lieu in lieuxEnregistrement:
        nomLieuComplet = ""
        if lieu.nomLieuFr:
            nomLieuComplet = nomLieuComplet + lieu.nomLieuFr
        if lieu.departement:
            nomLieuComplet = nomLieuComplet + ", " + lieu.departement
        if lieu.pays:
            nomLieuComplet = nomLieuComplet + ", " + lieu.pays
        if lieu.id:
            nomLieuComplet = nomLieuComplet + ", " + str(lieu.id)
        listeNomLieuEnregistrement.append(nomLieuComplet)
    return listeNomLieuEnregistrement

def sortByDestination(lieu):
    """
    fonction qui permet de donner un ordre aux type de lieux de la base selon un critère choisi
    :param lieu: objet lieuDeclare
    :return: int
    """
    if lieu.typeLieu == "Naissance":
        return 0
    elif lieu.typeLieu == "Domicile":
        return 1
    elif lieu.typeLieu == "Délivrance du passeport":
        return 2
    elif lieu.typeLieu == "Dernier Passage":
        return 3
    elif lieu.typeLieu == "Visa":
        return 4
    elif lieu.typeLieu == "Destination":
        return 5
    elif lieu.typeLieu == "Décès":
        return 6
    else:
        return 7

def sortByPhysique(carPhysique):
    """
    fonction qui permet de donner un ordre aux caractéristiques physiques de la base selon un critère choisi
    :param carPhysique: liste de tuple (labelcaracteristique, ')
    :return: int
    """
    if carPhysique[0] == "autres caractéristiques":
        return 9
    if carPhysique[0] == "amputé mains, doigts, pieds":
        return 0
    if carPhysique[0] == "aveugle":
        return 1
    if carPhysique[0] == "borgne":
        return 2
    if carPhysique[0] == "cicatrice":
        return 3
    if carPhysique[0] == "cul-de-jatte":
        return 4
    if carPhysique[0] == "manchot ":
        return 5
    if carPhysique[0] == "unijambiste ":
        return 6
    if carPhysique[0] == "vérole ":
        return 7
    else:
        return 8

def sortByDateEnregistrement(registre):
    """
    fonction qui retourne la date d'enregistrement pour chaque registre
    :param registre: objet detailRegistre
    :return: date
    """
    for lieu in registre.lieuxDeclares:
        if lieu.typeLieu == "Enregistrement":
            return lieu.date

def sortByMetiers(tuple):
    """
    fonction qui permet de donner un ordre catégories de métiers de la base selon un critère choisi
    :param metier: str correspondant au labelCategorie
    :return: int
    """
    if tuple[2] == "autres metiers":
        return 18
    elif tuple[2] == "indéterminé":
        return 17
    elif tuple[2] == "domestique":
        return 16
    else:
        return 1

def filterLieuxDeclareAvecUneNaissance(listeDetailsRegistres):
    findNaissance = False
    listeLieu = []
    for registre in listeDetailsRegistres:
        for lieux in registre.lieuxDeclares:
            if lieux.typeLieu == "Naissance":
                if findNaissance == False:
                    findNaissance = True
                    listeLieu.append(lieux)
            else:
                listeLieu.append(lieux)
    return listeLieu

def genrateObjetLieuxDeclare(labelLieuNormaliseHtml, listeDate, listeLabelLieuDeclare, listeObjet_lieuDeclare,listeTypeLieu):
    # définit la taille de listeLabelLieuDeclare qui est la même que celle des autres listes
    tailleListelieuDeclare = len(listeLabelLieuDeclare)

    #pour chaque lieu déclaré
    for i in range(0, tailleListelieuDeclare):
        # création d'un objet LieuDeclare pour chaque lieu déclaré
        objetLieuxDeclares = LieuDeclare(
            labelLieuDeclare=listeLabelLieuDeclare[i],
            # récupère le dernier élément de la la liste qui est l'id du lieu et ajoute None pour les lieux non saisis
            id_lieu=labelLieuNormaliseHtml[i].split(",")[-1] if (labelLieuNormaliseHtml[i] != "") else None,
            # ajoute None pour les dates non saisies
            date=listeDate[i] if listeDate[i] != "" else None,
            typeLieu=listeTypeLieu[i])
        # on ajoute l'objet à la liste d'objets déclarés
        listeObjet_lieuDeclare.append(objetLieuxDeclares)

def generateObjectCategorie(listeCategories, listeObjetsMetiers, listeSoucategories):
    # on définit la taille de la liste listeCategories qui est la même que celle des souscategories
    tailleListeCategorie = len(listeCategories)

    # pour chaque index de la liste on crée un objet de type LienRegistresCategories
    for i in range(0, tailleListeCategorie):
        if listeCategories[i] != '':
            idSousCat = listeSoucategories[i]
            #instanciation d'un objet LienRegistresCategories qui contient les deux attributs
            objetLienRegistreCategorie = LienRegistresCategories(
                id_categorie=listeCategories[i],
                id_souscategorie=idSousCat
            )
            #on ajoute l'objet à une liste qui contiendra tous les objets lienscatégories
            listeObjetsMetiers.append(objetLienRegistreCategorie)

def generateCompleteCSV(resultResearch):
    """
    fonction qui génère un fichier csv à la volée sans le stocker en mémoire. Il contient tous les lieux, les metiers et les regitres des personnes séléctionnées
    :param resultResearch: liste de tuple contenant le nombre de registre et l'objet personnes [(1, <Personne Abadi>),(2, <Personne Abadie>), (1, <Personne Abadie>), (2, <Personne Allouer>),(1, <Personne Ambroise>), (7, <Personne Ambrosini>),
    :return: generator yield
    """
    data = StringIO()
    w = csv.writer(data)

    # write header
    w.writerow(('id_registre', 'coteArchive', 'collecte', 'numeroOrdre', 'nomDeclare', 'prenomDeclare',
                'age', 'taille',
                'metierDeclare', 'categorie-soucategoriesNormaliser', 'caracteristiquesPhysiques',
                'dureeSejour', 'typeLieu', 'chronologieDeplacement', 'date',
                'labelLieuDeclare', 'lieuNormaliser', 'id_geonames', 'latitude', 'longitude', 'pays',
                'departement', 'idPersonneUnique',
                'sexe', 'nomOfficiel', 'prenomOfficiel', 'anneeNaissanceNormalisee', 'lieuNaissanceReconcilie', "lat_naiss", "lng_naiss"))

    yield data.getvalue()
    data.seek(0)
    data.truncate(0)

    # pour chaque tuple (nb registre, personne) de la liste de resultats
    for pers in resultResearch:
        # si la personne a des registres
        if pers[1].registresPers:
            # pour chaque registre de la personne
            for registre in pers[1].registresPers:
                listeCategorieSoucategorie = ""

                for liencatsoucat in registre.liensCategories:

                    if liencatsoucat.categories and liencatsoucat.souscategories:
                        catsoucatensemble = liencatsoucat.categories.labelCategorie + " - " + liencatsoucat.souscategories.labelSouscategorie + "; "
                        listeCategorieSoucategorie += catsoucatensemble
                    elif liencatsoucat.categories:
                        catsoucatvide = liencatsoucat.categories.labelCategorie + " - ; "
                        listeCategorieSoucategorie+=catsoucatvide

                registre.lieuxDeclares = sorted(registre.lieuxDeclares, key=sortByDestinationOrder)
                for i, lieuDeclare in enumerate(registre.lieuxDeclares):
                    rowLieux = []
                    rowLieux.append(registre.id)
                    rowLieux.append(registre.cote)
                    rowLieux.append(registre.collecte)
                    rowLieux.append(registre.nrOrdre)
                    rowLieux.append(registre.nomOrigine)
                    rowLieux.append(registre.prenomOrigine)
                    rowLieux.append(registre.agePersonne)
                    rowLieux.append(registre.taillePersonne)
                    rowLieux.append(registre.professionOrigine)
                    rowLieux.append(listeCategorieSoucategorie)
                    rowLieux.append(registre.caracteristiquesPhysiques)
                    rowLieux.append(registre.dureeSejour)
                    rowLieux.append(lieuDeclare.typeLieu)
                    # ajoute un ordre dans la succession des villes
                    rowLieux.append(i + 1)
                    # ajoute la date
                    rowLieux.append(lieuDeclare.date)
                    rowLieux.append(lieuDeclare.labelLieuDeclare)

                    # si le lieu est normalisé, récupère les informations enrichies sur les lieux
                    if lieuDeclare.id_lieu:
                        rowLieux.append(lieuDeclare.lieux.nomLieuFr)
                        rowLieux.append(lieuDeclare.lieux.id_geonames)
                        rowLieux.append(lieuDeclare.lieux.lat)
                        rowLieux.append(lieuDeclare.lieux.lng)
                        rowLieux.append(lieuDeclare.lieux.pays)
                        rowLieux.append(lieuDeclare.lieux.departement)
                    # autrement il faut laisser les colonnes vides
                    else:
                        rowLieux.append("")
                        rowLieux.append("")
                        rowLieux.append("")
                        rowLieux.append("")
                        rowLieux.append("")
                        rowLieux.append("")
                    # ajoute les éléments descriptifs de la personne
                    rowLieux.append(registre.id_personne)
                    rowLieux.append(pers[1].sexe)
                    rowLieux.append(pers[1].nom)
                    rowLieux.append(pers[1].prenom)
                    rowLieux.append(pers[1].anneeNaissance)
                    #si la personne a un lieu de naissance normalisé
                    if pers[1].lieux_naissance:
                        rowLieux.append(pers[1].lieux_naissance.nomLieuFr)
                        rowLieux.append(pers[1].lieux_naissance.lat)
                        rowLieux.append(pers[1].lieux_naissance.lng)

                    else:
                        rowLieux.append("")


                    # ajoute la ligne à la liste globale qui génère le fichier
                    w.writerow(rowLieux)
                    yield data.getvalue()
                    data.seek(0)
                    data.truncate(0)


def generateReducedCsv(resultResearch, cote):
    """
    fonction qui génère un fichier csv à la volée sans le stocker en mémoire. Il contient une selection de propriétés des regitres
    :param resultResearch: liste de tuple contenant le nombre de registre et l'objet personnes [(1, <Personne Abadi>),(2, <Personne Abadie>), (1, <Personne Abadie>), (2, <Personne Allouer>),(1, <Personne Ambroise>), (7, <Personne Ambrosini>),
    :param cote: str. le label de la cote choisie en filtre
    :return: generator yield
    """
    data = StringIO()
    w = csv.writer(data)

    # write header
    w.writerow(
        ('coteArchive', 'numeroOrdre', 'nomDeclare', 'prenomDeclare', 'id_personne', 'metierDeclare',
         'lieuEnregistrement', 'dateEnregistrement',
         'lieuNaissanceDeclare', 'paysLieuNaissance', 'departementLieuNaissance'))
    yield data.getvalue()
    data.seek(0)
    data.truncate(0)
    # pour chaque tuple (nb registre, personne)
    for pers in resultResearch:
        # si la personne a des registres
        if pers[1].registresPers:
            # pour chaque registre de la personne
            for registre in pers[1].registresPers:
                bool = False
                # on déclare une liste par registre
                registerRow = []

                # si le filtre cote est choisi
                if cote:

                    # si cote choisie correpond à la cote dans la base, on filtre pour ne récupérer que les registres
                    if registre.cote == cote:

                        # ajoute à la liste les élements du détails régistre
                        registerRow.append(registre.cote)
                        registerRow.append(registre.nrOrdre)
                        registerRow.append(registre.nomOrigine)
                        registerRow.append(registre.prenomOrigine)
                        registerRow.append(registre.id_personne)
                        registerRow.append(registre.professionOrigine)

                        # pour chaque lieu déclaré
                        for lieuDeclare in registre.lieuxDeclares:
                            # si le type lieu est Enregistrement, on ajoute le lieu et la date à la liste du registre
                            if lieuDeclare.typeLieu == "Enregistrement":
                                registerRow.append(lieuDeclare.lieux.nomLieuFr)
                                registerRow.append(lieuDeclare.date)

                            # si le type naissance existe
                            elif lieuDeclare.typeLieu == "Naissance":
                                # si le lieu déclaré a aussi un lieu normalisé ajoute à la liste les élements des lieux normalisés
                                if lieuDeclare.id_lieu:
                                    registerRow.append(lieuDeclare.lieux.nomLieuFr)
                                    registerRow.append(lieuDeclare.lieux.pays)
                                    registerRow.append(lieuDeclare.lieux.departement)
                                # sinon, ajoute uniquement le lieu déclaré, sans pays, ni département
                                elif lieuDeclare.labelLieuDeclare:
                                    registerRow.append(lieuDeclare.labelLieuDeclare)
                                    registerRow.append("")
                                    registerRow.append("")
                                # si le lieu naissance existe, le bool passe à True
                                bool = True
                        # Si le lieu de naissance n'existe pas, le bool reste à false, et les colonnes seront vides
                        if bool == False:
                            registerRow.append("")
                            registerRow.append("")
                            registerRow.append("")

                        # ajoute la ligne à la liste globale qui génère le fichier
                        w.writerow(registerRow)
                        yield data.getvalue()
                        data.seek(0)
                        data.truncate(0)
                # si le filtre cote n'est pas choisi
                else:
                    # ajoute à la liste les élements du détails régistre
                    registerRow.append(registre.cote)
                    registerRow.append(registre.nrOrdre)
                    registerRow.append(registre.nomOrigine)
                    registerRow.append(registre.prenomOrigine)
                    registerRow.append(registre.id_personne)
                    registerRow.append(registre.professionOrigine)

                    # pour chaque lieu déclaré
                    for lieuDeclare in registre.lieuxDeclares:
                        # si le type lieu est Enregistrement, on ajoute le lieu et la date à la liste du registre
                        if lieuDeclare.typeLieu == "Enregistrement":
                            registerRow.append(lieuDeclare.lieux.nomLieuFr)
                            registerRow.append(lieuDeclare.date)

                        # si le type naissance existe
                        elif lieuDeclare.typeLieu == "Naissance":
                            # si le lieu déclaré a aussi un lieu normalisé ajoute à la liste les élements des lieux normalisés
                            if lieuDeclare.id_lieu:
                                registerRow.append(lieuDeclare.lieux.nomLieuFr)
                                registerRow.append(lieuDeclare.lieux.pays)
                                registerRow.append(lieuDeclare.lieux.departement)
                            # sinon, ajoute uniquement le lieu déclaré, sans pays, ni département
                            elif lieuDeclare.labelLieuDeclare:
                                registerRow.append(lieuDeclare.labelLieuDeclare)
                                registerRow.append("")
                                registerRow.append("")
                            # si le lieu naissance existe, le bool passe à True
                            bool = True
                    # Si le lieu de naissance n'existe pas, le bool reste à false, et les colonnes seront vides
                    if bool == False:
                        registerRow.append("")
                        registerRow.append("")
                        registerRow.append("")

                    # ajoute la ligne à la liste globale qui génère le fichier
                    w.writerow(registerRow)
                    yield data.getvalue()
                    data.seek(0)
                    data.truncate(0)


def sortByDestinationOrder(lieu):
    """
    fonction qui permet de donner un ordre aux type de lieux de la base selon l'ordre logique de déplacement
    :param lieu: objet lieuDeclare
    :return: int
    """

    if lieu.typeLieu == "Naissance":
        return 0
    elif lieu.typeLieu == "Domicile":
        return 1
    elif lieu.typeLieu == "Délivrance du passeport":
        return 2
    elif lieu.typeLieu == "Visa":
        return 3
    elif lieu.typeLieu == "Dernier Passage":
        return 4
    elif lieu.typeLieu == "Enregistrement":
        return 5
    elif lieu.typeLieu == "Destination":
        return 5
    elif lieu.typeLieu == "Décès":
        return 6
    else:
        return 7