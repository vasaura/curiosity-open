from flask import render_template, flash, redirect, url_for, request, session, jsonify
from curiosity import appli, db
from curiosity.forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user, logout_user, login_required
from curiosity.modeles.users import User
from curiosity.modeles.personnes_registres import Personne, Lieu, Categorie, Souscategorie, DetailRegistre, LieuDeclare, LienRegistresCategories, CaracteristiquePhysique, VoyageAvec
from werkzeug.urls import url_parse
from sqlalchemy import func

PERSONNES_PAR_PAGES = 20
METIER_PAR_PAGE = 20
LIEUX_PAR_PAGES = 20


def json_response(statusCode, codeRetour, message, nomLieuComplet):
    response = jsonify({"codeRetour":codeRetour,
                        "message":message,
                        "nouveauLieuComplet": nomLieuComplet})
    response.status_code = statusCode
    return response

def extractLieuxComplet():
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
    elif lieu.typeLieu == "Destination":
        return 4
    else:
        return 5

def sortByMetiers(tuple):
    """
    fonction qui permet de donner un ordre catégories de métiers de la base selon un critère choisi
    :param metier: str correspondant au labelCategorie
    :return: int
    """
    if tuple[1].labelCategorie == "autres metiers":
        return 18
    elif tuple[1].labelCategorie == "indéterminé":
        return 17
    elif tuple[1].labelCategorie == "domestique":
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
    # création d'un objet LieuDeclare pour chaque lieu déclaré
    for i in range(0, tailleListelieuDeclare):
        objetLieuxDeclares = LieuDeclare(
            labelLieuDeclare=listeLabelLieuDeclare[i],
            # récupère le dernier élément de la la liste qui est l'id du lieu et ajoute None pour les lieux non saisis
            id_lieu=labelLieuNormaliseHtml[i].split(",")[-1] if (labelLieuNormaliseHtml[i] != "") else None,
            # ajoute None pour les dates non saisies
            date=listeDate[i] if listeDate[i] != "" else None,
            typeLieu=listeTypeLieu[i])
        # on ajoute l'objet à la liste d'objets déclarés
        listeObjet_lieuDeclare.append(objetLieuxDeclares)

def generatObjeteVoyageAvec(listeObjetsVoyageAvec, listePersonnesAccompagnantes):
    tailleListePersonnesAccompagnantes = len(listePersonnesAccompagnantes)
    for i in range(0, tailleListePersonnesAccompagnantes):
        objectVoyageAvec = VoyageAvec(
            id_personne=listePersonnesAccompagnantes[i]
        )
        listeObjetsVoyageAvec.append(objectVoyageAvec)

def generateObjectCategorie(listeCategories, listeObjetsMetiers, listeSoucategories):
    # on définit la taille de la liste listeCategories qui est la même que celle des souscategories
    tailleListeCategorie = len(listeCategories)

    # pour chaque index de la liste on crée un objet LienRegistresCategories
    for i in range(0, tailleListeCategorie):
        if listeCategories[i] != 'aucune':
            idSousCat = None
            if listeSoucategories:
                idSousCat = listeSoucategories[i]

            objetLienRegistreCategorie = LienRegistresCategories(
                id_categorie=listeCategories[i],
                id_souscategorie=idSousCat
            )
            listeObjetsMetiers.append(objetLienRegistreCategorie)


#############################################################################
#                             PAGES PRESENTATION                            #
#############################################################################

@appli.route('/')
def intro():
    personnes = Personne.query.order_by(Personne.id.desc()).limit(4).all()

    return render_template('intro.html', title='Accueil', personnes=personnes)

@appli.route('/projet')
def projet():

    return render_template('projet.html', title='Présentation du projet')

@appli.route('/credits')
def credits():

    return render_template('credits.html', title='Crédits')

@appli.route('/index', methods=["GET", "POST"])
def index():
    titre = "Index"

    # recupération de la liste des catégories professionnemmes pour les passer dans l'input HTML dans les filtres
    categories = Categorie.query.all()
    caracteristiquesPysiques= db.session.query(CaracteristiquePhysique.labelCaracteristique).distinct()

    filtreTemporaire = {}

    if request.method == "GET":
        personnes = db.session.query(Personne.id, Personne.nom, Personne.prenom, Personne.anneeNaissance).all()
        # retourne la page html en lui passant comme paramètre titre et personnes
        return render_template('index.html', title = titre,
                               personnes= personnes,
                               categories=categories,
                               caracteristiquesPysiques=caracteristiquesPysiques,
                               filtreTemporaire=filtreTemporaire)

    elif request.method == "POST":

        # REQUETE DE BASE les Personnes uniques
        resultResearch = db.session.query(Personne.id, Personne.nom, Personne.prenom, Personne.anneeNaissance).distinct()

        # récupérer les infos sur le sexe ex [Femme, Homme]
        filterSexe = request.form.getlist("sexe", None)
        # récupérer les infos sur la catégorie
        filtreCategorie = request.form.getlist("categorie", None)
        # récupérer les infos sur la souscatégorie
        filtreSousCategorie = request.form.getlist("souscategorie", None)
        #récupère les caractéristiques physiques
        pysique=request.form.getlist("physique", None)

        epoux = request.form.get("epoux", None)

        enfants = request.form.get("enfants", None)

        membreFamille = request.form.get("membreFamille", None)
        autrePersonne = request.form.get("autrePersonne", None)

        if filterSexe:
            filtreTemporaire["Sexe"] = filterSexe
            # on rajoute à la reqête le filtre pour le sexe avec une requête in_()
            resultResearch=resultResearch.filter(Personne.sexe.in_(filterSexe))

        # si l'un des deux filtres catagories ou sous-catégorie a été coché
        if filtreCategorie or filtreSousCategorie or pysique or epoux or enfants or membreFamille or autrePersonne:
            # on rajoute à la requete de base les jointures pour DetailsRegistre
            resultResearch = resultResearch.join(DetailRegistre, DetailRegistre.id_personne == Personne.id)

            if epoux == "oui":
                filtreTemporaire["Accompagnés par epoux.se"] = epoux
                resultResearch=resultResearch.filter(DetailRegistre.epoux == 1)
            if epoux == "non":
                filtreTemporaire["Accompagnés par epoux.se"] = epoux
                resultResearch=resultResearch.filter(DetailRegistre.epoux == 0)

            if enfants =="oui":
                filtreTemporaire["enfants"] = enfants
                resultResearch = resultResearch.filter(DetailRegistre.nbEnfants != None)
            if enfants == "non":
                filtreTemporaire["enfants"] = enfants
                resultResearch = resultResearch.filter(DetailRegistre.nbEnfants == None)

            if membreFamille == "oui":
                filtreTemporaire["autre membre de famille"] = membreFamille
                resultResearch = resultResearch.filter(DetailRegistre.nbAutreMembre != None)
            if membreFamille == "non":
                filtreTemporaire["autre membre de famille"] = membreFamille
                resultResearch = resultResearch.filter(DetailRegistre.nbAutreMembre == None)

            if autrePersonne =="oui":
                filtreTemporaire["autre personnes"] = autrePersonne
                resultResearch = resultResearch.filter(DetailRegistre.nbPersSupplement != None)
            if autrePersonne =="non":
                filtreTemporaire["autre personnes"] = autrePersonne
                resultResearch = resultResearch.filter(DetailRegistre.nbPersSupplement == None)

            if pysique:
                filtreTemporaire["Caractéristiques physiques"] = pysique
                resultResearch = resultResearch.join(CaracteristiquePhysique,
                                                     CaracteristiquePhysique.id_registre == DetailRegistre.id). \
                    filter(CaracteristiquePhysique.labelCaracteristique.in_(pysique))

            # si l'un des filtres relèves des catégories
            if filtreCategorie or filtreSousCategorie :
                # on rajoute à la requete de base+jointure avec DetailsRegistre les jointures les LienRegistresCategories
                resultResearch=resultResearch.join(LienRegistresCategories, DetailRegistre.id == LienRegistresCategories.id_registre)

                # si le filtre catégorie existe
                if filtreCategorie:
                    filtreTemporaire["categorie"] = filtreCategorie
                    # on construit la requête complète pour Categorie
                    # on rajoute la jointure pour Categorie et la condition where avec in_() si la/les catégories cochées sont dans le champs labelCategorie.
                    # Le résultat sera une addition de toutes les personnes qui sont regroupées sous les catégories mentionnées (l'equivalement de OU)
                    resultResearch = resultResearch.join(Categorie, LienRegistresCategories.id_categorie == Categorie.id).\
                        filter(Categorie.labelCategorie.in_(filtreCategorie))

                    # si filtre categorie et souscategorie ont été cochés à la fois
                    if filtreSousCategorie:
                        filtreTemporaire["souscategorie"] = filtreSousCategorie
                    # on consrtruit une requête complète uniquement pour les souscategories
                        resultResearchSoucat = db.session.query(Personne.id, Personne.nom, Personne.prenom,Personne.anneeNaissance).distinct(). \
                            join(DetailRegistre, DetailRegistre.id_personne == Personne.id). \
                            join(LienRegistresCategories, DetailRegistre.id == LienRegistresCategories.id_registre).\
                            join(Souscategorie, LienRegistresCategories.id_souscategorie == Souscategorie.id).\
                            filter(Souscategorie.labelSouscategorie.in_(filtreSousCategorie))
                        # on fait l'union entre les catégories et les sous-categories
                        # le résultat sera une addition de toutes les personnes qui relèvent de telle(s) catégories et les personnes qui relèvenrt de telle(s) sous-categories
                        resultResearch = resultResearch.union(resultResearchSoucat)

                # si la soucategorie a été cochée mais pas la categorie, on rajoute à la requête de base suite à la condition (if filtreCategorie or filtreSousCategorie)
                # la requête finale pour les sous-catégories seulement
                elif filtreSousCategorie:
                    filtreTemporaire["souscategorie"] = filtreSousCategorie
                    resultResearch = resultResearch.join(Souscategorie, LienRegistresCategories.id_souscategorie == Souscategorie.id).\
                        filter(Souscategorie.labelSouscategorie.in_(filtreSousCategorie))

        resultResearch = resultResearch.order_by(Personne.nom.asc()).all()
        return render_template('index.html', title=titre, personnes=resultResearch, categories=categories, caracteristiquesPysiques=caracteristiquesPysiques, filtreTemporaire=filtreTemporaire)

@appli.route('/personne/<int:identifier>')
def notice (identifier):
    titre = "Notice personne"
    # instanciation d'un objet personne avec un identifiant personne
    personneUnique = Personne.query.get(identifier)

    if personneUnique:
        # instanciation d'un objet DetailRegistre (qui contient tous les attributs de la classe)
        # résultat du type: [<DetailRegistre 872>, <DetailRegistre 953>, <DetailRegistre 1004>, <DetailRegistre 1736>, <DetailRegistre 4196>]
        listeDetailsRegistres = personneUnique.registresPers

        for registre in listeDetailsRegistres:
            # on change l'ordre des éléments dans les lieux declarés pour les afficher dans un ordre logique: Naissance, Domicile, délivrance du passeport, dernier passage, visa
            # (à l'aide de la methode sortByDestination créée auparavant) et on fait une réafectation de l'attribut lieuxDeclares de l'objet DetailRegistre
            # utilisation de la fonction sorted qui prend comme paramètres une liste et le nom d'une fonction (!! ce n'est pas un appel de fonction)
            registre.lieuxDeclares = sorted(registre.lieuxDeclares, key=sortByDestination)

        return render_template("notice.html",
                               title=titre,
                               unique=personneUnique,
                               detailsRegistres=listeDetailsRegistres)

    else:
        flash("La personne que vous cherchez n'existe pas", "warning")
        return redirect("/index")

@appli.route('/personneLieux/<int:identifier>')
def persLieux(identifier):
    """
    Fonction qui spécifie le fonctionnement de la route /personneLieux/<int:identifier>.
    La route renvoie la liste de tous les lieux de passage pour une personne donnée
    :param identifier: identifiant de la personne
    :return:
    """
    personneUnique= Personne.query.get(identifier)

    listeLieu=[]
    if personneUnique:
        # instanciation d'un objet DetailRegistre (qui contient tous les attributs de la classe)
        # résultat du type: [<DetailRegistre 872>, <DetailRegistre 953>, <DetailRegistre 1004>, <DetailRegistre 1736>, <DetailRegistre 4196>]
        listeDetailsRegistres = personneUnique.registresPers

        listeLieu = filterLieuxDeclareAvecUneNaissance(listeDetailsRegistres)

        return render_template("tous_lieux-par-pers.html", unique=personneUnique, listeLieu=listeLieu)
    else:
        flash("Cette personne n'existe pas", "warning")
        return redirect("/l-passage")

@appli.route('/cat-profession')
#la page avec la liste des catégories et des sous-catégories et du nombre de personnes pour chaque
def catProfession():
    titre = "Catégories professionnelles"


    # requete qui permet de regrouper le nombre de personnes par catégorie de métier par ordre aphabétique dans une liste de tuples comme ici:
    # [(295, <Catégorie professionnelle: acrobatie>), (128, <Catégorie professionnelle: autres metiers>), (2, <Catégorie professionnelle: aérostatier>),,(...)]
    nombrePersParCat = db.session.query(func.count((Personne.id).distinct()),
                                        Categorie). \
                                        filter(DetailRegistre.id_personne == Personne.id). \
                                        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
                                        filter(LienRegistresCategories.id_categorie == Categorie.id). \
                                        group_by(Categorie).order_by (Categorie.labelCategorie.asc()).all()

    # on trie la liste pour afficher à la fin: "autres metiers", "indétérminé" et "domestique"
    nombrePersParCat= sorted(nombrePersParCat, key=sortByMetiers)

    # requete qui permet de regrouper le nombre de personnes par sous-catégorie de métier dans une liste de tuple comme ici:
    # [(89, <Souscategorie animaux savants>), (21, <Souscategorie artificier>), (205, <Souscategorie chanteur>), (14, <Souscategorie combat d'animaux>),(...)]
    nombrePersParSousCat = db.session.query(func.count((Personne.id).distinct()),
                                        Souscategorie). \
                                        filter(DetailRegistre.id_personne == Personne.id). \
                                        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
                                        filter(LienRegistresCategories.id_souscategorie == Souscategorie.id). \
                                        group_by(Souscategorie).all()


    return render_template('catProfession.html', title = titre, nombrePersParCat = nombrePersParCat, nombrePersParSousCat = nombrePersParSousCat)

@appli.route('/personnesCategorie/<int:identifier>')
#la page avec la liste des personnes par catégorie de métier
def persCat(identifier):
    categorie = Categorie.query.get(identifier)
    page = request.args.get("page", 1, type=int)


    # requete qui permet de retourner le une liste avec le  nom, le prénom des personnes ayant la catégorie de métier définie.
    # retuorne un résultat de type : [(3139, 'Abd-el Kerim', 'Ben Ahmed'), (2531, 'Alirot', 'Jean-Bernard'), (212, 'Alirot', None), (211, 'Ambroisia', None), (...)]
    personneCat = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom).\
                                        filter(DetailRegistre.id_personne == Personne.id). \
                                        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
                                        filter(LienRegistresCategories.id_categorie == str(identifier)). \
                                        order_by (Personne.nom.asc()).\
                                        paginate(page=page, per_page=PERSONNES_PAR_PAGES)

    if categorie and personneCat:
        return render_template('pers-Categ.html', personneCat = personneCat, categorie = categorie)

    else:
        flash("Ce metier n'existe pas", "warning")
        return redirect("/cat-profession")

@appli.route('/personnesSousCategorie/<int:identifier>')
#la page avec la liste des personnes par souscatégorie de métier
def persSousCat(identifier):
    soucategorie = Souscategorie.query.get(identifier)
    page = request.args.get("page", 1, type=int)


    # retluorne un résultat de type : [(1484, 'Bernière', 'Joseph'), (1579, 'Chatel', 'Benjamin'), (1126, 'Landrevie', 'Pierre'), (3805, 'Mazier', 'François'), (...)]
    personneSoucatCat = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom).\
                                        filter(DetailRegistre.id_personne == Personne.id). \
                                        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
                                        filter(LienRegistresCategories.id_souscategorie == str(identifier)). \
                                        order_by(Personne.nom.asc()). \
                                        paginate(page=page, per_page=PERSONNES_PAR_PAGES)

    return render_template('pers-sousCateg.html', personneSoucatCat = personneSoucatCat, soucategorie = soucategorie)

@appli.route('/accompagne-par-epoux-se')
#la page avec la liste des personnes accompagnés par l'époux
def persEpoux():

    page = request.args.get("page", 1, type=int)

    personneAvecEpoux = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.epoux == 1). \
        order_by(Personne.nom.asc()). \
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)
    return render_template("pers-epoux.html", personneAvecEpoux=personneAvecEpoux )

@appli.route('/accompagne-par-enfant')
#la page avec la liste des personnes accompagnés par les enfants
def persEnfant():

    page = request.args.get("page", 1, type=int)

    personneAvecEnfant = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.nbEnfants != None). \
        order_by(Personne.nom.asc()). \
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)
    return render_template("pers-par-enfant.html", personneAvecEnfant=personneAvecEnfant)

@appli.route('/personneCaracteristiques/<label>')
#la page avec la liste des personnes par caractéristique physique
def persCarracteristique(label):
    page = request.args.get("page", 1, type=int)

    #resultat : une liste du type [(1398, 'Bara', 'Jean-François-Joseph'), (2145, 'Brugoni', 'Antoine'), (1777, 'Brumini', 'Antoine')
    personneCaracteristique = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.id == CaracteristiquePhysique.id_registre). \
        filter(CaracteristiquePhysique.labelCaracteristique == label). \
        order_by(Personne.nom.asc()). \
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)

    return render_template('pers-Caracteristiques.html', label=label, personneCaracteristique=personneCaracteristique)

@appli.route('/l-passage')
def passage():
    titre = "Lieu de passage"
    # récupère la valeur de la clé "page" depuis l'URL, s'il n'y a pas de paramètre, retourne 1
    # ex: http://127.0.0.1:5000/index?page=2
    page = request.args.get("page", 1, type=int)

    # il faut faire le query sur tous les champs qu'on veut afficher ou utiliser.

    # le résultat du query retourne une liste de tuple avec le nombre de passages, le nom de la ville et l'id de la ville
    # (ex:[(2796, 'Agen', 1480, '44.20199', '0.62055'), (453, 'Lyon', 722, '45.74846', '4.84671'),...)
    lieuxNombrePassage = db.session.query(func.count(Lieu.id), Lieu.nomLieuFr, Lieu.id, Lieu.lat, Lieu.lng) \
        .filter(LieuDeclare.id_lieu == Lieu.id) \
        .filter(LieuDeclare.typeLieu=="Enregistrement") \
        .group_by(Lieu.id)\
        .all()

    return render_template('l-passage.html', title = titre, lieux = lieuxNombrePassage)

@appli.route('/pers-par-passage/<int:id_villePassage>')
def persParPass(id_villePassage):

    villePassage = Lieu.query.get(id_villePassage)

    # le résultat du query retourne une liste de tuple avec l'id de la personne le nom et le prénom
    # (ex:[(935, 'Allard', 'Jean-Louis'), (1805, 'Chamard', 'Baptiste'),...])
    page = request.args.get("page", 1, type=int)
    persParPassage = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom) \
        .filter(Personne.id == DetailRegistre.id_personne) \
        .filter(DetailRegistre.id == LieuDeclare.id_registre) \
        .filter(LieuDeclare.id_lieu == str(id_villePassage))\
        .filter(LieuDeclare.typeLieu=="Enregistrement").order_by(Personne.nom)\
        .paginate(page=page, per_page=LIEUX_PAR_PAGES)

    return render_template("pers-par-passage.html", persParPassage=persParPassage, villePassage=villePassage )

@appli.route('/l-naissance')
def naissance():
    titre = "Lieu de naissance"
    # récupère la valeur de la clé "page" depuis l'URL, s'il n'y a pas de paramètre, retourne 1
    # ex: http://127.0.0.1:5000/index?page=2


    # le résultat du query retourne une liste de tuple avec
    # le nombre de personne par ville de naissance, le nom de la ville et l'id de la ville
    # (ex:[(2, 'Varsovie', 1, '52.22977', '21.01178'), (1, 'Mińsk Mazowiecki', 2, '52.17935', '21.57251'),,...)
    lieuNaissance = db.session.query(func.count(Lieu.id), Lieu.nomLieuFr, Lieu.id, Lieu.lat, Lieu.lng) \
        .join(Personne, Personne.id_lieuxNaissance == Lieu.id) \
        .group_by(Lieu.id).all()


    return render_template('naissance.html', title=titre, lieux=lieuNaissance)

@appli.route('/pers-par-villeNaissance/<int:id_villeNaissance>')
def persParNaissance(id_villeNaissance):

    villeNaissance = Lieu.query.get(id_villeNaissance)

    # le résultat du query retourne une liste de tuple avec l'id de la personne le nom et le prénom
    # (ex:[(935, 'Allard', 'Jean-Louis'), (1805, 'Chamard', 'Baptiste'),...])
    page = request.args.get("page", 1, type=int)
    persParNaissance = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom) \
        .filter(Personne.id_lieuxNaissance == Lieu.id) \
        .filter(Lieu.id == villeNaissance.id).order_by(Personne.nom)\
        .paginate(page=page, per_page=LIEUX_PAR_PAGES)
    #print(persParPassage)

    return render_template("pers-par-naissance.html", persParNaissance=persParNaissance, villeNaissance=villeNaissance)


@appli.route('/glossaire')
def glossaire():

    glossaireMetiers = db.session.query(DetailRegistre.professionOrigine.distinct(),Categorie.labelCategorie, Souscategorie.labelSouscategorie).\
        filter(LienRegistresCategories.id_registre==DetailRegistre.id).\
        filter(Categorie.id==LienRegistresCategories.id_categorie).\
        filter(Souscategorie.id==LienRegistresCategories.id_souscategorie)\
        .all()

    return render_template('glossaire.html', title="Glossaire de métiers", glossaireMetiers=glossaireMetiers)
#############################################################################
#                             PAGES MODIFICATION-CREATION                   #
#############################################################################
@appli.route("/creer-personne", methods=["GET", "POST"])
@login_required
def creer_personne():
    """ Route permettant à l'utilisateur de créer une notice personne unique """

    # recupération de la liste des lieux pour assurer l'automplete dans l'input HTML des lieux
    listeNomLieu = extractLieuxComplet()
    # déclaration d'un dictionnaire qui va regrouper les informations saises par l'utilisateurs et qui permet de ne pas perdre les info saisies
    personneTemporaire = {}
    #lieuParDefaut = Lieu.query.filter(Lieu.nomLieu == 'Non renseigné').first()

    if request.method == "POST":

        #récupération du lieu de naissance et du nom de la personne dans le formulaire
        nomPersonne = request.form.get("nom", None)
        lieuNaissanceComplet = request.form.get("lieuNaissance", None)
        lieuDecesComplet = request.form.get("lieuDeces", None)
        prenom = request.form.get("prenom", None)
        sexe = request.form.get("sexe", None)
        anneeNaissance = request.form.get("anneeNaissance", None)
        observations = request.form.get("description", None)
        dateDeces = request.form.get("dateDeces", None)
        certitudeNP = request.form.get("certitude", None)

        personneTemporaire["nom"] = nomPersonne
        personneTemporaire["prenom"] = prenom
        personneTemporaire["sexe"]= sexe
        personneTemporaire["anneeNaissance"] = anneeNaissance
        personneTemporaire["observations"] = observations
        personneTemporaire["dateDeces"] = dateDeces
        personneTemporaire["certitudeNP"] = certitudeNP
        personneTemporaire["lieuNaissance"] = lieuNaissanceComplet
        personneTemporaire["lieuDeces"] = lieuDecesComplet

        #Si le résultat de la requete, retourne un lieu, je crée la personne avec l'identifiation du lieu
        # transforme le str du lieu de passage (enregisrtement) en liste et récupère uniquement l'id (le dernier élément de la liste)
        listeLieuNaissance = lieuNaissanceComplet.split(",")
        # on récupère le dernière de la liste, l'id du lieu
        id_lieuNaissance = listeLieuNaissance[-1]

        listeLieuDeces = lieuDecesComplet.split(",")
        id_lieuDeces = listeLieuDeces[-1]

        status, data = Personne.create_person(
                # récupère le "nom", "prenom", etc dans la valeur de l'attribut name de la balise html <input>, <textatrea> ou <select>
                nom=nomPersonne,
                prenom=prenom,
                sexe=sexe,
                anneeNaissance=anneeNaissance,
                observations=observations,
                id_lieuxNaissance = id_lieuNaissance,
                dateDeces=dateDeces,
                id_lieuDeces= id_lieuDeces,
                certitudeNP=certitudeNP
                )
        if status is True:
            flash("Création d'une nouvelle personne réussie !", "success")
            #récupère l'objet personne qu'on vient de créer
            newpers = db.session.query(Personne).filter(Personne.nom == nomPersonne).order_by(Personne.id.desc()).first()
            return redirect("/personne/" + str(newpers.id))

        else:
            flash("La création d'une nouvelle personne a échoué pour les raisons suivantes : " + ", ".join(data), "error")
            render_template("creer_personne.html", lieux=listeNomLieu, personneTemporaire=personneTemporaire)

    return render_template("creer_personne.html", lieux = listeNomLieu, personneTemporaire=personneTemporaire)

@appli.route("/modifier-personne/<int:idPersonne>", methods=["GET", "POST"])
@login_required
def modifier_personne(idPersonne):
    # envoyer à la page html les éléments de l'objet personne correspondant à l'identifiant de la route
    personne_origine = Personne.query.get(idPersonne)
    listeNomLieu = extractLieuxComplet()


    if request.method == "GET":
        return render_template("modification_personne.html", personne_origine=personne_origine, lieux=listeNomLieu)

    if request.method == "POST":
        # récupération du lieu de naissance et du lieu de décès dans le formulaire
        lieuNaissanceComplet = request.form.get("lieuNaissance", None)
        lieuDecesComplet = request.form.get("lieuDeces", None)

        # transforme le str du lieu de passage (enregisrtement) en liste et récupère uniquement l'id (le dernier élément de la liste)
        listeLieuNaissance = lieuNaissanceComplet.split(",")
        # on récupère le dernière de la liste, l'id du lieu
        id_lieuNaissance = listeLieuNaissance[-1]

        listeLieuDeces = lieuDecesComplet.split(",")
        id_lieuDeces = listeLieuDeces[-1]
        # Si le résultat de la requete, retourne un lieu, je crée la personne avec l'identifiation du lieu

        status, data = Personne.modify_person(
            # récupère le "nom", "prenom", etc dans la valeur de l'attribut name de la balise html <input>, <textatrea> ou <select>
            id=idPersonne,
            nom=request.form.get("nom", None),
            prenom=request.form.get("prenom", None),
            sexe=request.form.get("sexe", None),
            anneeNaissance=request.form.get("anneeNaissance", None),
            observations=request.form.get("description", None),
            id_lieuxNaissance=id_lieuNaissance,
            dateDeces=request.form.get("dateDeces", None),
            id_lieuDeces=id_lieuDeces,
            certitudeNP=request.form.get("certitude", None)
        )
        if status is True:
            flash("Modification de personne réussie !", "success")

            # récupéré l'objet personne qu'on vient de créer
            return redirect("/personne/" + str(idPersonne))

        else:
            flash("La modification de la personne a échoué pour les raisons suivantes : " + ", ".join(data),
                  "error")

    return render_template("modification_personne.html", personne_origine=personne_origine, lieux = listeNomLieu)

@appli.route("/creer-lieu", methods=["GET", "POST"])
@login_required
def creer_lieu():
    """ Route permettant à l'utilisateur de créer une notice de lieu """

    if request.method == "POST":
        status, data = Lieu.create_lieu(
                # récupère les valeurs de l'attribut name de la balise html <input>, <textatrea> ou <select>
                nomLieuFr=request.form.get("nomLieu", None),
                pays=request.form.get("pays", None),
                region=request.form.get("region", None),
                departement= request.form.get("depart", None),
                codeINSEE=request.form.get("codeINSEE", None),
                lat=request.form.get("latitude", None),
                lng=request.form.get("longitude", None),
                id_geonames=request.form.get("idGeonames", None)
            )
        if status is True:
              flash("Création d'un nouveau lieu réussie !", "success")
        else:
              flash("La création d'un nouveau lieu a échoué pour les raisons suivantes : " + ", ".join(data),
                      "error")

    return render_template("creer_lieu.html")

@appli.route("/modifier-lieu/<int:id_lieu>", methods=["GET", "POST"])
@login_required
def modifier_lieu(id_lieu):
    """ Route permettant à l'utilisateur de modifier un formulaire avec les données d'un lieu """
    # envoyer à la page html les éléments de l'objet lieu correspondant à l'identifiant de la route
    lieu_origine = Lieu.query.get(id_lieu)
    if request.method == "GET":
        return render_template("modification_lieu.html", lieu_origine=lieu_origine)

    # on récupère les données du formulaire modifié
    else:
        status, data = Lieu.modifier_lieu(
            # récupère les valeurs de l'attribut name de la balise html <input>, <textatrea> ou <select>
            id=id_lieu,
            nomLieuFr=request.form.get("nomLieu", None),
            pays=request.form.get("pays", None),
            region=request.form.get("region", None),
            departement=request.form.get("depart", None),
            codeINSEE=request.form.get("codeINSEE", None),
            lat=request.form.get("lat", None),
            lng=request.form.get("lng", None),
            id_geonames=request.form.get("idGeonames", None)
        )
        if status is True:
            flash("Modification du lieu réussie !", "success")
        else:
            flash("La modification du lieu a échoué pour les raisons suivantes : " + ", ".join(data),
                  "error")

    return render_template("modification_lieu.html", lieu_origine=lieu_origine)

@appli.route("/creer-registre/<int:idPersonne>", methods=["GET", "POST"])
@login_required
def creer_registre(idPersonne):
    """
    Methoide permettand de créer un nouiveau registre pour la personne avec l'identifiant idPersonne
    :param idPersonne: int. identifiant de la personne à laquelle sera rattaché le registre
    :return:
    """
    personneUnique = Personne.query.get(idPersonne)
    registreTemporaire = {}

    #############################################################################
    #   Requête dans la base pour récupèrer des informations à passer au html   #
    #############################################################################

    #recupération de la liste des lieux pour assurer l'automplete dans l'input HTML des lieux. on passe le nom en français, le département, le pays et l'id du lieu
    listeNomLieu = extractLieuxComplet()

    # recupération de la liste des catégories professionnemmes pour les passer dans l'input HTML à la création du métier
    categories = Categorie.query.all()

    # on fournit une liste (en dur) avec les types de documents pour l'autocomplete. A mettre à jour si un nouveau type de document est proposé
    typeDocument = ['Registre visas', 'Souches passeports', 'Liste passeports', 'Passeports']
    # on fournit la liste en dur avec les types de lieux
    listeTypeLieux = ["Naissance", "Domicile", "Délivrance du passeport", "Dernier Passage", "Destination", "Visa",
                      "Décès"]
    # on fournit une liste (extraction depuis la bdd) avec le nom des archives pour l'autocomplete.
    # résultat du type [('Archives municipales -  BEAUNE',), ('Archives municipales -  LYON',), ('Archives municipales -  LIMOGES',)]
    nomsArchive = db.session.query(DetailRegistre.nomArchive).distinct().all()
    listeNomsArchive = []
    for nom in nomsArchive:
        #cityFirst = nom.split(" - ")
        listeNomsArchive.append(nom[0])

    ######################################################################################
    #  Methode GET: renvoie les informations uniques de la personne dans le formulaire   #
    ######################################################################################

    if request.method == "GET":
        return render_template("creer_registre.html",
                               personneUnique=personneUnique,
                               lieux=listeNomLieu,
                               categories=categories,
                               typeDocument=typeDocument,
                               listeNomsArchive=listeNomsArchive,
                               registreTemporaire=registreTemporaire,
                               listeTypeLieux=listeTypeLieux)

    ######################################################################################
    #      Méthode POST: récupère les informations saisies pour chaque régistre         #
    ######################################################################################

    elif request.method == "POST":
        erreurs = []
        listeObjet_lieuDeclare = []
        listeObjetsMetiers =[]
        listeObjetCaracteristiques = []
        listeObjetsVoyageAvec =[]

        # ----- RECUPERATION DES VALEURS DU FORMULAIRE HTML ----##
        #NOM+Prenom+taille+professionOrigine+dureeSejour+description+accompagnePar+caracteristiquesPhysiques+autresCaracteristiques
        nomOrigine = request.form.get("nom", None)
        prenomOrigine = request.form.get("prenom", None)
        taillePersonneHTML = request.form.get("taille", None)
        if "," in taillePersonneHTML:
            taillePersonne = taillePersonneHTML.replace (',', '.')
        else:
            taillePersonne = taillePersonneHTML

        agePersonne = request.form.get("age", None)
        professionOrigine = request.form.get("metier", None)
        dureeSejour = request.form.get("duree", None)
        description = request.form.get("description", None)
        accompagnePar = request.form.get("accompagnePar", None)
        caracteristiquesPhysiques = request.form.get("carrPhys", None)
        autresCaracteristiques = request.form.get("autreCarr", None)
        nbEnfants = request.form.get("nbEnfants", None)
        nbAutreMembre = request.form.get("nbAutreMembre", None)
        nbPersSupplement = request.form.get("nbAutrePers", None)
        pseudonyme = request.form.get("pseudo", None)
        nomArchive = request.form.get("archive", None)

        if nomArchive == '':
            erreurs.append("Le nom de l'institution d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Ajouter les sources d'archives'")
        cote = request.form.get("cote", None)

        if cote == '':
            erreurs.append(
                "La côte d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Ajouter les sources d'archives'")

        natureDoc = request.form.get("typeDoc", None)

        nrOrdre = request.form.get("ordre", None)
        photoArchive = request.form.get("photo", None)
        commentaires = request.form.get("commentaires", None)

        # recupération checkbox
        epoux = request.form.get("epoux", None)  # récupère la valeur de l'attribut value
        borgne = request.form.get("borgne", None)
        aveugle = request.form.get("aveugle", None)
        culJatte = request.form.get("cul-de-jatte", None)
        unijambiste = request.form.get("unijambiste", None)
        manchot = request.form.get("manchot", None)
        ampute = request.form.get("ampute", None)
        cicatrice = request.form.get("cicatrice", None)
        verole = request.form.get("verole", None)
        autreCaracteristiques = request.form.get("autreCaracteristiques", None)

        #récupération liste, objets complexes
        lieuEnregistrementComplet = request.form.get("lieuPassage", None)
        dateEnregistremnt = request.form.get("datePassage", None)

        # recupère une liste avec tous les labels des lieux déclarés
        listeLabelLieuDeclare = request.form.getlist("listeLieuDeclare", None)
        # recupère une liste avec tous les lieux normalisés
        labelLieuNormaliseHtml = request.form.getlist("listeLieuNormal", None)
        # récupère une liste avec toutes les dates
        listeDate = request.form.getlist("listeDates", None)
        # récupère une liste avec tous les types de lieux
        listeTypeLieu = request.form.getlist("listeTypeLieu", None)

        # récupération une liste avec tous les identifiants des personnes qui voyagent avec la personne du registre
        listePersonnesAccompagnantes = request.form.getlist("voyageAvecIdPers", None)

        # récupere les categories et les souscategories
        listeCategories = request.form.getlist("cat", None)
        listeSoucategories = request.form.getlist("sousCat", None)



#---OBJETS TEMPORAIRE POUR PERSISTER LES DONNEES---------#

        #on déclare une liste vide qui récupère toutes les listes des élements du lieuDeclarés [ [lieuD, lieuN, Date, Type], [lieuD, lieuN, Date, Type] ]
        listeGlobaleTemporaireLieuxD =[]

        # boucke sur la taille de la liste. définit la taille de la liste listeLabelLieuDeclare qui est la même que celle des autres listes des lieuxDeclarées
        for i in range(0, len(listeLabelLieuDeclare)):
            # déclare une liste pour un seul regroupement d'éléments de lieux déclarés
            listeTemporaireLieuDeclare = []
            listeTemporaireLieuDeclare.append(listeLabelLieuDeclare[i])
            listeTemporaireLieuDeclare.append(labelLieuNormaliseHtml[i])
            listeTemporaireLieuDeclare.append(listeDate[i])
            listeTemporaireLieuDeclare.append(listeTypeLieu[i])
            #on ajoute la liste à la liste globale
            listeGlobaleTemporaireLieuxD.append(listeTemporaireLieuDeclare)

        # on déclare une liste vide qui récupère toutes les listes des élements du lieuDeclarés [ [lieuD, lieuN, Date, Type], [lieuD, lieuN, Date, Type] ]
        listeGlobaleTemporaireCatSoucat = []

        # boucke sur la taille de la liste. définit la taille de la liste listeLabelLieuDeclare qui est la même que celle des autres listes des lieuxDeclarées
        for i in range(0, len(listeCategories)):
            # déclare une liste pour un seul regroupement qui comprend une catégorie et une sous-catégorie
            listeTemporaireCatSoucat = []
            listeTemporaireCatSoucat.append(listeCategories[i])
            listeTemporaireCatSoucat.append(listeSoucategories[i])
            # on ajoute la liste à la liste globale
            listeGlobaleTemporaireCatSoucat.append(listeTemporaireCatSoucat)

        registreTemporaire["nomOrigine"]=nomOrigine
        registreTemporaire["prenomOrigine"] = prenomOrigine
        registreTemporaire["taillePersonne"] = taillePersonne
        registreTemporaire["agePersonne"] = agePersonne
        registreTemporaire["professionOrigine"] = professionOrigine
        registreTemporaire["dureeSejour"] = dureeSejour
        registreTemporaire["description"] = description
        registreTemporaire["accompagnePar"] = accompagnePar
        registreTemporaire["caracteristiquesPhysiques"] = caracteristiquesPhysiques
        registreTemporaire["autresCaracteristiques"] = autresCaracteristiques
        registreTemporaire["epoux"] = epoux
        registreTemporaire["nbEnfants"] = nbEnfants
        registreTemporaire["nbAutreMembre"] = nbAutreMembre
        registreTemporaire["nbPersSupplement"] = nbPersSupplement
        registreTemporaire["pseudonyme"] = pseudonyme
        registreTemporaire["nomArchive"] = nomArchive
        registreTemporaire["cote"] = cote
        registreTemporaire["natureDoc"] = natureDoc
        registreTemporaire["nrOrdre"] = nrOrdre
        registreTemporaire["photoArchive"] = photoArchive
        registreTemporaire["commentaires"] = commentaires
        registreTemporaire["borgne"] = borgne
        registreTemporaire["aveugle"] = aveugle
        registreTemporaire["culJatte"] = culJatte
        registreTemporaire["unijambiste"] = unijambiste
        registreTemporaire["manchot"] = manchot
        registreTemporaire["ampute"] = ampute
        registreTemporaire["cicatrice"] = cicatrice
        registreTemporaire["verole"] = verole
        registreTemporaire["autreCaracteristiques"] = autreCaracteristiques
        registreTemporaire["lieuPassage"] = lieuEnregistrementComplet
        registreTemporaire["dateEnregistremnt"] = dateEnregistremnt
        # ajoute au dictionnaire la liste gloable des lieux déclarés
        registreTemporaire["lieuxDeclares"] = listeGlobaleTemporaireLieuxD
        # ajoute au dictionnaire la liste des identifiants des personnes qui voyagent avec le registre
        registreTemporaire["voyageAvec"] = listePersonnesAccompagnantes
        registreTemporaire["catSoucat"] = listeGlobaleTemporaireCatSoucat


 #      LIEUX DECLARES         #

        # transforme le str du lieu de passage (enregisrtement) en liste et récupère uniquement l'id (le dernier élément de la liste)
        lieuEnregistrementListe = lieuEnregistrementComplet.split(",")
        id_lieuPassage = lieuEnregistrementListe[-1]

        lieuEnregistrement = LieuDeclare(
            labelLieuDeclare=lieuEnregistrementComplet,
            id_lieu=id_lieuPassage,
            date=dateEnregistremnt,
            typeLieu="Enregistrement")
        # on ajoute l'objet à la liste d'objets déclarés
        listeObjet_lieuDeclare.append(lieuEnregistrement)

        # utilisation de la méthode genrateObjetLieuxDeclare pour créer des objets Lieux déclarés
        genrateObjetLieuxDeclare(labelLieuNormaliseHtml, listeDate, listeLabelLieuDeclare, listeObjet_lieuDeclare,
                                 listeTypeLieu)


#--------- ANNEES NAISSANCE CALCULEE, VOYAGE AVEC, EPOUX  -------#

        if agePersonne:
            anneeNaissCalcule = int(dateEnregistremnt.split("-")[0]) - int(agePersonne)
        else:
            anneeNaissCalcule = None

        # on définit la taille de la liste des identifiants des personnes accompagnantes
        generatObjeteVoyageAvec(listeObjetsVoyageAvec, listePersonnesAccompagnantes)

        if epoux=="on":
            epoux=1
        else:
            epoux=0

 # ------ CARACTERISTIUQES PHYSIQUES------##

        # récupérer les caracteristiques physiques

        if borgne == "on" :
            objetCaracteristique=CaracteristiquePhysique(labelCaracteristique="borgne")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if aveugle == "on" :
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="aveugle")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if culJatte == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="cul-de-jatte")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if unijambiste == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="unijambiste")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if manchot == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="manchot")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if ampute == "on" :
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="amputé mains, doigts, pieds")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if cicatrice == "on" :
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="cicatrice")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if verole == "on" :
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="vérole")
            listeObjetCaracteristiques.append(objetCaracteristique)

        if autreCaracteristiques == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="autres caractéristiques")
            listeObjetCaracteristiques.append(objetCaracteristique)


# ----- METIERS --------##

        # remplace les labels de deux listes par les id correspondants dans la base
        for i, categorie in enumerate(listeCategories):
            if categorie != "" and categorie != 'aucune':
                objectCategorie = Categorie.query.filter_by(labelCategorie=categorie).first()
                # remplace le label de la categorie par l'id
                listeCategories[i] = objectCategorie.id

        for i, souscategorie in enumerate(listeSoucategories):
            if souscategorie != "" and souscategorie != 'aucune':
                objetSouscategorie = Souscategorie.query.filter_by(labelSouscategorie=souscategorie).first()
                # remplace le label de la souscategorie par l'id sinon, rajoute None
                listeSoucategories[i] = objetSouscategorie.id
            else:
                listeSoucategories[i] = None

        generateObjectCategorie(listeCategories, listeObjetsMetiers, listeSoucategories)


        #------TESTS ET CONTROLS-------#

        if listeTypeLieu.count("Naissance") > 1 \
            or listeTypeLieu.count("Domicile") > 1 \
            or listeTypeLieu.count("Délivrance du passeport") > 1 \
            or listeTypeLieu.count("Dernier Passage") > 1 \
            or listeTypeLieu.count("Décès") > 1 \
            or listeTypeLieu.count("Destination") > 1:
            erreurs.append("Les lieux de type Naissance, Domicile, Délivrance du passeport, Dernier Passage, Destination Décès doivent figurer une seule fois")

        if lieuEnregistrementComplet == "":
            erreurs.append("Le lieu d'enregistrement est obligatoire. Vérifiez la rubrique 'Ajouter les élements d'identification'")

        if dateEnregistremnt =="":
            erreurs.append("La date est obligatoire. Vérifiez la rubrique 'Ajouter les élements d'identification'")

        if len(erreurs) > 0 :

            flash("La création d'un nouvel enregistrement a échoué pour les raisons suivantes : " + ", ".join(set(erreurs)), "error")

        # -------GENERER LES OBJETS ET ALIMENTER LA CREATION DU REGISTRE -------#
        # si les tests sont propres, on génère un objet LieuDeclare pour le lieu d'enregistrement et un avec un lieu déclaré
        else:

            status, data = DetailRegistre.create_register(
                # récupère le "nom", "prenom", etc dans la valeur de l'attribut name de la balise html <input>, <textatrea> ou <select>
                id_personne=idPersonne,
                nomOrigine=nomOrigine,
                prenomOrigine=prenomOrigine,
                agePersonne=agePersonne,
                anneeNaissCalcule=anneeNaissCalcule,
                taillePersonne=taillePersonne,
                professionOrigine=professionOrigine,
                dureeSejour=dureeSejour,
                description=description,
                accompagnePar=accompagnePar,
                caracteristiquesPhysiques=caracteristiquesPhysiques,
                autresCaracteristiques=autresCaracteristiques,
                epoux =epoux,
                nbEnfants = nbEnfants,
                nbAutreMembre = nbAutreMembre,
                nbPersSupplement = nbPersSupplement,
                pseudonyme = pseudonyme,
                nomArchive=nomArchive,
                cote=cote,
                natureDoc=natureDoc,
                nrOrdre=nrOrdre,
                photoArchive=photoArchive,
                commentaires=commentaires,
                lieuxDeclares = listeObjet_lieuDeclare,
                liensCategories=listeObjetsMetiers,
                caracteristiques=listeObjetCaracteristiques,
                voyageAvecRegistre=listeObjetsVoyageAvec)

            if status is True:
               flash("Création d'un nouveau registre réussie !", "success")
               return redirect("/personne/"+str(idPersonne))

            else:
               flash("La création d'un nouvel enregistrement a échoué pour les raisons suivantes : " + ", ".join(data), "error")


        return render_template("creer_registre.html",
                               personneUnique=personneUnique,
                               lieux=listeNomLieu,
                               categories=categories,
                               typeDocument=typeDocument,
                               listeNomsArchive=listeNomsArchive,
                               registreTemporaire=registreTemporaire,
                               listeTypeLieux=listeTypeLieux
                               )

@appli.route("/modifier-registre/<int:id_registre>", methods=["GET", "POST"])
@login_required
def modifier_registre(id_registre):
    """
    Route permettant à l'utilisateur de modifier un formulaire avec les données d'un registre
    :param id_registre: int. L'identifiant du registre à modifier
    :return:
    """
    #############################################################################
    #   Requête dans la base pour récupèrer des informations à passer au html   #
    #############################################################################

    # recupération de la liste des lieux (table lieux) pour assurer l'automplete dans l'input HTML des lieux. on passe le nom en français, le département, le pays et l'id du lieu. Résultat du type: ['Varsovie, Warszawa, Pologne, 1', 'Mińsk Mazowiecki, Powiat miński, Pologne, 2', 'Sétif, Algérie, 3', 'Oran, Algérie, 4']
    listeNomLieu = extractLieuxComplet()

    # recupération de la liste des catégories professionnemmes pour les passer dans l'input HTML à la création du métier
    listeObjetscategories = Categorie.query.all()

    # on fournit une liste (en dur) avec les types de documents pour l'autocomplete. A mettre à jour si un nouveau type de document est proposé
    typeDocument = ['Registre visas', 'Souches passeports', 'Liste passeports', 'Passeports']

    # on fournit une liste (extraction depuis la bdd) avec le nom des archives pour l'autocomplete.
    nomsArchive = db.session.query(DetailRegistre.nomArchive).distinct().all()
    listeNomsArchive = []
    for nom in nomsArchive:
        listeNomsArchive.append(nom[0])

    listeTypeLieux=["Naissance","Domicile","Délivrance du passeport","Dernier Passage","Destination","Visa","Décès"]

    # envoyer à la page html les éléments de l'objet registre correspondant à l'identifiant de la route
    registre_origine = DetailRegistre.query.get(id_registre)


    ######################################################################################
    #  Methode GET: renvoie les informations uniques de la personne dans le formulaire   #
    ######################################################################################
    if request.method == "GET":
        return render_template("modification_registre.html", registre_origine=registre_origine,lieux=listeNomLieu,listeObjetscategories=listeObjetscategories, typeDocument=typeDocument, listeNomsArchive=listeNomsArchive, listeTypeLieux=listeTypeLieux)

    ######################################################################################
    #      Méthode POST: récupère les informations saisies pour chaque régistre         #
    ######################################################################################

    elif request.method == "POST":
        erreurs = []
        listeObjet_lieuDeclare = []
        listeObjetsMetiers = []
        listeObjetCaracteristiques = []
        listeObjetsVoyageAvec = []


 #      LIEUX DECLARES         #

        # on récupère le lieu d'enregistrement et la date du formulaire modifié
        # récupération du lieu de passage avec la forme lieu, departement, pays, id dans le form (Lieu d'enregistrement) (attribut html name)
        lieuEnregistrementComplet = request.form.get("lieuPassage", None)
        # transforme le str du lieu de passage (enregisrtement) en liste et récupère uniquement l'id (le dernier élément de la liste)
        lieuEnregistrementListe = lieuEnregistrementComplet.split(",")
        # on récupère le dernière de la liste, l'id du lieu
        id_lieuPassage = lieuEnregistrementListe[-1]
        #on recupère le contenu du chamo date
        dateEnregistremnt = request.form.get("datePassage", None)
        if lieuEnregistrementComplet == "":
            erreurs.append("Le lieu d'enregistrement est obligatoire. Vérifiez la rubrique 'Ajouter les élements d'identification'")

        if dateEnregistremnt =="":
            erreurs.append("La date est obligatoire. Vérifiez la rubrique 'Modifier les élements d'identification'")

        else:
            # si les tests sont propres, on génère un objet LieuDeclare pour le lieu d'enregistrement et un avec un lieu déclaré
            lieuEnregistrement = LieuDeclare(
                labelLieuDeclare=lieuEnregistrementListe[0],# le premier de la liste pour le label du lieu déclaré
                id_lieu=id_lieuPassage,
                date=dateEnregistremnt,
                typeLieu="Enregistrement")
            # on ajoute l'objet à la liste d'objets déclarés
            listeObjet_lieuDeclare.append(lieuEnregistrement)

        # recupère une liste avec tous les lieux normalisés
        labelLieuNormaliseHtml = request.form.getlist("listeLieuNormal", None)
        # recupère une liste avec tous les labels des lieux déclarés
        listeLabelLieuDeclare = request.form.getlist("listeLieuDeclare", None)
        # récupère une liste avec toutes les dates
        listeDate = request.form.getlist("listeDates", None)
        # récupère une liste avec tous les types de lieux
        listeTypeLieu = request.form.getlist("listeTypeLieu", None)

        # utilisation de la méthode genrateObjetLieuxDeclare pour créer des objets Lieux déclarés
        genrateObjetLieuxDeclare(labelLieuNormaliseHtml, listeDate, listeLabelLieuDeclare, listeObjet_lieuDeclare,
                                 listeTypeLieu)

# ------ AGE, TAILLE, ANNEES NAISSANCE, VOYAGE AVEC   #

        # récupérer l'age de la personne et calculer l'année de naissance
        agePersonne = request.form.get("age", None)
        if agePersonne and dateEnregistremnt :
            anneeNaissCalcule = int(dateEnregistremnt.split("-")[0]) - int(agePersonne)
        else:
            anneeNaissCalcule = None

        taillePersonneHTML = request.form.get("taille", None)
        if "," in taillePersonneHTML:
            taillePersonne = taillePersonneHTML.replace(',', '.')
        else:
            taillePersonne = taillePersonneHTML

        # récupération une liste avec tous les identifiants des personnes qui voyagent avec la personne du registre
        listePersonnesAccompagnantes = request.form.getlist("voyageAvecIdPers", None)

        # on définit la taille de la liste des identifiants des personnes accompagnantes
        generatObjeteVoyageAvec(listeObjetsVoyageAvec, listePersonnesAccompagnantes)

# ------Archives et cotes
        nomArchive = request.form.get("archive", None)
        if nomArchive == '':
            erreurs.append(
                "Le nom de l'institution d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Ajouter les sources d'archives'")

        cote = request.form.get("cote", None)
        if cote == '':
            erreurs.append(
                "La côte d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Ajouter les sources d'archives'")

#------ CARACTERISTIUQES PHYSIQUES    -----##

        # récupérer les caracteristiques physiques
        borgne = request.form.get("borgne", None)
        if borgne == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="borgne")
            listeObjetCaracteristiques.append(objetCaracteristique)
        aveugle = request.form.get("aveugle", None)
        if aveugle == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="aveugle")
            listeObjetCaracteristiques.append(objetCaracteristique)
        culJatte = request.form.get("cul-de-jatte", None)
        if culJatte == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="cul-de-jatte")
            listeObjetCaracteristiques.append(objetCaracteristique)
        unijambiste = request.form.get("unijambiste", None)
        if unijambiste == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="unijambiste")
            listeObjetCaracteristiques.append(objetCaracteristique)
        manchot = request.form.get("manchot", None)
        if manchot == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="manchot")
            listeObjetCaracteristiques.append(objetCaracteristique)
        ampute = request.form.get("ampute", None)
        if ampute == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="amputé mains, doigts, pieds")
            listeObjetCaracteristiques.append(objetCaracteristique)
        cicatrice = request.form.get("cicatrice", None)
        if cicatrice == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="cicatrice")
            listeObjetCaracteristiques.append(objetCaracteristique)
        verole = request.form.get("verole", None)
        if verole == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="vérole")
            listeObjetCaracteristiques.append(objetCaracteristique)
        autreCaracteristiques = request.form.get("autreCaracteristiques", None)
        if autreCaracteristiques == "on":
            objetCaracteristique = CaracteristiquePhysique(labelCaracteristique="autres caractéristiques")
            listeObjetCaracteristiques.append(objetCaracteristique)

# ----- METIERS --------##

        # récupere les categories et les souscategories
        listeCategories = request.form.getlist("cat", None)
        listeSoucategories = request.form.getlist("sousCat", None)

        # remplace les labels de deux listes par les id correspondants dans la base
        for i, categorie in enumerate(listeCategories):
            if categorie != "" and categorie != 'aucune':
                objectCategorie = Categorie.query.filter_by(labelCategorie=categorie).first()
                # remplace le label de la categorie par l'id
                listeCategories[i] = objectCategorie.id

        for i, souscategorie in enumerate(listeSoucategories):
            if souscategorie != "" and souscategorie != 'aucune':
                objetSouscategorie = Souscategorie.query.filter_by(labelSouscategorie=souscategorie).first()
                # remplace le label de la souscategorie par l'id sinon, rajoute None
                listeSoucategories[i] = objetSouscategorie.id
            else:
                listeSoucategories[i] = None

        generateObjectCategorie(listeCategories, listeObjetsMetiers, listeSoucategories)

        # En cas d'erreurs
        if len(erreurs) > 0:
            flash("La modification a échoué pour les raisons suivantes : " + ", ".join(set(erreurs)),
                  "error")
            return render_template("modification_registre.html", registre_origine=registre_origine,lieux=listeNomLieu,listeObjetscategories=listeObjetscategories, typeDocument=typeDocument, listeNomsArchive=listeNomsArchive, listeTypeLieux=listeTypeLieux)

        else:
            # sortit le request pour l'id personne car on a besoin de le passer en paramètre du return
            idPersonne = request.form.get("idPers", None)
            # Sinon on récupère les valeurs de l'attribut name de la balise html <input>, <textatrea> ou <select>
            status, data = DetailRegistre.modifier_registre(
                id=id_registre,
                id_personne=idPersonne,
                indexOrigine=request.form.get("index", None),
                nomOrigine=request.form.get("nom", None),
                prenomOrigine=request.form.get("prenom", None),
                agePersonne=agePersonne,
                anneeNaissCalcule=anneeNaissCalcule,
                taillePersonne=taillePersonne,
                professionOrigine=request.form.get("metier", None),
                dureeSejour=request.form.get("duree", None),
                description=request.form.get("description", None),
                accompagnePar=request.form.get("accompagnePar", None),
                caracteristiquesPhysiques= request.form.get("carrPhys", None),
                autresCaracteristiques= request.form.get("autreCarr", None),
                epoux=request.form.get("epoux", None),
                nbEnfants=request.form.get("nbEnfants", None),
                nbAutreMembre=request.form.get("nbAutreMembre", None),
                nbPersSupplement=request.form.get("nbAutrePers", None),
                pseudonyme= request.form.get("pseudo", None),
                nomArchive=nomArchive,
                cote=cote,
                natureDoc=request.form.get("typeDoc", None),
                nrOrdre=request.form.get("ordre", None),
                photoArchive=request.form.get("photo", None),
                commentaires= request.form.get("commentaires", None),
                lieuxDeclares=listeObjet_lieuDeclare,
                voyageAvecRegistre=listeObjetsVoyageAvec,
                caracteristiques=listeObjetCaracteristiques,
                liensCategories=listeObjetsMetiers
            )
            if status is True:
                flash("Modification du registre réussie !", "success")
                return redirect(url_for('notice',identifier=idPersonne))
            else:
                flash("La modification a échoué pour les raisons suivantes : " + ", ".join(data),
                      "error")
                return render_template("modification_registre.html", registre_origine=registre_origine,
                                       lieux=listeNomLieu, listeObjetscategories=listeObjetscategories,
                                       typeDocument=typeDocument, listeNomsArchive=listeNomsArchive,
                                       listeTypeLieux=listeTypeLieux)

@appli.route("/supprimerPers/<int:nr_personne>")
@login_required
def deletePers(nr_personne):
    """ Route pour gérer la suppresion d'une personne dans la base
    :param nr_person : identifiant numérique de la personne
    """
    personne = Personne.query.get(nr_personne)
    if personne:
        for personneAccompagnant in personne.voyageAvecPers:
            VoyageAvec.delete_voyageAvec(personneAccompagnant.id)

    Personne.supprimer_personne(id_personne=nr_personne)
    flash("Suppression réussie !", "success")
    return redirect("/index")

@appli.route("/supprimerReg/<int:id_registre>")
@login_required
def deleteRegister(id_registre):
    """ Route pour gérer la suppresion d'un registre
    :param id_registre : identifiant numérique du registre
    """

    # on instancie un objet detail registre
    registre = DetailRegistre.query.get(id_registre)

    if registre:

        for lieux in registre.lieuxDeclares:
            LieuDeclare.delete_lieuDeclare(lieux.id)

        for lienRegistreCategorie in registre.liensCategories:
            LienRegistresCategories.delete_lienRegistreCategorie(lienRegistreCategorie.id)

        for caracteristique in registre.caracteristiques:
            CaracteristiquePhysique.delete_caractersitiques(caracteristique.id)

        for persVogayeAvec in registre.voyageAvecRegistre:
            VoyageAvec.delete_voyageAvec(persVogayeAvec.id)


        DetailRegistre.supprimer_registre(id_registre=id_registre)
        flash("Suppression de l'enregistrement réussie !", "success")
        return redirect("/personne/"+str(registre.id_personne))
    else:
        flash("Suppression échouée ! L'enregistrement n'existe pas", "warning")
        return redirect("/personne/" + str(registre.id_personne))

#############################################################################
#                             PAGES RECHERCHE DANS LA BASE                   #
#############################################################################

@appli.route("/recherche")
def recherche():
    """ Route permettant la recherche plein-texte à partir de la navbar
    """
    motcle = request.args.get("keyword", None)
    page = request.args.get("page", 1)

    if isinstance(page, str) and page.isdigit():
        page = int(page)
    else:
        page = 1

    # Création d'une liste vide de résultat (par défaut, vide si pas de mot-clé)
    resultats = []

    # cherche les mots-clés dans les champs : nom, prenom, surnom, nom en langue maternelle, pays nationalité, langue
    # occupation(s) et description
    titre = "Recherche"
    if motcle :
        resultats = db.session.query(Personne).\
            join(DetailRegistre, Personne.id == DetailRegistre.id_personne).\
            filter(db.or_(Personne.nom.like("%{}%".format(motcle)),Personne.prenom.like("%{}%".format(motcle)), DetailRegistre.professionOrigine.like("%{}%".format(motcle)) )).\
            paginate(page=page, per_page=PERSONNES_PAR_PAGES)

    # si un résultat, renvoie sur la page résultat
        titre = "Résultat de la recherche : `" + motcle + "`"
        return render_template("resultats.html", resultats=resultats, titre=titre, keyword=motcle)

#############################################################################
#                             PAGES LOGIN                                  #
#############################################################################
# on utiise GET pour acceder à la page "login" et POST pour envoyer les données de connexion
@appli.route('/login', methods=['GET', 'POST'])
def login():
    # rediriger l'utilisateur connecté vers l'index si par erreur il click sur la page de connexion
    if current_user.is_authenticated:
        return redirect(url_for('intro'))

    # on instancie la classe LoginForm pour créer un formulaire
    formulaire = LoginForm()

    # validate_on_submit est une méthode propre à la classe LoginForm;
    # dans le cas de GET, il renvoit FALSE,
    # dans le cas d'un POST, il vérifie les données saisies par l'utilisateur et si tout est correct il renvoit TRUE
    if formulaire.validate_on_submit() :

        # cherche l'utilisateur dans la base de données.
        # Le username et le password de l'utilisateur sont fournis avec le formulaire
        user = User.query.filter_by(email=formulaire.email.data).first()

        if user is None or not user.check_password(formulaire.password.data):
            flash('Invalid username or password', 'warning')
            return redirect(url_for('login'))

        # si le passw et le username sont corrects, on appelle la fonction login_user
        # qui enregistre l'utilisateur comme utilisateur connecté
        login_user(user, remember=formulaire.remember_me.data)
        session.permanent = True

        # permet de renvoyer l'utilisateur vers la première page inaccessible en tant qu'utilisateur anonyme
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('intro')
        # l'utilisateur connecté est envoyé à la page d'index
        # attention url_for prend comme paramètre le nom de la fonction, pas le paramètre de la route
        return redirect(next_page)

    return render_template('login.html', title='Connexion', form=formulaire)

"""
@appli.route('/register', methods=['GET', 'POST'])
def register():
    # rediriger l'utilisateur connecté vers l'index si par erreur il click sur la page d'eregistrement
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # on instancie la classe RegistrationForm que j'ai crée aupréalable dans forms.py
    # cette opération permet de récuperer les données saisies par l'utilisateur
    formulaire = RegistrationForm()

    # validate_on_submit est une méthode propre à la classe LoginForm;
    # dans le cas de GET, il renvoit FALSE,
    # dans le cas d'un POST, il vérifie les données saisies par l'utilisateur et si tout est correct il renvoit TRUE
    if formulaire.validate_on_submit() :

        # si le formulaire est validé, on instancie la classe User pour créer un objet user avec tous les attributs
        user = User(nom=formulaire.nom.data, prenom=formulaire.prenom.data, email=formulaire.email.data, username_geoname=formulaire.username_geoname.data)
       # le password est rajouté par le set password
        user.set_password(formulaire.password.data)
       # ajout dans la base de données des données du user
        db.session.add(user)
        db.session.commit()

        flash('Félicitation, vous êtes enregistré! Maintenant vous pouvez vous connecter.', 'success')
        return redirect(url_for('login'))


    # ça retourne une page html à laquelle on passe en paramètre pour title la valeur 'Enregistrement"
    # et pour form la valeur formulaire (qui a été instancé et rempli plus haut)
    return render_template('register.html', title='Enregistrement', form=formulaire)
"""
@appli.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('intro'))

@appli.route("/savePlace", methods=["POST"])
@login_required
def savePlace():
    """ Route permettant à l'utilisateur de créer une notice de lieu """
    #['Varsovie, Warszawa, Pologne, 1', 'Mińsk Mazowiecki, Powiat miński, Pologne, 2', 'Sétif, Algérie, 3', 'Oran, Algérie, 4']
    nouveauLieuComplet = ""
    if request.method == "POST":
        # vérifie que l'objet envoyé depuis le client est en format json
        if request.is_json:
            content = request.get_json()
            status, data = Lieu.create_lieu(
                    # récupère les valeurs de l'objet json envoyé par l'appel POST realisé en Javascript ajax.
                    nomLieuFr=content["nomLieu"],
                    pays=content["pays"],
                    region=content["region"],
                    departement= content["depart"],
                    codeINSEE=content["codeINSEE"],
                    lat=content["lat"],
                    lng=content["lng"],
                    id_geonames=content["idGeonames"]
                )

            if status is True:
                if data.nomLieuFr:
                    nouveauLieuComplet= nouveauLieuComplet + data.nomLieuFr
                if data.departement :
                    nouveauLieuComplet = nouveauLieuComplet + ", " + data.departement
                if data.pays:
                    nouveauLieuComplet = nouveauLieuComplet + ", " + data.pays
                if data.id:
                    nouveauLieuComplet = nouveauLieuComplet + ", " + str(data.id)

                succesResponse = "Création d'un nouveau lieu réussie !"

                # appelle la méthode json_response avec des parametres 201, OK, le message de succes et le nom complet du lieu
                return json_response(201,"OK", succesResponse, nouveauLieuComplet)

            else:
                # si le status est False, appelle la méthode json_response avec des parametres 202 car la requete fonctionne, mais le message KO, les messages qui indique l'echec de la creation du lieu (ex:parce que le lieu existe)
                errorResponse ="La création d'un nouveau lieu a échoué pour les raisons suivantes : " + ", ".join(data)
                return json_response(202, "KO", errorResponse, "")

        else:
            # si l'objet n'est pas en json, il retourne 404'
            return json_response(404, "KO", "la requête a échoué", "")