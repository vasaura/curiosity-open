from curiosity import appli, db
from curiosity.modeles.users import User, AuthorshipPersonne
from curiosity.modeles.personnes_registres import Personne,DetailRegistre,LieuDeclare,Lieu,LienRegistresCategories,CaracteristiquePhysique,Categorie,VoyageAvec,Souscategorie


# pour créer une shell flask
@appli.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Personne': Personne, 'AuthorshipPersonne':AuthorshipPersonne}