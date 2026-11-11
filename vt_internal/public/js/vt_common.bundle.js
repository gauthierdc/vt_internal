// Bundle commun vt_internal : helpers front partagés, chargés sur tout le Desk
// (déclaré dans hooks.py -> app_include_js).
//
// Expose les namespaces globaux :
//   - vt.timer   : pointage (feuilles de temps / fiches de travail) + widget global
//   - vt.photos  : galerie photos réutilisable
//
// Ces modules remplacent le code dupliqué qui vivait dans visite_technique.js
// et fiche_de_travail.js.
//
// vt.copyChildRowData copie une ligne de tableau enfant sans son identité
// (name, doctype, parent), pour que les set_value suivants ne retombent pas
// sur le document d'origine.

import "./vt/timer";
import "./vt/photos";
import "./vt/timer_widget";
import { copyChildRowData } from "./copy_child_row.js";
import { attachCalendarEmployeeHelpers } from "./event_calendar_employees.js";
import { attachDeskMobileScrollHelpers, installDeskMobileScrollGuard } from "./vt_desk_mobile_scroll.js";

if (typeof frappe !== "undefined") {
	frappe.provide("frappe.vt");
	frappe.vt.copyChildRowData = copyChildRowData;
	attachCalendarEmployeeHelpers(frappe.vt);
	attachDeskMobileScrollHelpers(frappe.vt);

	const bootMobileScroll = () => {
		installDeskMobileScrollGuard({
			doc: document,
			pageProto: frappe.ui && frappe.ui.Page && frappe.ui.Page.prototype,
			router: frappe.router,
			getWidth: () => window.innerWidth,
		});
	};
	if (frappe.after_ajax) {
		frappe.after_ajax(bootMobileScroll);
	} else {
		bootMobileScroll();
	}
}
