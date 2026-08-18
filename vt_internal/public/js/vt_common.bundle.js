// Bundle commun vt_internal : helpers front partagés, chargés sur tout le Desk
// (déclaré dans hooks.py -> app_include_js).
//
// Expose les namespaces globaux :
//   - vt.timer   : pointage (feuilles de temps / fiches de travail) + widget global
//   - vt.photos  : galerie photos réutilisable
//
// Ces modules remplacent le code dupliqué qui vivait dans visite_technique.js
// et fiche_de_travail.js.

import "./vt/timer";
import "./vt/photos";
import "./vt/timer_widget";
