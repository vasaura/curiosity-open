
function estDansLaListe(list, valeur){
           var estdansLaliste = false;

           // boucle sur toute la liste de lieux
          for (i=0; i < list.length; ++i ){

              if (valeur === list[i]) {
                  //si oui, on sort de la boucle
                  estdansLaliste = true;
                  break;
              }
          }
          return estdansLaliste;
}

//Fonction qui ajoute une icone rouge et supprime la saisie si le lieu n'existe pas dans la liste des lieu de l'autocomplete
function removeValueWhenIncorrectPlace(listeLieu, valeur, idInput, idDiv) {

    //récupère le input html avec le lieu normalisé
     var idLieuNorm = document.getElementById(idInput);

    // vérifie que le lieu normalisé est dans la liste
      // var retour = estDansLaListe(listeLieu,valeur )
      var retour = tagsLieux.includes(valeur);

     let divContainerLieuNorm = document.getElementById(idDiv);

    // crée la balise a < href="#myModalPlace" data-toggle="modal">
    const elementLinkModal = document.createElement("a");

    // ajoute les attributs : "href" = "#myModalPlace" et "data-toggle" = "modal"
    elementLinkModal.setAttribute("href", "#myModalPlace");
    elementLinkModal.setAttribute("data-toggle", "modal");

    // crée la balise icon  <i class="fas fa-clipboard-list icon-curiosity"></i>
     const elementIcon = document.createElement("i");
    // ajoute les attributs : class="far fa-folder-open icon-curiosity"
    elementIcon.classList.add("fas", "fa-clipboard-list", "icon-curiosity");

    // ajoute l'element <i> dans l'éléemnt <a>
    elementLinkModal.appendChild(elementIcon);


    // récupère l'élément <i> s'il existe
    var elemetsExist = divContainerLieuNorm.querySelector("i");

    // si le lieu saisi n'est pas dans la liste, le retour est à false
     if (retour ===false){
         // vider le lieu saisi s'il n'est pas dans la liste
          idLieuNorm.value="";
          // si l'élément <i> n'existe pas,
          if (typeof(elemetsExist) == 'undefined' || elemetsExist == null){
              // avec append on rajoute à la fin l'élément <a> qui contient l'élément <i>.
               divContainerLieuNorm.appendChild(elementLinkModal);
          }
      }
     // si le lieu saisi est dans la liste, le retour est à true
     else {
         // si l'élément <i> existe
         if (typeof(elemetsExist) != 'undefined' && elemetsExist != null){
             // on le supprime. il est le dernier élement du noeud parent
              divContainerLieuNorm.removeChild(divContainerLieuNorm.lastElementChild);
         }
     }
}

 // desactiver le mode submit du formulaire lorsqu'on appuie sur Enter du clavier
function removeEnterSubmit (idHtml){
      $("#"+idHtml).keypress(function(e) {
              //Enter key
              if (e.which == 13) {
                return false;
              }
            });
}

// griser le button submit des formulaires pour empêcher d'appuyer plusieurs fois sur creer-formulaire
function shadeButtonSubmit (){
      $(document).ready(function(){
                $("form.form-once-only").submit(function () {
                    $(this).find(':button').prop('disabled', true);
                });
            });
}

// fonction pour afficher la carte leaflet sans erreurs
 function displayMapInModal(idModal) {
  $("#"+idModal).on('shown.bs.modal', function () {
      setTimeout(function () {
          mymap.invalidateSize();
      }, 10);
  });
}

//fonction pour réaliser l'autocomplete pour plusieurs variables
function autocompleMultiple(id,sourceData){
     var accentMap = {
                "à": "a",
                "ö": "o",
                "â": "a",
                "é":"e",
                "è":"e",
                "ô":"o",
                "î":"i",
                "ï":"i",
                "û":"u",
                "ç":"c",
                "ù":"u",
                "ë":"e",
                "É":"E",
                "ú":"u",
                "ô":"o"
                };
     var normalize = function(term) {
        var ret = "";
        for (var i = 0; i < term.length; i++) {
          ret += accentMap[term.charAt(i)] || term.charAt(i);
        }
        return ret;
      };
     $(id).autocomplete({
      source: function( request, response ) {
              var matcher = new RegExp( "^" + $.ui.autocomplete.escapeRegex( request.term ), "i" );
              response( $.grep( sourceData, function( item ){
                  return matcher.test( item ) || matcher.test(normalize(item));
              }) );
          }
        });
}

