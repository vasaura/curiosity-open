from flask import render_template, flash, redirect, url_for, request, session, stream_with_context
from curiosity import appli, db
from curiosity.forms import LoginForm, RegistrationForm
from .constantes import PERSONNES_PAR_PAGES, LIEUX_PAR_PAGES, RESULT_PER_PAGE
from flask_login import current_user, login_user, logout_user, login_required
from curiosity.modeles.users import User, AuthorshipPersonne, AuthorshipRegistre
from curiosity.modeles.personnes_registres import Personne, Lieu, Categorie, \
    Souscategorie, DetailRegistre, LieuDeclare, \
    LienRegistresCategories, CaracteristiquePhysique, VoyageAvec, Photo
from werkzeug.urls import url_parse
from werkzeug.wrappers import Response
from sqlalchemy import func, extract
from sqlalchemy.orm import aliased
from .externalMethods.externalMethods import validate, extractLieuxComplet, \
    sortByDateEnregistrement, sortByDestination, sortByMetiers, \
    sortByPhysique, filterLieuxDeclareAvecUneNaissance, generateObjectCategorie, \
    genrateObjetLieuxDeclare, generateCompleteCSV,generateReducedCsv,\
    extractLieuxEnregistrementComplet
# librairie pour se déplacer dans les répertoires
import os

# déclaration d'une class pour utiliser ses variables et ses méthodes statiques
# classe utilisée pour améliorer les performances de chargement de la page index qui initialement faisait beaucoup de requêtes en base de donées;
# la variable statique listePersonne est vide quand on lance le serveur, elle est vidée quand on modifie la personne, quand on crée un registre, quand on supprime un registre ou une personne
class dataCache:
    listePersonnes = []
#############################################################################
#                             PAGES PRESENTATION                            #
#############################################################################

@appli.route('/')
def intro():
    personnes = Personne.query.order_by(Personne.id.desc()).all()

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
    # recupération de la liste des lieux pour assurer l'automplete dans l'input HTML des lieux. on passe le nom en français, le département, le pays et l'id du lieu
    listeNomLieu = extractLieuxComplet()
    listeNomLieuEnregistrement = extractLieuxEnregistrementComplet()
    # récupération des cotes d'archives sous la forme de tuples # résultat du type [('AM Agen 2i20',), ('AM Agen 2i19',), ('AM Agen 2i21',), ('AM Agen 2i25',), ('AM Agen 2i26',),
    listeTuplesCotes = db.session.query(DetailRegistre.cote).distinct().order_by(DetailRegistre.cote.asc()).all()
    listeCotes = []
    for nom in listeTuplesCotes:
        # récupérer uniquement le premier éléméent de la liste qui est le nom de l'archive et l'ajouter à une liste qui va etre envoyé au formulaire
        listeCotes.append(nom[0])

    # récupération de la base des types de documents
    listeTypeDocu = db.session.query(DetailRegistre.natureDoc).distinct().all()


    collector = db.session.query(DetailRegistre.collecte).distinct().all()
    # recupération de la liste des catégories professionnelles, caractéristiques physiques pour les passer dans l'input HTML dans les filtres
    categories = Categorie.query.all()

    caracteristiquesPys= db.session.query(CaracteristiquePhysique.labelCaracteristique).distinct().all()

    caracteristiquesPysiques = sorted(caracteristiquesPys, key=sortByPhysique)

    filtreTemporaire = {}

    # si la variable statique dataCache.listePersonnes est vide
    if not dataCache.listePersonnes:
        # on requete la bdd
        # résultat attendu où le nr représente le nombre de registre par personne
        # [(1, <Personne Abadi>),(2, <Personne Abadie>), (1, <Personne Abadie>), (2, <Personne Allouer>),(1, <Personne Ambroise>), (7, <Personne Ambrosini>),
        listePersonnes = db.session.query(func.count(DetailRegistre.id_personne),Personne).distinct().join(DetailRegistre, DetailRegistre.id_personne == Personne.id). \
            order_by(Personne.nom). \
            order_by(Personne.prenom). \
            group_by(Personne.id). \
            all()

        # déclare une liste de personnes qui sera envoyée au html pour générer la datatable qui récupère le résulat de query pour avoir une liste de listes
        # besoin d'obtenir cette forme pour datatable [[3138, 'Abadi', 'Jean-Jacques', 1814, 'non renseigné'], [4177, 'Abadie', 'Bernard', 1797, 'Lourde'],
        completeListWithPerson = []

        for person in listePersonnes:
            listeElement = []
            listeElement.append(person[1].id)
            listeElement.append(person[1].nom)
            if person[1].prenom:
                listeElement.append(person[1].prenom)
            else:
                listeElement.append("non renseigné")
            if person[1].anneeNaissance :
                listeElement.append(person[1].anneeNaissance)
            else:
                listeElement.append("non renseigné")
            if person[1].lieux_naissance:
                listeElement.append(person[1].lieux_naissance.nomLieuFr)
            else:
                listeElement.append("non renseigné")
            listeElement.append(person[0])
            completeListWithPerson.append(listeElement)
        # affecte à la variable statique la liste completeListWithPerson
        dataCache.listePersonnes = completeListWithPerson

    # instantiation de la variable statique listePersonnes de la class dataCache.
    # la variable listePersonnes prendra les valeurs de la variable statique affectée au préalable
    personneListe = dataCache.listePersonnes

    if request.method == "GET":
        # retourne la page html en lui passant comme paramètre titre et personnes

        return render_template('index.html', title = titre,
                               personnes= personneListe,
                               categories=categories,
                               caracteristiquesPysiques=caracteristiquesPysiques,
                               filtreTemporaire=filtreTemporaire,
                               lieux=listeNomLieu,
                               lieuxEnregistrement =listeNomLieuEnregistrement,
                               collector=collector,
                               listeTypeDocu= listeTypeDocu,
                               listeCotes=listeCotes)

    elif request.method == "POST":

        # récupérer les infos sur le sexe ex [Femme, Homme]
        filterSexe = request.form.getlist("sexe", None)
        # récupérer les infos sur la catégorie
        filtreCategorie = request.form.getlist("categorie", None)
        # récupérer les infos sur la souscatégorie
        filtreSousCategorie = request.form.getlist("souscategorie", None)
        #récupère les caractéristiques physiques
        pysique=request.form.getlist("physique", None)
        # récupère les informations pour epoux-se
        epoux = request.form.get("epoux", None)
        # récupère les informations pour enfants
        enfants = request.form.get("enfants", None)
        # récupère les informations pour le lieu de naissance
        lieuNaissanceComplet = request.form.get("bornPlace", None)
        listeLieuNaissance = lieuNaissanceComplet.split(",")
        # on récupère le dernière de la liste, l'id du lieu
        id_lieuNaissance = listeLieuNaissance[-1]

        # récupère les informations pour le lieu d'enregistrement
        lieuEnregistrementComplet = request.form.get("registerPlace", None)
        listeLieuEnregistrement = lieuEnregistrementComplet.split(",")
        # on récupère le dernière de la liste, l'id du lieu
        id_lieuEnregistrement = listeLieuEnregistrement[-1]

        # récupère les informations pour la date du début de l'enregistrement
        anneeEnregistrementDebut =  request.form.get("debut", None)

        # récupère les informations pour la date de fin de l'enregistrement
        anneeEnregistrementFin = request.form.get("fin", None)

        # on récupère l'auteur de la collecte
        auteurCollecte = request.form.get("collecte")
        # on récupère le type de document
        typeDoc = request.form.get("typedoc")
        # on récupère la cote
        cote = request.form.get("coteArchive")

        # REQUETE DE BASE les Personnes uniques
        #requête sur le model Personne et sur le nb de registre avec une jointeure dès maintenant avec detailsRegistre
        resultResearch = db.session.query(func.count(DetailRegistre.id_personne),(Personne)).distinct().join(DetailRegistre, DetailRegistre.id_personne == Personne.id)
        # déclaration des alias pour faire des jointures sur la table lieux depuis Personnes et LieuxDeclares et éviter la répetition du "from lieux" qui génère une erreur en base
        lieu1 = aliased(Lieu)
        lieu2 = aliased(Lieu)

        if filterSexe:
            filtreTemporaire["Sexe"] = filterSexe
            # on rajoute à la reqête le filtre pour le sexe avec une requête in_().
            # Cet opérateur prend en param une liste d'elements. ex: ['Femme', 'Inconnu']
            resultResearch=resultResearch.filter(Personne.sexe.in_(filterSexe))



        if lieuNaissanceComplet:
            filtreTemporaire["lieu naissance"] = lieuNaissanceComplet
            resultResearch = resultResearch.join(lieu1, lieu1.id == Personne.id_lieuxNaissance).filter(
                lieu1.id == id_lieuNaissance)

        if lieuEnregistrementComplet or anneeEnregistrementDebut or anneeEnregistrementFin:
            resultResearch = resultResearch. \
                join(LieuDeclare, DetailRegistre.id == LieuDeclare.id_registre).\
                filter(LieuDeclare.typeLieu == "Enregistrement")

            if lieuEnregistrementComplet:
                filtreTemporaire["lieu enregistrement"] = lieuEnregistrementComplet
                resultResearch = resultResearch.\
                    join(lieu2, lieu2.id == LieuDeclare.id_lieu). \
                    filter(lieu2.id == id_lieuEnregistrement)

            if anneeEnregistrementDebut and anneeEnregistrementFin:
                filtreTemporaire["Début"] = anneeEnregistrementDebut
                filtreTemporaire["Fin"] = anneeEnregistrementFin
                resultResearch = resultResearch.filter(extract('year', LieuDeclare.date) >= anneeEnregistrementDebut). \
                    filter(extract('year', LieuDeclare.date) <= anneeEnregistrementFin)

            elif anneeEnregistrementDebut :
                filtreTemporaire["Début"] = anneeEnregistrementDebut
                resultResearch = resultResearch.filter(
                    extract('year', LieuDeclare.date) >= anneeEnregistrementDebut)

            elif anneeEnregistrementFin:
                filtreTemporaire["Fin"] = anneeEnregistrementFin
                resultResearch = resultResearch.filter(extract('year', LieuDeclare.date) <= anneeEnregistrementFin)



        if auteurCollecte:
            filtreTemporaire["Auteur de la collecte"] = auteurCollecte
            resultResearch= resultResearch.filter(DetailRegistre.collecte==auteurCollecte)

        if typeDoc :
            filtreTemporaire["Type de document"] = typeDoc
            resultResearch = resultResearch.filter(DetailRegistre.natureDoc == typeDoc)

        if cote :
            filtreTemporaire["Cote d'archive"] = cote
            resultResearch = resultResearch.filter(DetailRegistre.cote == cote)

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

        if pysique:
            # la fonction in_() compare si l'élément existe dans une liste
            filtreTemporaire["Caractéristiques physiques"] = pysique
            resultResearch = resultResearch.join(CaracteristiquePhysique,
                                                 CaracteristiquePhysique.id_registre == DetailRegistre.id). \
                filter(CaracteristiquePhysique.labelCaracteristique.in_(pysique))

# CATEGORIES + SOUSCATEGORIES
        topUnionCatSoucat = False
        # si l'un des filtres relève des catégories et /ou souscategories
        if filtreCategorie or filtreSousCategorie :
            # on rajoute à la requete de base la table de jointures LienRegistresCategories
            resultResearch=resultResearch.join(LienRegistresCategories, DetailRegistre.id == LienRegistresCategories.id_registre)

            # si le filtre catégorie est coché
            if filtreCategorie:
                filtreTemporaire["categorie"] = filtreCategorie
                # on rajoute la jointure pour Categorie et la condition where avec in_()
                # Le résultat sera une addition de toutes les personnes qui sont regroupées sous les catégories mentionnées (l'equivalement de OU)
                resultSearchCat = resultResearch
                resultSearchCat = resultSearchCat.join(Categorie, LienRegistresCategories.id_categorie == Categorie.id).\
                    filter(Categorie.labelCategorie.in_(filtreCategorie)).group_by(Personne.id)

                # si filtre categorie et souscategorie ont été cochés à la fois
                if filtreSousCategorie:
                    filtreTemporaire["souscategorie"] = filtreSousCategorie
                # on construit une requête complète uniquement pour les souscategories
                    #db.session.query(func.count(DetailRegistre.id_personne),(Personne)).distinct().
                    # join(DetailRegistre, DetailRegistre.id_personne == Personne.id)
                    resultResearchSoucat= resultResearch
                    resultResearchSoucat = resultResearchSoucat.join(Souscategorie, LienRegistresCategories.id_souscategorie == Souscategorie.id). \
                        filter(Souscategorie.labelSouscategorie.in_(filtreSousCategorie)).group_by(Personne.id)

                    # on fait l'union entre les catégories et les sous-categories
                    # le résultat sera une addition de toutes les personnes qui relèvent de telle(s) catégories et les personnes qui relèvenrt de telle(s) sous-categories
                    resultResearch = resultSearchCat.union(resultResearchSoucat)
                    topUnionCatSoucat = True

                else:
                    resultResearch=resultSearchCat

            # si la soucategorie a été cochée mais pas la categorie, on rajoute à la requête de base la jointure finale pour les sous-catégories seulement
            elif filtreSousCategorie:
                filtreTemporaire["souscategorie"] = filtreSousCategorie
                resultResearch = resultResearch.join(Souscategorie, LienRegistresCategories.id_souscategorie == Souscategorie.id).\
                    filter(Souscategorie.labelSouscategorie.in_(filtreSousCategorie))

        # requête de base complétée avec order by pour calculer le nb de registre. Résultat attendu [(1, <Personne Abadi>),(2, <Personne Abadie>), (2, <Personne Allouer>), (7, <Personne Ambrosini>)]
        resultResearch = resultResearch.order_by(Personne.nom). \
            order_by(Personne.prenom)

        if topUnionCatSoucat == False:
            resultResearch=resultResearch.group_by(Personne.id)

        resultResearch=resultResearch.all()

        #si on clique sur le bouton Filter
        if request.form["submit_button"] == "filter":
            # traite la liste de type de document envoyée au html pour ne pas retrouner le type de document séléctionné
            if typeDoc :
                for tuple in listeTypeDocu:
                    if tuple[0] == typeDoc:
                        listeTypeDocu.remove(tuple)
            # traite la liste de collecte envoyée au html pour ne pas retrouner la personne séléctionnée
            if auteurCollecte:
                for tuple in collector:
                    if tuple[0] == auteurCollecte:
                        collector.remove(tuple)

            personneListe = []

            for person in resultResearch:
                listeElement = []
                listeElement.append(person[1].id)
                listeElement.append(person[1].nom)
                if person[1].prenom:
                    listeElement.append(person[1].prenom)
                else:
                    listeElement.append("non renseigné")
                if person[1].anneeNaissance :
                    listeElement.append(person[1].anneeNaissance)
                else:
                    listeElement.append("non renseigné")
                if person[1].lieux_naissance:
                    listeElement.append(person[1].lieux_naissance.nomLieuFr)
                else:
                    listeElement.append("non renseigné")
                listeElement.append(person[0])
                personneListe.append(listeElement)

            return render_template('index.html',
                                   title=titre,
                                   personnes=personneListe,
                                   categories=categories,
                                   caracteristiquesPysiques=caracteristiquesPysiques,
                                   filtreTemporaire=filtreTemporaire,
                                   lieux=listeNomLieu,
                                   lieuxEnregistrement =listeNomLieuEnregistrement,
                                   collector=collector,
                                   listeTypeDocu=listeTypeDocu,
                                   listeCotes=listeCotes
                                   )

        # si on clique sur le bouton Télecharger
        elif request.form["submit_button"] == "download":
            # resultResearch prend la forme [<Personne Lalun>, <Personne Lafargue>, <Personne Bertani>, <Personne Bouthor>, <Personne Calpe>,...]
            outputdata = request.form.get ("outputdata", None)

            if outputdata == "dcomplet" :

                # stream the response as the data is generated. Appel de la méthode generateCompleteCSV
                response = Response(stream_with_context(generateCompleteCSV(resultResearch)), mimetype='text/csv')
                # add a filename
                # add a filename
                response.headers['Content-Disposition'] = 'attachment; filename={}'.format('extractionCuriosites.csv')
                return response

            if outputdata=="dreduit":
                # on declare une liste rows

                # stream the response as the data is generated. Appel de la méthode generateReducedCsv
                response = Response(stream_with_context(generateReducedCsv(resultResearch, cote)),  mimetype='text/csv')
                # add a filename
                response.headers['Content-Disposition'] = 'attachment; filename={}'.format('extractionCuriosites.csv')
                return response

        elif request.form["submit_button"] == "reset":
            # instantiation de la variable statique listePersonnes de la class dataCache.
            # la variable listePersonnes prendra les valeurs de la variable statique affectée au préalable
            personneListe = dataCache.listePersonnes


    return render_template('index.html', title=titre,
                                       personnes=personneListe,
                                       categories=categories,
                                       caracteristiquesPysiques=caracteristiquesPysiques,
                                       filtreTemporaire=filtreTemporaire,
                                       lieux=listeNomLieu,
                                        lieuxEnregistrement =listeNomLieuEnregistrement,
                                       collector=collector,
                                       listeTypeDocu=listeTypeDocu,
                                       listeCotes=listeCotes
                                  )


@appli.route('/personne/<int:identifier>')
def notice (identifier):
    titre = "Notice personne"
    # instanciation d'un objet personne avec un identifiant personne
    personneUnique = Personne.query.get(identifier)
    listePhysiqueNotice=[]
    listeProfessionOrigineNotice = []

    if personneUnique:
        # instanciation d'un objet DetailRegistre (qui contient tous les attributs de la classe)
        # résultat du type: [<DetailRegistre 872>, <DetailRegistre 953>, <DetailRegistre 1004>, <DetailRegistre 1736>, <DetailRegistre 4196>]
        # Sorte la liste des registre par date en ordre chronologique
        listeDetailsRegistres = sorted(personneUnique.registresPers, key=sortByDateEnregistrement)


        for registre in listeDetailsRegistres:
            # on change l'ordre des éléments dans les lieux declarés pour les afficher dans un ordre logique: Naissance, Domicile, délivrance du passeport, dernier passage, visa
            # (à l'aide de la methode sortByDestination créée auparavant) et on fait une réafectation de l'attribut lieuxDeclares de l'objet DetailRegistre
            # utilisation de la fonction sorted qui prend comme paramètres une liste et le nom d'une fonction (!! ce n'est pas un appel de fonction)
            registre.lieuxDeclares = sorted(registre.lieuxDeclares, key=sortByDestination)
            #Ajoute à une liste le contenu du champ caracteristiquesPhysiques et professionOrigine
            listePhysiqueNotice.append(registre.caracteristiquesPhysiques)
            listeProfessionOrigineNotice.append(registre.professionOrigine)
        #rend uniques les éléments contenu dans les listes
        listeProfessionUnique=set(listeProfessionOrigineNotice)
        listePhysiqueUnique = set(listePhysiqueNotice)

        return render_template("notice.html",
                               title=titre,
                               unique=personneUnique,
                               detailsRegistres=listeDetailsRegistres,
                               listeProfessionUnique=listeProfessionUnique,
                               listePhysiqueUnique=listePhysiqueUnique)

    else:
        flash("La personne que vous cherchez n'existe pas", "warning")
        return redirect("/index")

@appli.route('/registre/<int:identifier_registre>')
def registre (identifier_registre):
    titre = "Enregistrement"
    # instanciation d'un objet personne avec un identifiant personne
    registreUnique = DetailRegistre.query.get(identifier_registre)

    if registreUnique:

        return render_template("registre.html",
                               title=titre,
                               registreUnique=registreUnique,
                               code="display")

    else:
        flash("L'enregistrement que vous cherchez n'existe pas", "warning")
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
    nombrePersParCat = db.session.query(func.count((Personne.id).distinct()),Categorie). \
                                        filter(DetailRegistre.id_personne == Personne.id). \
                                        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
                                        filter(LienRegistresCategories.id_categorie == Categorie.id). \
                                        group_by(Categorie).order_by (Categorie.labelCategorie.asc()).all()

    # requete qui permet de regrouper le nombre de personnes par sous-catégorie de métier dans une liste de tuple comme ici:
    # [(89, <Souscategorie animaux savants>), (21, <Souscategorie artificier>), (205, <Souscategorie chanteur>), (14, <Souscategorie combat d'animaux>),(...)]
    nombrePersParSousCat = db.session.query(func.count((Personne.id).distinct()),Souscategorie). \
                                        filter(DetailRegistre.id_personne == Personne.id). \
                                        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
                                        filter(LienRegistresCategories.id_souscategorie == Souscategorie.id). \
                                        group_by(Souscategorie).all()

    # Requeête avec left join pour récupérer les métiers déclarés et les catégories et les souscatégories associés.
    # utilise les db.relationships pour le join (LienRegistresCategories.souscategories)
    # resultat du type liste = [(2, "brassier et joueur de vielle", "autres metiers", None), (3, "chanteur de place", "spectacle musical", "chanteur")]
    countMetiersDeclares = db.session.query(func.count(DetailRegistre.id_personne.distinct()),DetailRegistre.professionOrigine, Categorie.labelCategorie,
                                        Souscategorie.labelSouscategorie). \
        join(Souscategorie, LienRegistresCategories.souscategories, isouter=True). \
        filter(LienRegistresCategories.id_registre == DetailRegistre.id). \
        filter(Categorie.id == LienRegistresCategories.id_categorie). \
        group_by(DetailRegistre.professionOrigine, Categorie.labelCategorie,
                                        Souscategorie.labelSouscategorie). order_by(Categorie.labelCategorie.asc()).\
        all()

    # on trie la liste pour afficher à la fin: "autres metiers", "indétérminé" et "domestique"
    countMetiersDeclares = sorted(countMetiersDeclares, key=sortByMetiers)

    totalCategoriesSousCatmetier={}
    boolSouscat=False
    boolCat=False

    for element in countMetiersDeclares:
        metier={}
        #ajoute au traitement uniquement les cas où le metiers déclaré a été saisi ainsi également la catégorie
        if element[1] and element[2]:
            metier[element[1]]=element[0]
            for objetCategorie in nombrePersParCat:
                if objetCategorie[1].labelCategorie == element[2]:
                    boolCat = True
                    # si le dictionnaire n'existe pas ou que la catégorie n'existe pas dans le dictionnaire,
                    # on ajoute la clé de la catégorie pour créer le dictionnaires
                    if not totalCategoriesSousCatmetier or element[2] not in totalCategoriesSousCatmetier:
                        totalCategoriesSousCatmetier[element[2]] = {"nbPersCat": objetCategorie[0],
                                                                    "idCat": objetCategorie[1].id,
                                                                    "souscategories": {}, "metiers": {}}
                    # si le dictionnaire ou la catégorie existent
                    else:
                        # si le tuple contient une souscategorie
                        if element[3]:
                            for objetsSoucategorie in nombrePersParSousCat:
                                if objetsSoucategorie[1].labelSouscategorie == element[3]:
                                    boolSouscat = True
                                    souscategorie = {}
                                    # si la souscategorie n'existe pas on la crée avec le premier dictionnaire de metiers
                                    if element[3] not in totalCategoriesSousCatmetier[element[2]]["souscategories"]:
                                        souscategorie[element[3]] = {"nbPersSouscat":objetsSoucategorie[0],
                                                                     "idSouscat":objetsSoucategorie[1].id,
                                                                     "metiers":metier}
                                        totalCategoriesSousCatmetier[element[2]]["souscategories"].update(souscategorie)
                                    else:
                                        totalCategoriesSousCatmetier[element[2]]["souscategories"][element[3]]["metiers"].update(metier)

                                elif boolSouscat == True:
                                    boolSouscat = False
                                    break
                        # sinon si element[3] n'existe pas (aka la souscategorie est none)
                        else:
                            # si le dictionnaire n'existe pas,ou que la catégorie n'existe pas on ajoute la clé de la catégorie pour créer le dictionnaires, la souscatégorie
                            if element[2] not in totalCategoriesSousCatmetier:
                                totalCategoriesSousCatmetier[element[2]] = {"nbPersCat": objetCategorie[0],
                                                                            "idCat": objetCategorie[1].id,
                                                                            "souscategories": {}, "metiers":metier }
                            # si le dictionnaire existe et qu'il contient la clé de la catégorie, on fait un update de la souscatégorie
                            elif element[2] in totalCategoriesSousCatmetier:
                                totalCategoriesSousCatmetier[element[2]]["metiers"].update(metier)
                elif boolCat==True:
                    boolCat= False
                    break


    return render_template('catProfession.html', title = titre,
                           totalCategoriesSousCatmetier=totalCategoriesSousCatmetier)

@appli.route("/graphiques")
def graphique():
    titre="Graphiques"

    # requete qui permet de regrouper le nombre de personnes par catégorie de métier par ordre aphabétique dans une liste de tuples comme ici:
    # [(295, <Catégorie professionnelle: acrobatie>), (128, <Catégorie professionnelle: autres metiers>), (2, <Catégorie professionnelle: aérostatier>),,(...)]
    nombrePersParCat = db.session.query(func.count((Personne.id).distinct()),
                                        Categorie). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
        filter(LienRegistresCategories.id_categorie == Categorie.id). \
        group_by(Categorie).order_by (Categorie.labelCategorie.asc()).all()

    # requete qui permet de regrouper le nombre de personnes par sous-catégorie de métier dans une liste de tuple comme ici:
    # [(89, <Souscategorie animaux savants>), (21, <Souscategorie artificier>), (205, <Souscategorie chanteur>), (14, <Souscategorie combat d'animaux>),(...)]
    nombrePersParSousCat = db.session.query(func.count((Personne.id).distinct()),
                                            Souscategorie). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.id == LienRegistresCategories.id_registre). \
        filter(LienRegistresCategories.id_souscategorie == Souscategorie.id). \
        group_by(Souscategorie).all()

    # données nécessaires pour la bib chart de JS qui est une liste de dictionnaires
    totalData = []

    for categorie in nombrePersParCat:
        dicoCategorie = {}
        dicoCategorie["name"] = categorie[1].labelCategorie
        dicoCategorie["children"] = []
        if categorie[1].souscategories:
            for tupleSouscategorie in nombrePersParSousCat:
                if tupleSouscategorie[1].categories.labelCategorie == categorie[1].labelCategorie:
                    dictionnaireSousCategorie = {}
                    dictionnaireSousCategorie["name"] = tupleSouscategorie[1].labelSouscategorie
                    dictionnaireSousCategorie["value"] = tupleSouscategorie[0]
                    dicoCategorie["children"].append(dictionnaireSousCategorie)
            totalData.append(dicoCategorie)
        else:
            dictionnaireCategorie = {}
            dictionnaireCategorie["name"] = categorie[1].labelCategorie
            dictionnaireCategorie["value"] = categorie[0]
            dicoCategorie["children"].append(dictionnaireCategorie)
            totalData.append(dicoCategorie)

    return render_template("graphic.html", title = titre, nombrePersParCat = nombrePersParCat, nombrePersParSousCat = nombrePersParSousCat, totalData=totalData)


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
        return render_template('pers-Categ.html', title = "personne par categorie", personnes = personneCat, categorie = categorie)

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

    return render_template('pers-sousCateg.html', title='personnes par sous-categorie', personnes = personneSoucatCat, soucategorie = soucategorie)

@appli.route('/personnes-par-metier-declare/<label>')
def persParMetiersDeclare(label):
    page = request.args.get("page", 1, type=int)
    # resultat : une liste du type [(1398, 'Bara', 'Jean-François-Joseph'), (2145, 'Brugoni', 'Antoine'), (1777, 'Brumini', 'Antoine')

    personneParMetier = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.professionOrigine == label). \
        order_by(Personne.nom.asc()). \
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)

    return render_template('persMetierDeclare.html', title="personnes par métier déclaré",
                           label=label,
                           personnes=personneParMetier)


@appli.route('/accompagne-par-epoux-se')
#la page avec la liste des personnes accompagnés par l'époux
def persEpoux():

    page = request.args.get("page", 1, type=int)

    personneAvecEpoux = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.epoux == 1). \
        order_by(Personne.nom.asc()). \
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)
    return render_template("pers-epoux.html", title = "personnes accompagnées par epoux-se", personnes=personneAvecEpoux )

@appli.route('/accompagne-par-enfant')
#la page avec la liste des personnes accompagnés par les enfants
def persEnfant():

    page = request.args.get("page", 1, type=int)

    personneAvecEnfant = db.session.query((Personne.id).distinct(), Personne.nom, Personne.prenom). \
        filter(DetailRegistre.id_personne == Personne.id). \
        filter(DetailRegistre.nbEnfants != None). \
        order_by(Personne.nom.asc()). \
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)
    return render_template("pers-par-enfant.html", title = "personnes accompagnées par enfants", personnes=personneAvecEnfant)

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

    return render_template('pers-Caracteristiques.html',
                           title ="personnes par caractéristique physique",
                           label=label,
                           personnes=personneCaracteristique)

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

    return render_template("pers-par-passage.html", title = "personnes par ville d'enregistrement", personnes=persParPassage, villePassage=villePassage )

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

    return render_template("pers-par-naissance.html", title = "personnes par ville de naissance", personnes=persParNaissance, villeNaissance=villeNaissance)

@appli.route('/tableau-prefessions')
@login_required
def glossaire():
    #Requeête avec left join pour récupérer les métiers déclarés et les catégories et les souscatégories associés.
    # utilise les db.relationships pour le join (LienRegistresCategories.souscategories)
    # résultat du type [("artiste d'agilité", 'acrobatie', "voltigeur / artiste d'agilité"), ('acrobatie 2 petites personnes nain', 'acrobatie', None) ('artiste acrobate', 'acrobatie', None)],
    glossaireMetiers = db.session.query((DetailRegistre.professionOrigine).distinct(),Categorie.labelCategorie, Souscategorie.labelSouscategorie) .\
        join(Souscategorie, LienRegistresCategories.souscategories, isouter=True).\
        filter(LienRegistresCategories.id_registre==DetailRegistre.id).\
        filter(Categorie.id==LienRegistresCategories.id_categorie). \
        all()

    return render_template('glossaire.html', title="Glossaire de métiers", glossaireMetiers=glossaireMetiers)

@appli.route('/photos-manquantes')
@login_required
def displayPhotos():

    listePhotosRegistreBDD =[]

    photos = Photo.query.all()
    for eachPhoto in photos:
        if eachPhoto.label_photo == None:
            pass
        elif eachPhoto.label_photo == "None":
            pass
        elif eachPhoto.label_photo == "":
            pass
        else:
            #on ajoute à la liste le label de la photo et le id du registre
            listePhotoRegistre=[]
            formatPhoto = eachPhoto.label_photo + ".jpg"
            listePhotoRegistre.append(formatPhoto)
            listePhotoRegistre.append(eachPhoto.id_registre)
            # on ajoute la liste avec un label photo et un iod de registre à la liste globale
            listePhotosRegistreBDD.append(listePhotoRegistre)

    differenceBDD_Folder = []
    photosRepertoire = os.listdir("./curiosity/static/images/Photos_BDD/")

    for couplePhotoRegistre in listePhotosRegistreBDD:
        #si le label photo existe dans la liste des photos du repertoire
        if couplePhotoRegistre[0] in photosRepertoire:
            # on passe
            pass
        #sinon on ajoute le couple photo-idregistre à la liste de différence
        else:
            differenceBDD_Folder.append(couplePhotoRegistre)


    return render_template("photos-manque.html", title="Photos manquantes", differenceBDD_Folder=differenceBDD_Folder)

@appli.route('/archives')
def archives():
    archives = db.session.query(DetailRegistre.nomArchive.distinct()). order_by(DetailRegistre.nomArchive.asc())
    return render_template("archives.html", title="Archives", archives=archives)

@appli.route('/cotes')
def cotes():
    cotes = db.session.query(DetailRegistre.cote.distinct()).order_by(DetailRegistre.cote.asc())
    return render_template("cotes.html", title ="Cotes", cotes=cotes)

@appli.route('/pers-par-archives/<nom_archive>')
def persParArchives(nom_archive):
    page = request.args.get("page", 1, type=int)
    persArchives = db.session.query(Personne.id.distinct(), Personne.nom, Personne.prenom). \
        join(DetailRegistre, Personne.id == DetailRegistre.id_personne). \
        filter(DetailRegistre.nomArchive == nom_archive).\
        order_by(Personne.nom.asc()). \
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)
    return render_template("pers-par-archives.html", title = "personnes par archives", personnes=persArchives, nom_archive=nom_archive)

@appli.route('/registre-par-cote/<cote_archive>')
def registreParCote(cote_archive):
    page = request.args.get("page", 1, type=int)

    registreCote = db.session.query(DetailRegistre).\
        filter(DetailRegistre.cote == cote_archive).\
        order_by(DetailRegistre.nomOrigine).\
        paginate(page=page, per_page=PERSONNES_PAR_PAGES)

    return render_template("registre-par-cote.html", title="registre par cote", personnes=registreCote, cote_archive=cote_archive)


@appli.route("/date-lieu-registre",methods=["GET", "POST"])
@login_required
def registerPerDatePlace():

    outputListeDateLieuRegistre=[]

    resultDatelieuxEnregistrement = db.session.query((LieuDeclare.date).distinct(), Lieu.nomLieuFr, DetailRegistre).\
        filter(LieuDeclare.typeLieu=="Enregistrement").\
        filter(Lieu.id==LieuDeclare.id_lieu).\
        filter(DetailRegistre.id==LieuDeclare.id_registre).\
        order_by(LieuDeclare.date.asc()).all()

    for eachDateLieuRegistre in resultDatelieuxEnregistrement:
        boolExist = False
        for element in outputListeDateLieuRegistre:
            if eachDateLieuRegistre[0] == element[0] and eachDateLieuRegistre[1]==element[1] :
                boolExist = True
                element[2].append(eachDateLieuRegistre[2])
                break
        if boolExist == False:
            outputListeDateLieuRegistre.append([eachDateLieuRegistre[0], eachDateLieuRegistre[1], [eachDateLieuRegistre[2]]])

    if request.method == "POST":
        # récupérer les id des registre des personnes
        voyageEnsemble = request.form.getlist("persdeclares", None)




    return render_template("date-lieu-registre.html", title="Date et lieu d'enregistrement", outputListeDateLieuRegistre=outputListeDateLieuRegistre)

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


        listeAuthorshipPers =[]
        # users
        if current_user.is_authenticated:
            # cherche l'utilisateur dans la base de données.
            # Le username et le password de l'utilisateur sont fournis avec le formulaire
            userID = current_user.get_id()

            authorshipPers = AuthorshipPersonne(user_id=userID, role="creator")
            listeAuthorshipPers.append(authorshipPers)

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
                certitudeNP=certitudeNP,
                authorshipPers=listeAuthorshipPers
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

        listeAuthorshipPers = []
        # users
        if current_user.is_authenticated:
            # cherche l'utilisateur dans la base de données.
            # Le username et le password de l'utilisateur sont fournis avec le formulaire
            userID = current_user.get_id()

            authorshipPers = AuthorshipPersonne(user_id=userID, role="contributor")
            listeAuthorshipPers.append(authorshipPers)

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
            certitudeNP=request.form.get("certitude", None),
            authorshipPers=listeAuthorshipPers
        )
        if status is True:
            flash("Modification de personne réussie !", "success")

            # initialise à vide la variable statique de la class dataCache pour relancer la requête en bdd lors de l'appel de la route index.
            #cela permet de mettre à jours les éléments de description de la personne dans l'index.
            dataCache.listePersonnes = []

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
            lat=request.form.get("latitude", None),
            lng=request.form.get("longitude", None),
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
    Methoide permettant de créer un nouiveau registre pour la personne avec l'identifiant idPersonne
    :param idPersonne: int. identifiant de la personne à laquelle sera rattaché le registre
    :return:
    """
    personneUnique = Personne.query.get(idPersonne)
    registreTemporaire = {}

    #############################################################################
    #   Requête dans la base pour récupèrer des informations à passer au html   #
    #############################################################################

    # l'appel de la fonciton extractLieuxCompletpour recupérer la liste des lieux normalisés pour assurer l'automplete dans l'input HTML des lieux.
    # on passe le nom en français, le département, le pays et l'id du lieu
    listeNomLieu = extractLieuxComplet()

    # recupération de la liste des catégories professionnemmes et des caractéristiques physiques pour les passer dans l'input HTML à la création du métier
    categories = Categorie.query.all()
    caracteristiquesPys = db.session.query(CaracteristiquePhysique.labelCaracteristique).distinct().all()
    caracteristiquesPysiques = sorted(caracteristiquesPys, key=sortByPhysique)

    # Si un utilisateur est connecté
    if current_user.is_authenticated:
        # retourne l'id de l'utilisateur connecté
        userID = current_user.get_id()

        #le dernier registre créé par l'utilisateur connecté
        lastRecord = db.session.query(DetailRegistre).join(AuthorshipRegistre, DetailRegistre.id== AuthorshipRegistre.registre_id)\
            .join(User, User.id==AuthorshipRegistre.user_id)\
            .filter(User.id==userID)\
            .order_by(DetailRegistre.id.desc()).first()

    listeTypeDocument=[]
    typeDocument= db.session.query(DetailRegistre.natureDoc).distinct().all()
    for typeDoc in typeDocument:
            if typeDoc[0] is not None:
                listeTypeDocument.append(typeDoc[0])
    # listes des métiers fréquents à insérer automatiquement dans les formulaires pour éviter de les saisir à la main.
    # 1er mot= le mot trouvé dans les archives, 2e mot= catégorie, 3e mot sous-catégorie si elle existe
    listeMetiersCourants = [
        ["acrobate","acrobatie"],
        ["artiste d'agilité","acrobatie","voltigeur / artiste d'agilité"],
        ["chanteur","spectacle musical","chanteur"],
        ["chanteur ambulant","spectacle musical","chanteur"],
        ["conducteur d'animaux","monstration d'animaux","indéterminé"],
        ["écuyer","monstration d'animaux","équitation"],
        ["figuriste","monstration de cires / plâtres / bois"],
        ["joueur d'instrument","spectacle musical","musicien"],
        ["joueur d'orgue","joueur / porteur d'orgue"],
        ["joueur de vielle","spectacle musical","musicien"],
        ["joueur de violon","spectacle musical","musicien"],
        ["marchand de cantiques","spectacle musical","marchand de chansons"],
        ["marchand de chansons","spectacle musical","marchand de chansons"],
        ["marchand de complaintes","spectacle musical","marchand de chansons"],
        ["marchand d'estampes","monstration d'images"],
        ["marchand d'images","monstration d'images"],
        ["musicien","spectacle musical","musicien"],
        ["musicien ambulant","spectacle musical","musicien"],
        ["physicien","spectacle d'illusion", "physicien"],
        ["porteur d'orgue","joueur / porteur d'orgue"],
        ["saltimbanque","saltimbanque"],
        ["voltigeur","acrobatie","voltigeur / artiste d'agilité"]]

    # on fournit la liste en dur avec les types de lieux
    listeTypeLieux = ["Naissance", "Domicile", "Délivrance du passeport", "Dernier Passage", "Destination", "Visa",
                      "Décès"]

    # on fournit une liste (extraction depuis la bdd) avec le nom des archives pour l'autocomplete.
    # résultat du type [('AGEN-Archives municipales ',), ('LYON-Archives municipales ',), ('ALBI-Archives municipales ',) ('COSNE-Archives municipales ',),('SAINT-ETIENNE-Archives municipales',), ('CHALON-Archives municipales ',), ('BOURG-Archives municipales ',), ('BEAUNE-Archives municipales ',)]
    nomsArchive = db.session.query(DetailRegistre.nomArchive).distinct().all()
    listeNomsArchive = []
    for nom in nomsArchive:
        #récupérer uniquement le premier éléméent de la liste qui est le nom de l'archive et l'ajouter à une liste qui va etre envoyé au formulaire
        listeNomsArchive.append(nom[0])

    ######################################################################################
    #  Methode GET: renvoie les informations uniques de la personne dans le formulaire   #
    ######################################################################################

    if request.method == "GET":
        return render_template("creer_registre.html",
                               personneUnique=personneUnique,
                               lieux=listeNomLieu,
                               categories=categories,
                               typeDocument=listeTypeDocument,
                               listeNomsArchive=listeNomsArchive,
                               registreTemporaire=registreTemporaire,
                               listeTypeLieux=listeTypeLieux,
                               listeMetiersCourants=listeMetiersCourants,
                               lastRecord=lastRecord,
                               caracteristiquesPysiques=caracteristiquesPysiques)

    ######################################################################################
    #      Méthode POST: récupère les informations saisies pour chaque régistre         #
    ######################################################################################

    elif request.method == "POST":
        erreurs = []
        listeObjet_lieuDeclare = []
        listeObjetsMetiers =[]
        listeObjetCaracteristiques = []
        listeObjetsVoyageAvec =[]
        listeObjetsPhotos =[]

        # ----- RECUPERATION DES VALEURS DU FORMULAIRE HTML ----##

        #NOM+Prenom+taille+professionOrigine+dureeSejour+description+accompagnePar+caracteristiquesPhysiques+autresCaracteristiques
        nomOrigineForm = request.form.get("nom", None)
        prenomOrigineForm = request.form.get("prenom", None)

        if nomOrigineForm == "" and prenomOrigineForm == "" :
            nomOrigine = personneUnique.nom
            prenomOrigine = personneUnique.prenom
        else:
            nomOrigine = nomOrigineForm
            prenomOrigine = prenomOrigineForm


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
        collecte = request.form.get("collecte", None)

        if nomArchive == '':
            erreurs.append("Le nom de l'institution d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Ajouter les sources d'archives'")
        cote = request.form.get("cote", None)

        if cote == '':
            erreurs.append(
                "La côte d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Ajouter les sources d'archives'")

        natureDoc = request.form.get("typeDoc", None)

        nrOrdre = request.form.get("ordre", None)

        commentaires = request.form.get("commentaires", None)

        # recupération checkbox
        epoux = request.form.get("epoux", None)  # récupère la valeur de l'attribut value

        #récupération liste, objets complexes
        listePhotoArchive = request.form.getlist("photo", None)

        lieuEnregistrementComplet = request.form.get("lieuPassage", None)
        dateEnregistremnt = request.form.get("datePassage", None)

        # recupère une liste avec tous les labels des lieux déclarés
        listeLabelLieuDeclare = request.form.getlist("listeLieuDeclare", None)
        # recupère une liste avec tous les lieux normalisés
        labelLieuNormaliseHtml = request.form.getlist("listeLieuNormal", None)

        # récupère une liste avec toutes les dates
        listeDate = request.form.getlist("listeDates", None)
        for i in range(0, len(listeDate)):
            # si les dates sont saisies
            if listeDate[i] != "":
                # vérifie le format des dates
                formatStatusDate = validate(listeDate[i])
                # si le format est invalide, renvoie une erreur
                if formatStatusDate == False:
                    erreurs.append(
                        "Format de date incorrect. Resaisir selon le modèle JJ-MM-AAAA dans 'Ajouter les lieux et les dates de passage de la personne'")
                # sinon on change pas la liste
                else:
                    listeDate = listeDate
            else:
                listeDate = listeDate

        # récupère une liste avec tous les types de lieux
        listeTypeLieu = request.form.getlist("listeTypeLieu", None)

        # récupération d'une liste avec tous les identifiants des personnes qui voyagent avec la personne du registre
        listePersonnesAccompagnantes = request.form.getlist("voyageAvecIdPers", None)

        # récupere les categories et les souscategories déclarés
        listeCategories = request.form.getlist("cat", None)
        listeSoucategories = request.form.getlist("sousCat", None)

        # récupere les metiers, les categories et les souscategories fréquents
        listeMetiersFrequent = request.form.getlist("metierFrequent", None)
        listeCatFrequent = request.form.getlist("categorieFrequente", None)
        listeSoucatFrequent = request.form.getlist("souscategorieFrequente", None)
        # récupérer les caracteristiques physiques
        listePhysique = request.form.getlist("physique", None)


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

        # on déclare une liste vide qui récupère toutes les listes qui regroupe des categories et des sous-categories. exemple <class 'list'>: [['acrobatie', 'jongleur'], ['acrobatie', 'sauteur/danseur'],]
        listeGlobaleTemporaireCatSoucat = []

        if len(listeSoucategories) != len(listeCategories):
            erreurs.append(
                "Veuillez vérifier les categories et les sous-categories de métiers que vous avez selectionnées")
        else:
            # boucke sur la taille de la liste. définit la taille de la liste listeCategories
            for i in range(0, len(listeCategories)):
                # déclare une liste pour un seul regroupement qui comprend une catégorie et une sous-catégorie
                listeTemporaireCatSoucat = []
                listeTemporaireCatSoucat.append(listeCategories[i])
                listeTemporaireCatSoucat.append(listeSoucategories[i])
                # on ajoute la liste à la liste globale
                listeGlobaleTemporaireCatSoucat.append(listeTemporaireCatSoucat)

        # on déclare une liste vide qui récupère toutes les listes qui regroupe metiers, categories et sous-categories fréquent
        #  exemple <class 'list'>:[['Musicien', 'spectacle musical', 'musicien'], ['Voltigeur', 'acrobatie', "voltigeur / artiste d'agilité"], ['Figuriste', 'monstration de cires / plâtres / bois', '']]
        listeGlobaleTemporaireMetierCatSoucat = []
        for i in range (0, len(listeMetiersFrequent)):
            listeTemporaireMetierCatSoucat =[]
            listeTemporaireMetierCatSoucat.append(listeMetiersFrequent[i])
            listeTemporaireMetierCatSoucat.append(listeCatFrequent[i])
            listeTemporaireMetierCatSoucat.append(listeSoucatFrequent[i])
            listeGlobaleTemporaireMetierCatSoucat.append(listeTemporaireMetierCatSoucat)

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
        registreTemporaire["commentaires"] = commentaires
        registreTemporaire["lieuPassage"] = lieuEnregistrementComplet
        registreTemporaire["dateEnregistremnt"] = dateEnregistremnt
        # ajoute au dictionnaire la liste des photos
        registreTemporaire["photoArchive"] = listePhotoArchive
        # ajoute au dictionnaire la liste gloable des lieux déclarés
        registreTemporaire["lieuxDeclares"] = listeGlobaleTemporaireLieuxD
        # ajoute au dictionnaire la liste des identifiants des personnes qui voyagent avec le registre
        registreTemporaire["voyageAvec"] = listePersonnesAccompagnantes
        # ajoute au dictionnaire une liste qui contient des listes avec une categorie et une sous-categorie
        registreTemporaire["catSoucat"] = listeGlobaleTemporaireCatSoucat
        # ajoute au dictionnaire la liste des listes des metiers categories, souscategories fréquent
        registreTemporaire["metiersCatSoucatFrequent"] = listeGlobaleTemporaireMetierCatSoucat
        #ajoute au dictionnaire la liste des caractéristiques physiques normalisées
        registreTemporaire["physiqueNormalise"] = listePhysique


 #--------LIEUX DECLARES--------#
        # transforme le str du lieu de passage (enregistrement) en liste et récupère uniquement l'id (le dernier élément de la liste)
        lieuEnregistrementListe = lieuEnregistrementComplet.split(",")
        id_lieuPassage = lieuEnregistrementListe[-1]
        #crée un objet lieu décalré pour l'enregistrement
        lieuEnregistrement = LieuDeclare(
            labelLieuDeclare=lieuEnregistrementListe[0],
            id_lieu=id_lieuPassage,
            date=dateEnregistremnt,
            typeLieu="Enregistrement")

        # on ajoute l'objet lieuEnregistrement à la liste d'objets déclarés
        listeObjet_lieuDeclare.append(lieuEnregistrement)

        # utilisation de la méthode genrateObjetLieuxDeclare pour créer des objets Lieux déclarés pour les autres lieux
        genrateObjetLieuxDeclare(labelLieuNormaliseHtml, listeDate, listeLabelLieuDeclare, listeObjet_lieuDeclare,
                                 listeTypeLieu)

#--------- ANNEES NAISSANCE CALCULEE, VOYAGE AVEC, PHOTOS, EPOUX  -------#

        if agePersonne and dateEnregistremnt:
            anneeNaissCalcule = int(dateEnregistremnt.split("-")[0]) - int(agePersonne)
        else:
            anneeNaissCalcule = None

        if listePersonnesAccompagnantes:
            for idPersonneAccompagnante in listePersonnesAccompagnantes :
                personneCompagne = Personne.query.get(idPersonneAccompagnante)
                if personneCompagne:
                    # utilisation de la mérthode generateObjectVoyageAvec pour créer des objects voyageAvec
                    objectVoyageAvec = VoyageAvec(id_personne=personneCompagne.id)
                    listeObjetsVoyageAvec.append(objectVoyageAvec)

                else:
                    erreurs.append(
                        "L'un des identifiants des compagnons de la personne n'existe pas. Vérifier la rubrique 'Ajouter des éléments sur les personnes d'accompagnement' ")

        if listePhotoArchive:
            for photo in listePhotoArchive:
                # pour chaque nom de photo de la liste, on crée un objet Photo et on le rajoute à la liste d'objets photos
                objetPhoto = Photo(label_photo=photo)
                listeObjetsPhotos.append(objetPhoto)

        if epoux=="on":
            epoux=1
        else:
            epoux=0

        # ------ CARACTERISTIUQES PHYSIQUES------##
        if listePhysique:
            for physique in listePhysique:
                objetPhysique = CaracteristiquePhysique(labelCaracteristique=physique)
                listeObjetCaracteristiques.append(objetPhysique)

        # si le champs caractéristiques physiques déclarés n'est pas saisi on enregistre dans la base la valeur de car phys normalisées
        if caracteristiquesPhysiques == "" and listePhysique:
            caracteristiquesPhysiques = ", ".join(listePhysique)


        # ----- METIERS FREQUENTS --------##

        labelMetierFrequent=""
        #reprend le label des metiers fréquents pour les traiter séparément sous la forme d'une str, la concaténer avec le metier déclarés pour l'enregistre dans un seul champs
        for metierFrequent in listeMetiersFrequent:
            if labelMetierFrequent != "":
                labelMetierFrequent = labelMetierFrequent + ", " + metierFrequent
            else:
                labelMetierFrequent = metierFrequent

        # ----- Profession d'origine: variations --------##
        #si le metier fréquent et professionOrigine existent il faut contactener les deux avec le point (.) comme séparateur
        if labelMetierFrequent != "" and professionOrigine != "":
            professionOrigine = labelMetierFrequent + ", " + professionOrigine
        elif labelMetierFrequent != "":
            professionOrigine = labelMetierFrequent
        else:
            professionOrigine=professionOrigine


        #les catégories fréquentes
        for i, categorieFrequent in enumerate(listeCatFrequent):
            if categorieFrequent != "":
                objectCategorieFrec = Categorie.query.filter_by(labelCategorie=categorieFrequent).first()
                # remplace le label de la categorie par l'id
                listeCatFrequent[i] = objectCategorieFrec.id

        #les souscategories fréquents
        for i, souscategorieFrequent in enumerate(listeSoucatFrequent):
            if souscategorieFrequent != "":
                objectsousCategorieFrec = Souscategorie.query.filter_by(labelSouscategorie=souscategorieFrequent).first()
                # remplace le label de la souscategorie par l'id
                listeSoucatFrequent[i] = objectsousCategorieFrec.id
            else:
                #si la soucategorie n'existe pas, on remplace par None
                listeSoucatFrequent[i] = None


        # si la taille de la liste categorie est egale à celle de la sous-categorie, on appelle la méthode generateObjectCategorie pour la creation des objets categories
        if len(listeCatFrequent) == len(listeSoucatFrequent):
            generateObjectCategorie(listeCatFrequent, listeObjetsMetiers, listeSoucatFrequent)
        else:
            erreurs.append(
                "Veuillez vérifier les categories et les sous-categories de métiers que vous avez selectionnées")

# ----- METIERS DECLARES--------##

        # remplace les labels de deux listes par les id correspondants dans la base
        for i, categorie in enumerate(listeCategories):
            if categorie != "":
                objectCategorie = Categorie.query.filter_by(labelCategorie=categorie).first()
                # remplace le label de la categorie par l'id
                listeCategories[i] = objectCategorie.id

        for i, souscategorie in enumerate(listeSoucategories):
            if souscategorie != "":
                objetSouscategorie = Souscategorie.query.filter_by(labelSouscategorie=souscategorie).first()
                # remplace le label de la souscategorie par l'id sinon, rajoute None
                listeSoucategories[i] = objetSouscategorie.id
            else:
                # si la soucategorie n'existe pas, on remplace par None
                listeSoucategories[i] = None
        # si la taille de la liste categorie est egale à celle de la sous-categorie, on appelle la méthode pour la creation des objets categories
        if len(listeCategories) == len(listeSoucategories):
            generateObjectCategorie(listeCategories, listeObjetsMetiers, listeSoucategories)
        else:
            erreurs.append(
                "Veuillez vérifier les categories et les sous-categories de métiers que vous avez selectionnées")

        # ----- AUTHORSPHIP --------##
        listeAuthorshipRegistre = []
        # users
        if current_user.is_authenticated:
            # retourne l'id de l'utilisateur connecté
            userID = current_user.get_id()

            authorshipRegistre = AuthorshipRegistre(user_id=userID, role="creator")
            listeAuthorshipRegistre.append(authorshipRegistre)

        #------TESTS ET CONTROLS-------#

        if listeTypeLieu.count("Naissance") > 1 \
            or listeTypeLieu.count("Domicile") > 1 \
            or listeTypeLieu.count("Dernier Passage") > 1 \
            or listeTypeLieu.count("Décès") > 1 :
            erreurs.append("Les lieux du type 'Naissance', 'Domicile', 'Dernier Passage', 'Décès' doivent figurer une seule fois")

        if lieuEnregistrementComplet == "":
            erreurs.append("Le lieu d'enregistrement est obligatoire. Vérifiez la rubrique 'Ajouter les éléments d'identification'")

        if dateEnregistremnt == "":
            erreurs.append("La date d'enregistrement est obligatoire. Vérifier la rubrique 'Ajouter les éléments d'identification")
        else:
            # appelle la méthode validate pour valider le format de date
            formatDateStatus = validate(dateEnregistremnt)
            if formatDateStatus == False:
                erreurs.append(
                    "Format de date incorrect. Resaisir selon le modèle JJ-MM-AAAA dans 'Ajouter les éléments d'identification'")

        if len(erreurs) > 0 :

            flash("La création d'un nouvel enregistrement a échoué pour les raisons suivantes : " + ", ".join(set(erreurs)), "error")

        # -------GENERER LES OBJETS ET ALIMENTER LA CREATION DU REGISTRE -------#
        # si les tests sont propres, on génère un objet LieuDeclare pour le lieu d'enregistrement et un avec un lieu déclaré
        else:

            status, data = DetailRegistre.create_register(
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
                collecte=collecte,
                commentaires=commentaires,
                photos=listeObjetsPhotos,
                lieuxDeclares = listeObjet_lieuDeclare,
                liensCategories=listeObjetsMetiers,
                caracteristiques=listeObjetCaracteristiques,
                voyageAvecRegistre=listeObjetsVoyageAvec,
                authorshipRegistres=listeAuthorshipRegistre)

            if status is True:
               #récupère l'objet registre qu'on vient de créer
               newregister = db.session.query(DetailRegistre).order_by(DetailRegistre.id.desc()).first()
               flash("Création d'un nouveau registre réussie !", "success")

               # initialise à vide la variable statique de la class dataCache pour relancer la requête en bdd lors de l'appel de la route index.
               # cela permet de mettre à jours le nombre de registre de la personne dans l'index.
               dataCache.listePersonnes = []

               return redirect("/registre/"+str(newregister.id))

            else:
               flash("La création d'un nouvel enregistrement a échoué pour les raisons suivantes : " + ", ".join(data), "error")


        return render_template("creer_registre.html",
                               personneUnique=personneUnique,
                               lieux=listeNomLieu,
                               categories=categories,
                               typeDocument=listeTypeDocument,
                               listeNomsArchive=listeNomsArchive,
                               registreTemporaire=registreTemporaire,
                               listeTypeLieux=listeTypeLieux,
                               listeMetiersCourants=listeMetiersCourants,
                               lastRecord=lastRecord,
                               caracteristiquesPysiques=caracteristiquesPysiques
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

    # recupération de la liste des catégories professionnemmes pour les passer dans l'input HTML à la modification du métier
    listeObjetscategories = Categorie.query.all()
    # recupération de la liste des caracteristiques physiques pour les passer dans l'input HTML
    caracteristiquesPys = db.session.query(CaracteristiquePhysique.labelCaracteristique).distinct().all()
    caracteristiquesPysiques = sorted(caracteristiquesPys, key=sortByPhysique)

    # on fournit une liste avec les types de documents pour l'autocomplete. A mettre à jour si un nouveau type de document est proposé
    listeTypeDocument = []
    typeDocument = db.session.query(DetailRegistre.natureDoc).distinct().all()
    for typeDoc in typeDocument:
        if typeDoc[0] is not None:
            listeTypeDocument.append(typeDoc[0])

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
        return render_template("modification_registre.html",
                               registre_origine=registre_origine,
                               lieux=listeNomLieu,
                               listeObjetscategories=listeObjetscategories,
                               typeDocument=listeTypeDocument,
                               listeNomsArchive=listeNomsArchive,
                               listeTypeLieux=listeTypeLieux,
                               caracteristiquesPysiques=caracteristiquesPysiques)

    ######################################################################################
    #      Méthode POST: récupère les informations saisies pour chaque régistre         #
    ######################################################################################

    elif request.method == "POST":
        erreurs = []
        listeObjet_lieuDeclare = []
        listeObjetsMetiers = []
        listeObjetCaracteristiques = []
        listeObjetsVoyageAvec = []
        listeObjetsPhotos = []


 #      LIEUX DECLARES         #

        # on récupère le lieu d'enregistrement et la date du formulaire modifié
        # récupération du lieu de passage avec la forme lieu, departement, pays, id dans le form (Lieu d'enregistrement) (attribut html name)
        lieuEnregistrementComplet = request.form.get("lieuPassage", None)
        # transforme le str du lieu de passage (enregisrtement) en liste et récupère uniquement l'id (le dernier élément de la liste)
        lieuEnregistrementListe = lieuEnregistrementComplet.split(",")
        # on récupère le dernière de la liste, l'id du lieu
        id_lieuPassage = lieuEnregistrementListe[-1]
        #on recupère le contenu du champ date
        dateEnregistremnt = request.form.get("datePassage", None)
        if lieuEnregistrementComplet == "":
            erreurs.append("Le lieu d'enregistrement est obligatoire. Vérifiez la rubrique 'Modifier les éléments d'identification'")

        if dateEnregistremnt == "":
            erreurs.append("La date d'enregistrement est obligatoire. Vérifiez la rubrique 'Modifier les éléments d'identification'")

        else:
            # appelle la méthode validate pour valider le format de date
            formatDateStatus = validate(dateEnregistremnt)
            if formatDateStatus == False:
                erreurs.append("Format de date incorrect. Resaisir selon le modèle JJ-MM-AAAA dans 'Modifier les éléments d'identification'")
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

        for i in range (0,len(listeDate)):
            # si les dates sont saisies
            if listeDate[i] != "":
                # vérifie le format des dates
                formatStatusDate = validate(listeDate[i])
                # si le format est invalide, renvoie une erreur
                if formatStatusDate == False:
                    erreurs.append(
                         "Format de date incorrect. Resaisir selon le modèle JJ-MM-AAAA dans 'Modifier les lieux et les dates de passage de la personne'")
                #sinon on change pas la liste
                else:
                    listeDate=listeDate
            else:
                listeDate = listeDate

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

#-------- VOYAGE AVEC ID PERSONNE -----------#
        listePersonnesAccompagnantes = request.form.getlist("voyageAvecIdPers", None)

        if listePersonnesAccompagnantes:
            for idPersonneAccompagnante in listePersonnesAccompagnantes:
                personneCompagne = Personne.query.get(idPersonneAccompagnante)
                if personneCompagne:
                    # utilisation de la mérthode generateObjectVoyageAvec pour créer des objects voyageAvec
                    objectVoyageAvec = VoyageAvec(id_personne=personneCompagne.id)
                    listeObjetsVoyageAvec.append(objectVoyageAvec)

                else:
                    erreurs.append(
                        "L'un des identifiants des compagnons de la personne n'existe pas. Vérifier la rubrique 'Modifier les éléments sur les personnes d'accompagnement' ")

# -------- PHOTOS -----------#
        listePhotoArchive = request.form.getlist("photo", None)
        if listePhotoArchive:
            for photo in listePhotoArchive:
                # pour chaque nom de photo de la liste, on crée un objet Photo et on le rajoute à la liste d'objets photos
                objetPhoto = Photo(label_photo=photo)
                listeObjetsPhotos.append(objetPhoto)


 # ------Archives et cotes
        nomArchive = request.form.get("archive", None)
        if nomArchive == '':
            erreurs.append(
                "Le nom de l'institution d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Modifier les sources d'archives'")

        cote = request.form.get("cote", None)
        if cote == '':
            erreurs.append(
                "La côte d'archive à l'origine de la notice est obligatoire. Vérifier la rubrique 'Modifier les sources d'archives'")

#------ CARACTERISTIUQES PHYSIQUES    -----##

        # récupérer les caracteristiques physiques
        listePhysique = request.form.getlist("physique", None)
        if listePhysique:
            for physique in listePhysique:
                objetPhysique = CaracteristiquePhysique(labelCaracteristique=physique)
                listeObjetCaracteristiques.append(objetPhysique)

        caracteristiquesPhysiques=request.form.get("carrPhys", None)
        # si le champs caractéristiques physiques déclarés n'est pas saisi on enregistre dans la base la valeur de car phys normalisées
        if caracteristiquesPhysiques == "" and listePhysique:
            caracteristiquesPhysiques = ", ".join(listePhysique)

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

# ------AUTHORSHIP-------#
        listeAuthorshipRegistre = []
        # users
        if current_user.is_authenticated:
            # cherche l'utilisateur dans la base de données.
            # Le username et le password de l'utilisateur sont fournis avec le formulaire
            userID = current_user.get_id()

            authorshipRegistre = AuthorshipRegistre(user_id=userID, role="contributor")
            listeAuthorshipRegistre.append(authorshipRegistre)

# ------TESTS ET CONTROLS-------#

        if listeTypeLieu.count("Naissance") > 1 \
                or listeTypeLieu.count("Domicile") > 1 \
                or listeTypeLieu.count("Dernier Passage") > 1 \
                or listeTypeLieu.count("Décès") > 1:
            erreurs.append("Les lieux du type 'Naissance', 'Domicile', 'Dernier Passage', 'Décès' doivent figurer une seule fois")

        # En cas d'erreursa
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
                caracteristiquesPhysiques= caracteristiquesPhysiques,
                autresCaracteristiques= request.form.get("autreCarr", None),
                epoux=request.form.get("epoux", None),
                nbEnfants=request.form.get("nbEnfants", None),
                nbAutreMembre=request.form.get("nbAutreMembre", None),
                nbPersSupplement=request.form.get("nbAutrePers", None),
                pseudonyme= request.form.get("pseudo", None),
                collecte= request.form.get("collecte", None),
                nomArchive=nomArchive,
                cote=cote,
                natureDoc=request.form.get("typeDoc", None),
                nrOrdre=request.form.get("ordre", None),
                photos=listeObjetsPhotos,
                commentaires= request.form.get("commentaires", None),
                lieuxDeclares=listeObjet_lieuDeclare,
                voyageAvecRegistre=listeObjetsVoyageAvec,
                caracteristiques=listeObjetCaracteristiques,
                liensCategories=listeObjetsMetiers,
                authorshipRegistres=listeAuthorshipRegistre
            )
            if status is True:
                flash("Modification du registre réussie !", "success")
                return redirect(url_for('registre',identifier_registre=id_registre))
            else:
                flash("La modification a échoué pour les raisons suivantes : " + ", ".join(data),
                      "error")
                return render_template("modification_registre.html", registre_origine=registre_origine,
                                       lieux=listeNomLieu, listeObjetscategories=listeObjetscategories,
                                       typeDocument=listeTypeDocument, listeNomsArchive=listeNomsArchive,
                                       listeTypeLieux=listeTypeLieux,
                                       caracteristiquesPysiques=caracteristiquesPysiques)

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

        for auteur in personne.authorshipPers:
            AuthorshipPersonne.delete_authorsphiPers(auteur.id)


    Personne.supprimer_personne(id_personne=nr_personne)

    # initialise à vide la variable statique de la class dataCache pour relancer la requête en bdd lors de l'appel de la route index.
    #cela permet de mettre à jours les liste de personnes dans l'index.
    dataCache.listePersonnes = []

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

        for auteur in registre.authorshipRegistres:
            AuthorshipRegistre.delete_authorsphiRegistre(auteur.id)

        for photo in registre.photos:
            Photo.delete_photos(photo.id)

        DetailRegistre.supprimer_registre(id_registre=id_registre)

        # initialise à vide la variable statique de la class dataCache pour relancer la requête en bdd lors de l'appel de la route index.
        #cela permet de mettre à jours les liste du nombre de registre par personnes dans l'index.
        dataCache.listePersonnes = []

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
    titre = "Résultats de la recherche : `" + motcle + "`"
    if isinstance(page, str) and page.isdigit():
        page = int(page)
    else:
        page = 1

    # Création d'une liste vide de résultat (par défaut, vide si pas de mot-clé)
    # liste du type : [(<Personne Boulan>, ["maitre d'un jeu de bagues", "joueur d'un jeu mécanique", 'joueur de chevaux de bois', "joueur d'un jeu mécanique de chevaux de bois"]), (<Personne Boulan>, ["joueur d'un jeu mécanique de chevaux de bois", 'joueur de chevaux de bois'])]
    listePersonnesMetitersAnnee = []

    # cherche les mots-clés dans les champs : nom, prenom, surnom, nom en langue maternelle, pays nationalité, langue
    # occupation(s) et description  categories = Categorie.query.all()
    if motcle !='' :
        # requete avec left join pour prendre en considération les personnes qui n'ont pas de registre
        #résultat du tyoe [<Personne Boulan>, <Personne Boulan>,<Personne Boulanger>]
        resultats = db.session.query(Personne).distinct().\
            join(DetailRegistre, Personne.id == DetailRegistre.id_personne, isouter=True).\
            filter(db.or_(Personne.nom.like("%{}%".format(motcle)),
                          Personne.prenom.like("%{}%".format(motcle)),
                          DetailRegistre.professionOrigine.like("%{}%".format(motcle)),
                          DetailRegistre.pseudonyme.like("%{}%".format(motcle)) )).\
            order_by(Personne.nom). \
            order_by(Personne.prenom).\
            all()

        #requête pour obtenir la liste des metiers de chaque personne, tout registre confondu
        for objetPersonne in resultats:
            listeMetiers=[]
            listeAnneeNaissance = []
            for registre in objetPersonne.registresPers:
                if registre.professionOrigine not in listeMetiers and registre.professionOrigine != None:
                    listeMetiers.append(registre.professionOrigine)
                else:
                    pass
                if registre.anneeNaissCalcule not in listeAnneeNaissance and registre.anneeNaissCalcule != None:
                    listeAnneeNaissance.append(registre.anneeNaissCalcule)
                else:
                    pass

            listePersonnesMetitersAnnee.append((objetPersonne, listeMetiers, listeAnneeNaissance))

    # si un résultat, renvoie sur la page résultat
    return render_template("resultats.html", personnes=listePersonnesMetitersAnnee, title=titre, keyword=motcle)


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

        flash('Félicitation, vous êtes enregisgit tré! Maintenant vous pouvez vous connecter.', 'success')
        return redirect(url_for('login'))


    # ça retourne une page html à laquelle on passe en paramètre pour title la valeur 'Enregistrement"
    # et pour form la valeur formulaire (qui a été instancé et rempli plus haut)
    return render_template('register.html', title='Enregistrement', form=formulaire)
"""
@appli.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('intro'))
