// Helpers de la vue Carnet de commande.
// Couleurs événements alignées sur Planning (MILESTONE_TYPES).

export const EVENT_KIND_META = {
	vt: { label: "VT", icon: "🔍", color: "#00838f", bg: "rgba(0,131,143,.14)" },
	ft: { label: "Pose", icon: "📋", color: "#4f5bd5", bg: "rgba(92,107,192,.16)" },
	event: { label: "Évt", icon: "📅", color: "#546e7a", bg: "rgba(84,110,122,.14)" },
};

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

// Ordre canonique des statuts internes (pills colonne Statut / sales_order_list).
export const INTERNAL_STATUS_ORDER = [
	"À fabriquer",
	"En fabrication",
	"À livrer",
	"En BL",
	"Chantier à planifier",
	"Chantier à faire",
	"Chantier en cours",
	"CH fait à facturer",
	"🕦 Acompte",
	"On Hold",
	"Closed",
	"Terminé",
];

// Reproduit l'indicateur de la liste des commandes clients (sales_order_list.js).
export function salesOrderStatus(so) {
	if (!so) return null;
	const billed = so.per_billed;
	const del = so.per_delivered;
	const fiche = so.custom_statut_fiche_de_travail;
	const rec = so.custom_per_received;
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

export function rowStatusLabel(row) {
	const s = salesOrderStatus(row);
	return s ? s.label : "";
}

export function uniqueInternalStatusOptions(rows) {
	const present = new Set((rows || []).map(rowStatusLabel).filter(Boolean));
	const options = [];
	const seen = new Set();
	INTERNAL_STATUS_ORDER.forEach((key) => {
		const label = typeof __ === "function" ? __(key) : key;
		if ((present.has(label) || present.has(key)) && !seen.has(label)) {
			options.push({ value: present.has(label) ? label : key, label: present.has(label) ? label : key });
			seen.add(options[options.length - 1].value);
		}
	});
	[...present]
		.filter((label) => !seen.has(label))
		.sort((a, b) => a.localeCompare(b, "fr"))
		.forEach((label) => options.push({ value: label, label }));
	return options;
}

export function filterRowsByInternalStatuses(rows, statuses) {
	if (!statuses || !statuses.length) return rows;
	const set = new Set(statuses);
	return (rows || []).filter((r) => set.has(rowStatusLabel(r)));
}

function parseNaiveParis(raw) {
	if (raw == null || raw === "") return null;
	const m = String(raw)
		.trim()
		.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/);
	if (!m) return null;
	return {
		y: +m[1],
		mo: +m[2],
		d: +m[3],
		h: +(m[4] || 0),
		mi: +(m[5] || 0),
		s: +(m[6] || 0),
		hasTime: Boolean(m[4]),
	};
}

function parisParts(ref) {
	const fmt = new Intl.DateTimeFormat("en-GB", {
		timeZone: "Europe/Paris",
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
		hour12: false,
	});
	const parts = {};
	fmt.formatToParts(ref).forEach((p) => {
		if (p.type !== "literal") parts[p.type] = p.value;
	});
	return {
		y: +parts.year,
		mo: +parts.month,
		d: +parts.day,
		h: +parts.hour,
		mi: +parts.minute,
		s: +parts.second,
	};
}

export function isFutureEvent(ev, now) {
	if (!ev) return false;
	if (ev.past === true) return false;
	const parsed = parseNaiveParis(ev.starts_on);
	if (!parsed) return false;
	const ref = parisParts(now instanceof Date ? now : new Date());
	if (!parsed.hasTime) {
		if (parsed.y !== ref.y) return parsed.y > ref.y;
		if (parsed.mo !== ref.mo) return parsed.mo > ref.mo;
		return parsed.d >= ref.d;
	}
	const a = [parsed.y, parsed.mo, parsed.d, parsed.h, parsed.mi, parsed.s];
	const b = [ref.y, ref.mo, ref.d, ref.h, ref.mi, ref.s];
	for (let i = 0; i < 6; i++) {
		if (a[i] !== b[i]) return a[i] > b[i];
	}
	return true;
}

export function futureEvents(events, now) {
	return (events || []).filter((ev) => isFutureEvent(ev, now));
}

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

export const fmtDate = (d) => {
	if (!d) return "";
	if (typeof frappe !== "undefined" && frappe.datetime && frappe.datetime.str_to_user) {
		return frappe.datetime.str_to_user(String(d).slice(0, 10));
	}
	const dt = new Date(String(d).slice(0, 10) + "T00:00:00");
	if (Number.isNaN(dt.getTime())) return String(d);
	return new Intl.DateTimeFormat("fr-FR").format(dt);
};

export const fmtDateShort = (d) => {
	if (!d) return "";
	const dt = new Date(String(d).replace(" ", "T"));
	if (Number.isNaN(dt.getTime())) return String(d);
	return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit" }).format(dt);
};

export const ageTone = (age) => {
	if (age == null) return "";
	if (age < 30) return "ok";
	if (age < 100) return "warn";
	return "late";
};

export const hoursTone = (solde) => {
	if (solde == null) return "";
	if (solde < 0) return "late";
	if (solde === 0) return "ok";
	return "";
};
