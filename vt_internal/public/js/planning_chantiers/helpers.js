// Helpers partagés de la vue Planning Chantiers.

export const fmtMoney = (n) =>
	new Intl.NumberFormat("fr-FR", {
		style: "currency",
		currency: "EUR",
		maximumFractionDigits: 0,
	}).format(n || 0);

export const fmtCompact = (n) => {
	n = n || 0;
	if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + " M€";
	if (Math.abs(n) >= 1e3) return Math.round(n / 1e3) + " k€";
	return Math.round(n) + " €";
};

// Définition visuelle de chaque type de jalon (icône, libellé, couleurs).
export const MILESTONE_TYPES = {
	po: { icon: "🛒", label: "Réception fournisseur", color: "#1565c0", bg: "rgba(25,118,210,.12)" },
	fab: { icon: "🏭", label: "Fabrication", color: "#6a3fb0", bg: "rgba(126,87,194,.14)" },
	delivery: { icon: "🚚", label: "Livraison", color: "#2e7d32", bg: "rgba(46,125,50,.12)" },
	vt: { icon: "🔍", label: "Visite technique", color: "#00838f", bg: "rgba(0,131,143,.12)" },
	ft: { icon: "📋", label: "Fiche de travail", color: "#4f5bd5", bg: "rgba(92,107,192,.16)" },
	event: { icon: "📅", label: "Événement", color: "#546e7a", bg: "rgba(84,110,122,.14)" },
	reception: { icon: "✅", label: "Réception de chantier", color: "#455a64", bg: "rgba(69,90,100,.12)" },
};

export const isEventLike = (t) => t === "vt" || t === "ft" || t === "event";

// Couleurs (nom d'indicateur Frappe → hex) pour VOS statuts de commande.
export const ORDER_STATUS_COLORS = {
	green: { color: "#1b7d3e", bg: "rgba(46,125,50,.14)" },
	red: { color: "#c62828", bg: "rgba(198,40,40,.14)" },
	orange: { color: "#e65100", bg: "rgba(245,124,0,.16)" },
	purple: { color: "#6a3fb0", bg: "rgba(126,87,194,.16)" },
	pink: { color: "#c2185b", bg: "rgba(216,27,96,.14)" },
	yellow: { color: "#b58a00", bg: "rgba(249,168,37,.20)" },
	blue: { color: "#1565c0", bg: "rgba(25,118,210,.14)" },
	gray: { color: "#6c7680", bg: "rgba(120,130,140,.14)" },
	grey: { color: "#6c7680", bg: "rgba(120,130,140,.14)" },
};

// Reproduit l'indicateur de la liste des commandes clients (sales_order_list.js
// get_indicator) pour afficher EXACTEMENT vos statuts métier dans le planning.
export function salesOrderStatus(so) {
	if (!so) return null;
	const billed = so.per_billed, del = so.per_delivered;
	const fiche = so.custom_statut_fiche_de_travail, rec = so.custom_per_received;
	const pay = so.custom_payment_request_status;
	const R = (label, color) => ({ label, color });
	if (billed === 100) return R(__("Terminé"), "green");
	if (so.status === "On Hold" || so.status === "Closed") return R(so.status, "gray");
	if (pay === "Requested") return R(__("🕦 Acompte"), "gray");
	if (del > 0 && billed < 100 && !fiche) return R(__("En BL"), "red");
	if (fiche === "À faire" && billed < 100) return R(__("Chantier à faire"), "orange");
	if (fiche === "En cours" && billed < 100) return R(__("Chantier en cours"), "purple");
	if (fiche === "À planifier" && billed < 100) return R(__("Chantier à planifier"), "pink");
	if (rec > 0 && rec < 100) return R(__("En fabrication"), "yellow");
	if (rec === 100 && del === 0 && !fiche) return R(__("À livrer"), "blue");
	if (del < 100 && billed < 100 && fiche === "Fait") return R(__("CH fait à facturer"), "red");
	if (rec === 0) return R(__("À fabriquer"), "green");
	return R(so.status || "", "gray");
}

export const fmtDate = (d) => (d ? frappe.datetime.str_to_user(d) : "");

export const fmtDateTime = (d) => {
	if (!d) return "";
	try {
		return new Intl.DateTimeFormat("fr-FR", {
			day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
		}).format(new Date(d.replace(" ", "T")));
	} catch (e) {
		return d;
	}
};
