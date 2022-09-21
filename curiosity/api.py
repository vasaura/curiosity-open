from flask import request, url_for, jsonify
from urllib.parse import urlencode
from curiosity import appli
from flask_login import login_required
from curiosity.modeles.personnes_registres import Personne, Lieu
from .constantes import PERSONNES_PAR_PAGES, API_ROUTE
from .externalMethods.externalMethods import json_response


@appli.route(API_ROUTE+"/personne/<int:identifier>")
@login_required
def api_personne(identifier):
    person = Personne.query.get(identifier)

    if not person:
        return json_response(404,"raté","la requête a échoué", "")
    else:
        personne = jsonify(person.personne_json())
        personne.headers["content-type"] = "application/json;charset=UTF-8"
        return personne

@appli.route(API_ROUTE+"/personnes")
@login_required
def api_personnes_browse():
    """ Route permettant de trouver une liste de personnes en fonct du mot clé rechercher q=motclé

    L'appeller avec une requête du type http://127.0.0.1:5000/api/personnes?q=Audif
    """
    # q est très souvent utilisé pour indiquer une capacité de recherche
    motclef = request.args.get("q", None)
    page = request.args.get("page", 1)

    if isinstance(page, str) and page.isdigit():
        page = int(page)
    else:
        page = 1

    if motclef:
        query = Personne.query.filter(
            Personne.nom.like("%{}%".format(motclef))
        )
    else:
        query = Personne.query

    try:
        resultats = query.paginate(page=page, per_page=PERSONNES_PAR_PAGES)
    except Exception:
        return json_response(404,"raté","la requête a échoué", "")

    dict_resultats = {
        "links": {
            "self": request.url
        },
        "data": [
            pers.personne_json() for pers in resultats.items
        ]
    }

    if resultats.has_next:
        arguments = {
            "page": resultats.next_num
        }
        if motclef:
            arguments["q"] = motclef
        dict_resultats["links"]["next"] = url_for("api_personnes_browse", _external=True)+"?"+urlencode(arguments)

    if resultats.has_prev:
        arguments = {
            "page": resultats.prev_num
        }
        if motclef:
            arguments["q"] = motclef
        dict_resultats["links"]["prev"] = url_for("api_personnes_browse", _external=True)+"?"+urlencode(arguments)

    response = jsonify(dict_resultats)
    return response


@appli.route("/savePlace", methods=["POST"])
@login_required
def savePlace():
    """ Route de type api permettant à l'utilisateur de créer un lieu sans passer par return_template"""
    # variable qui va récupérer la concaténation entre le nom du lieu, le département, le pay et l'id du lieu et le passe en paramettre pour le rajouter à la liste des lieux coté html
    nouveauLieuComplet = ""
    if request.method == "POST":
        # vérifie que l'objet envoyé depuis le client est en format json
        if request.is_json:
            # recupère le contenu json de l'objet body crée coté clien avec ajax
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

