// Bundle Vue de la page Planning Chantiers.
//
// frappe.ui.PlanningChantiersView : construit le store réactif, charge l'API
// JSON `get_planning` et monte l'app Vue (grille hebdomadaire des jalons).
// Même architecture que la page Chantiers.

import { createApp, reactive } from "vue";
import PlanningApp from "./planning_chantiers/PlanningApp.vue";

const API = "vt_internal.vt_internal.api.planning.get_planning";

// Lundi de la semaine contenant `d` (Date) → "YYYY-MM-DD".
function mondayISO(d) {
	const dt = new Date(d);
	const dow = (dt.getDay() + 6) % 7; // lundi = 0
	dt.setDate(dt.getDate() - dow);
	return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
}

function defaultStart() {
	// 2 semaines avant la semaine courante (pour voir aussi ce qui vient d'être fait).
	const d = new Date();
	d.setDate(d.getDate() - 14);
	return mondayISO(d);
}

function readUrlFilters() {
	const q = new URLSearchParams(window.location.search);
	const f = {};
	if (q.get("start")) f.start_date = q.get("start");
	if (q.get("weeks")) f.weeks = parseInt(q.get("weeks"), 10) || undefined;
	if (q.get("company")) f.company = q.get("company");
	if (q.get("cc")) f.cost_center = q.get("cc");
	if (q.get("cm")) f.conducteur = q.get("cm");
	if (q.get("resp")) f.responsable = q.get("resp");
	if (q.get("active")) f.only_active = q.get("active") === "1";
	if (q.get("g")) f.granularity = q.get("g") === "day" ? "day" : "week";
	return f;
}

class PlanningChantiersView {
	constructor({ wrapper, page }) {
		this.$wrapper = $(wrapper);
		this.page = page;
		this.store = reactive({
			loading: true,
			data: null,
			error: null,
			filters: {
				start_date: defaultStart(),
				weeks: 14,
				company: null,
				cost_center: null,
				conducteur: null,
				responsable: null,
				only_active: true,
				granularity: "week",
				...readUrlFilters(),
			},
			openDoc: (dt, name) => frappe.set_route("Form", dt, name),
			openProject: (name) => window.openProjectDetails(name),
			reload: () => this.reload(),
			shiftWeeks: (delta) => {
				const d = new Date(this.store.filters.start_date + "T00:00:00");
				d.setDate(d.getDate() + delta * 7);
				this.store.filters.start_date = mondayISO(d);
				this.reload();
			},
			goToday: () => {
				this.store.filters.start_date = defaultStart();
				this.reload();
			},
		});

		this.setup_filters();
		this.setup_actions();
		this.mount();
		this.reload();
	}

	setup_filters() {
		this.page.clear_fields();
	}

	setup_actions() {
		this.page.set_primary_action(__("Rafraîchir"), () => this.reload(), "refresh");
		this.page.add_menu_item(__("Exporter en CSV"), () => this.export_csv());
		this.page.add_menu_item(__("Ouvrir l'ancien rapport (Order book)"), () =>
			frappe.set_route("query-report", "Order book")
		);
	}

	syncUrl() {
		const f = this.store.filters;
		const q = new URLSearchParams();
		if (f.start_date) q.set("start", f.start_date);
		if (f.weeks) q.set("weeks", f.weeks);
		if (f.company) q.set("company", f.company);
		if (f.cost_center) q.set("cc", f.cost_center);
		if (f.conducteur) q.set("cm", f.conducteur);
		if (f.responsable) q.set("resp", f.responsable);
		q.set("active", f.only_active ? "1" : "0");
		if (f.granularity === "day") q.set("g", "day");
		const qs = q.toString();
		window.history.replaceState(window.history.state, "", window.location.pathname + (qs ? "?" + qs : ""));
	}

	reload() {
		const f = this.store.filters;
		this.syncUrl();
		this.store.loading = true;
		this.store.error = null;
		frappe.call({
			method: API,
			args: {
				start_date: f.start_date,
				weeks: f.weeks,
				company: f.company || undefined,
				cost_center: f.cost_center || undefined,
				conducteurs: f.conducteur ? JSON.stringify([f.conducteur]) : undefined,
				responsable: f.responsable || undefined,
				only_active: f.only_active ? 1 : 0,
				granularity: f.granularity || "week",
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
		if (!d || !d.rows || !d.rows.length) {
			frappe.show_alert({ message: __("Rien à exporter"), indicator: "orange" });
			return;
		}
		const cols = [
			["project", "Chantier"], ["customer", "Client"], ["construction_status", "Statut chantier"],
			["conducteur_nom", "Conducteur"], ["status", "Statut projet"],
			["total_sold", "Total commandé"], ["pct_facture", "% facturé"],
			["reste_a_facturer", "Reste à facturer"], ["nb_todo", "Jalons à venir"],
			["nb_overdue", "En retard"], ["next_date", "Prochaine échéance"],
		];
		const esc = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
		const lines = [cols.map((c) => esc(c[1])).join(",")];
		d.rows.forEach((r) => lines.push(cols.map((c) => esc(r[c[0]])).join(",")));
		const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `planning_chantiers_${d.period.start_date}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	mount() {
		const el = document.createElement("div");
		this.$wrapper.get(0).appendChild(el);
		const app = createApp(PlanningApp, { store: this.store });
		if (typeof window.SetVueGlobals === "function") window.SetVueGlobals(app);
		app.mount(el);
		this.app = app;
	}
}

// Modale de détail projet — réutilise l'API HTML existante project_details,
// exactement comme la page Chantiers. Définie globalement pour être partagée
// entre les deux pages (redéfinition idempotente si les deux bundles chargent).
function openProjectDetails(project) {
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
}
window.openProjectDetails = window.openProjectDetails || openProjectDetails;

frappe.provide("frappe.ui");
frappe.ui.PlanningChantiersView = PlanningChantiersView;
export default PlanningChantiersView;
