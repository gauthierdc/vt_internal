// TODO(remove): supprimer ce fichier + l'entrée dans hooks.py (app_include_js)
// une fois dokos/dokos#699 corrigé en amont (pricing dashboard paginé/plafonné).
//
// Neutralise le "Item Pricing Dashboard" upstream (erpnext/Dokos).
//
// erpnext/public/js/utils/item_pricing_dashboard.js rend TOUS les Item Price
// d'un partenaire dans un seul innerHTML (getPrices sans limit + un <tr> avec
// dropdown complet par prix). Sur un gros fournisseur ça gèle le thread
// principal ~30 s (ex. ADLER, 7390 prix). On ne s'en sert pas → on le désactive.
//
// Bug remonté en amont : dokos/dokos#699
// https://gitlab.com/dokos/dokos/-/work_items/699
//
// after_ajax garantit qu'on passe APRÈS erpnext.bundle.js (qui définit la
// classe au chargement) : notre remplacement gagne quel que soit l'ordre des
// bundles. Le constructeur no-op laisse simplement le wrapper "item_prices" vide.
frappe.after_ajax(() => {
  frappe.provide("erpnext.ui");
  erpnext.ui.pricing_dashboard = class DisabledPricingDashboard {
    constructor() {}
    init() {}
    loadData() {}
    render() {}
  };
});
