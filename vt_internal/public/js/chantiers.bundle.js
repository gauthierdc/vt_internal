// Bundle Vue de la page Chantiers.
//
// frappe.ui.ChantiersView : construit les filtres dans la barre de la page
// (contrôles Frappe natifs → autocomplétion), charge les données via l'API JSON
// `get_chantiers`, et monte l'app Vue qui rend tout (KPIs, graphes, tableau).
//
// Le détail d'un projet réutilise la modale HTML existante (project_details),
// exposée ici en global `openProjectDetails` pour que le composant Vue l'appelle.

import { createApp, reactive } from "vue";
import ChantiersApp from "./chantiers/ChantiersApp.vue";

const API = "vt_internal.vt_internal.api.chantiers.get_chantiers";

function todayMinus(days) {
	return frappe.datetime.add_days(frappe.datetime.get_today(), days);
}

// Lit les filtres depuis la query string de l'URL (partage / navigation).
function readUrlFilters() {
	const q = new URLSearchParams(window.location.search);
	const f = {};
	if (q.get("start")) f.start_date = q.get("start");
	if (q.get("end")) f.end_date = q.get("end");
	if (q.get("company")) f.company = q.get("company");
	if (q.get("cm")) f.conducteurs = q.get("cm").split(",").filter(Boolean);
	return f;
}

class ChantiersView {
	constructor({ wrapper, page }) {
		this.$wrapper = $(wrapper);
		this.page = page;
		// Store réactif partagé avec l'app Vue.
		this.store = reactive({
			loading: true,
			data: null,
			error: null,
			filters: {
				// -6 → 7 jours glissants incluant aujourd'hui (aligné sur le bouton "7 j").
				start_date: todayMinus(-6),
				end_date: frappe.datetime.get_today(),
				company: null,
				conducteurs: [],
				// Écrase les valeurs par défaut avec celles de l'URL si présentes.
				...readUrlFilters(),
			},
			// Callbacks fournis au composant.
			openProject: (name) => window.openProjectDetails(name),
			reload: () => this.reload(),
			setPeriod: (start, end) => {
				this.store.filters.start_date = start;
				this.store.filters.end_date = end;
				this.reload();
			},
		});

		this.setup_filters();
		this.setup_actions();
		this.mount();
		this.reload();
	}

	setup_filters() {
		// Tous les filtres (période, société, conducteurs) sont pilotés depuis
		// l'app Vue : plus visibles et plus fiables que les champs de la barre.
		this.page.clear_fields();
	}

	setup_actions() {
		this.page.set_primary_action(
			__("Rafraîchir"),
			() => this.reload(),
			"refresh"
		);
		this.page.add_menu_item(__("Exporter en CSV"), () => this.export_csv());
		this.page.add_menu_item(__("Ouvrir l'ancien rapport"), () =>
			frappe.set_route("query-report", "👷Chantiers")
		);
	}

	// Écrit les filtres courants dans la query string (sans recharger la page).
	syncUrl() {
		const f = this.store.filters;
		const q = new URLSearchParams();
		if (f.start_date) q.set("start", f.start_date);
		if (f.end_date) q.set("end", f.end_date);
		if (f.company) q.set("company", f.company);
		if (f.conducteurs && f.conducteurs.length) q.set("cm", f.conducteurs.join(","));
		const qs = q.toString();
		const url = window.location.pathname + (qs ? "?" + qs : "");
		window.history.replaceState(window.history.state, "", url);
	}

	reload() {
		const f = this.store.filters;
		this.syncUrl();
		this.store.loading = true;
		this.store.error = null;
		// On utilise les callbacks natifs de frappe.call plutôt que le chaînage de
		// promesse : frappe.call renvoie un jqXHR jQuery qui n'implémente pas
		// .finally(), ce qui provoquait une "Unhandled Promise Rejection".
		frappe.call({
			method: API,
			args: {
				start_date: f.start_date,
				end_date: f.end_date,
				company: f.company || undefined,
				conducteurs: f.conducteurs && f.conducteurs.length ? JSON.stringify(f.conducteurs) : undefined,
			},
			callback: (r) => {
				if (r && r.message) this.store.data = r.message;
				this.store.loading = false;
			},
			error: () => {
				this.store.error = __("Erreur de chargement");
				this.store.loading = false;
			},
		});
	}

	export_csv() {
		const d = this.store.data;
		if (!d || !d.projects || !d.projects.length) {
			frappe.show_alert({ message: __("Rien à exporter"), indicator: "orange" });
			return;
		}
		const cols = [
			["project", "Chantier"], ["client", "Client"], ["status", "Statut"],
			["type_projet", "Type"], ["conducteur_nom", "Conducteur"],
			["ca_periode", "Facturé période"], ["po_periode", "Commandé fournisseur période"],
			["depense_periode", "Dépenses période"], ["fab_periode", "Fabrication période"], ["marge_theo", "Marge théo %"],
			["marge_reel", "Marge réel %"], ["marge_diff", "Écart marge"],
			["heures_val", "Heures validées"], ["heures_draft", "Heures non validées"],
			["heures_total", "Heures totales"], ["heures_expected", "Heures prévues"],
			["heures_diff", "Écart heures"], ["pct_facture", "% facturé"],
			["reste_a_facturer", "Reste à facturer"], ["retard", "Retard (j)"],
			["nb_incidents", "Incidents"], ["is_sav", "SAV"],
		];
		const esc = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
		const lines = [cols.map((c) => esc(c[1])).join(",")];
		d.projects.forEach((p) => lines.push(cols.map((c) => esc(p[c[0]])).join(",")));
		const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `chantiers_${d.period.start_date}_${d.period.end_date}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	mount() {
		const el = document.createElement("div");
		this.$wrapper.get(0).appendChild(el);
		const app = createApp(ChantiersApp, { store: this.store });
		if (typeof window.SetVueGlobals === "function") window.SetVueGlobals(app);
		app.mount(el);
		this.app = app;
	}
}

// Modale de détail projet (réutilise l'API HTML existante project_details).
window.openProjectDetails = function (project) {
	const dialog = new frappe.ui.Dialog({
		size: "extra-large",
		title: __("Détails du projet") + " · " + project,
		fields: [{ fieldname: "content", fieldtype: "HTML" }],
		primary_action: () => frappe.set_route("Form", "Project", project),
		primary_action_label: __("Ouvrir le projet"),
	});
	dialog.show();
	dialog.fields_dict.content.$wrapper.html(
		`<div class="text-muted" style="padding:40px;text-align:center;">${__("Chargement…")}</div>`
	);
	frappe
		.call({
			method: "vt_internal.vt_internal.api.project_details.project_details",
			args: { project },
		})
		.then((r) => dialog.fields_dict.content.$wrapper.html(r.message.html))
		.catch(() =>
			dialog.fields_dict.content.$wrapper.html(
				`<div class="text-danger" style="padding:40px;text-align:center;">${__("Erreur de chargement")}</div>`
			)
		);
};

frappe.provide("frappe.ui");
frappe.ui.ChantiersView = ChantiersView;
export default ChantiersView;
