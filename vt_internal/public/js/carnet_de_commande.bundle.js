// Bundle Vue de la page Carnet de commande.
//
// frappe.ui.CarnetDeCommandeView : store réactif, charge l'API JSON
// `get_order_book` et monte l'app Vue (filtres, KPIs, tableau riche).
// Même architecture que la page Chantiers.

import { createApp, reactive } from "vue";
import CarnetApp from "./carnet_de_commande/CarnetApp.vue";
import { rowStatusLabel } from "./carnet_de_commande/helpers.js";

const API = "vt_internal.vt_internal.api.order_book.get_order_book";

function parseStatusParam(raw) {
	if (!raw) return [];
	return raw
		.split(",")
		.map((s) => s.trim())
		.filter(Boolean);
}

function readUrlFilters() {
	const q = new URLSearchParams(window.location.search);
	const f = {};
	if (q.get("company")) f.company = q.get("company");
	if (q.get("cm")) f.conducteurs = q.get("cm").split(",").filter(Boolean);
	if (q.get("cc")) f.cost_center = q.get("cc");
	const statuses = parseStatusParam(q.get("status"));
	if (statuses.length) f.statuses = statuses;
	return f;
}

class CarnetDeCommandeView {
	constructor({ wrapper, page }) {
		this.$wrapper = $(wrapper);
		this.page = page;
		this.store = reactive({
			loading: true,
			data: null,
			error: null,
			filters: {
				company: null,
				conducteurs: [],
				cost_center: null,
				statuses: [],
				...readUrlFilters(),
			},
			openProject: (name) => window.openProjectDetails(name),
			openDoc: (dt, name) => frappe.set_route("Form", dt, name),
			reload: () => this.reload(),
			syncUrl: () => this.syncUrl(),
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
		this.page.add_menu_item(__("Ouvrir l'ancien rapport"), () =>
			frappe.set_route("query-report", "Order book")
		);
		this.page.add_menu_item(__("Ouvrir le planning"), () =>
			frappe.set_route("planning-chantiers")
		);
	}

	syncUrl() {
		const f = this.store.filters;
		const q = new URLSearchParams();
		if (f.company) q.set("company", f.company);
		if (f.conducteurs && f.conducteurs.length) q.set("cm", f.conducteurs.join(","));
		if (f.cost_center) q.set("cc", f.cost_center);
		if (f.statuses && f.statuses.length) q.set("status", f.statuses.join(","));
		const qs = q.toString();
		window.history.replaceState(
			window.history.state,
			"",
			window.location.pathname + (qs ? "?" + qs : "")
		);
	}

	reload() {
		const f = this.store.filters;
		this.syncUrl();
		this.store.loading = true;
		this.store.error = null;
		frappe.call({
			method: API,
			args: {
				company: f.company || undefined,
				cost_center: f.cost_center || undefined,
				construction_managers:
					f.conducteurs && f.conducteurs.length ? JSON.stringify(f.conducteurs) : undefined,
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
			["name", "Désignation"],
			["customer_name", "Client"],
			["delivery_date", "Date de livraison"],
			["internal_status", "Statut"],
			["custom_construction_status", "Statut du chantier"],
			["reference_piece", "Référence"],
			["remaining_amount", "Reste à facturer"],
			["total", "Total HT"],
			["hours_total", "Heures total"],
			["hours_solde", "Heures solde"],
			["age", "Age"],
			["construction_manager_name", "Responsable du chantier"],
			["project", "Chantier"],
		];
		const esc = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;
		const lines = [cols.map((c) => esc(c[1])).join(",")];
		d.rows.forEach((row) => {
			const extra = [
				esc((row.pending_arcs || []).map((a) => a.supplier_name).join(" | ")),
				esc((row.events || []).map((e) => e.kind).join(" | ")),
			];
			const values = cols.map((c) => {
				if (c[0] === "internal_status") return esc(row.internal_status || rowStatusLabel(row));
				return esc(row[c[0]]);
			});
			lines.push(values.join(",") + "," + extra.join(","));
		});
		const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = "carnet_de_commande.csv";
		a.click();
		URL.revokeObjectURL(url);
	}

	mount() {
		const el = document.createElement("div");
		this.$wrapper.get(0).appendChild(el);
		const app = createApp(CarnetApp, { store: this.store });
		if (typeof window.SetVueGlobals === "function") window.SetVueGlobals(app);
		app.mount(el);
		this.app = app;
	}
}

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
frappe.ui.CarnetDeCommandeView = CarnetDeCommandeView;
export default CarnetDeCommandeView;
