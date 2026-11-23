// Chargé sur tout le site (web_include_js, nom de bundle nu → fichier haché).
// Inactif hors /bon-pour-accord-devis.
//
// webform_include_js ne convient pas : sur Frappe 15 il n'est injecté que pour
// un Web Form standard qui a déjà un .js dans l'app. Celui-ci est custom, en
// base. Le passer en standard écraserait les éditions de Solène.

import {
	applyPaiementCbDocument,
	isBonPourAccordPath,
	quotationFromSearch,
} from "./bon_pour_accord_paiement.js";

const METHOD = "vt_internal.vt_internal.api.web_form.get_texte_paiement_cb";

function fillPaiementCb() {
	try {
		if (typeof window === "undefined" || !isBonPourAccordPath(window.location.pathname)) return;
		const quotation = quotationFromSearch(window.location.search);
		if (!quotation || typeof frappe === "undefined" || typeof frappe.call !== "function") return;
		frappe.call({
			method: METHOD,
			args: { quotation },
			silent: true,
			error() {},
			callback(response) {
				const message = response && response.message;
				if (!message || typeof document === "undefined") return;
				applyPaiementCbDocument(document, message);
			},
		});
	} catch (_e) {
		// La phrase générique déjà dans l'intro reste affichée.
	}
}

if (typeof frappe !== "undefined" && typeof frappe.ready === "function") {
	frappe.ready(fillPaiementCb);
}
