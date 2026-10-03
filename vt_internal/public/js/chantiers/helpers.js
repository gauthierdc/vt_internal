// Helpers partagés entre les composants de la vue Chantiers.

export const STATUS_COLORS = {
	Open: "#1976d2",
	Completed: "#2e7d32",
	Cancelled: "#9e9e9e",
	"En cours": "#f57c00",
	Overdue: "#c62828",
};

export const ACT_COLORS = [
	"#1976d2", "#26a69a", "#7e57c2", "#ef6c00", "#ec407a", "#78909c", "#9ccc65",
];

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
	return n + " €";
};

// Miroir de vt_internal.vt_internal.utils.ca_facture.VARIATION_MIN_BASE_RATIO.
// En dessous, la base de comparaison est trop mince pour un pourcentage
// (centre de coût créé en cours de période précédente, etc.).
export const VARIATION_MIN_BASE_RATIO = 0.05;

export function periodVariation(cur, prev, invert = false) {
	if (prev == null) {
		return { delta: null, deltaText: "", deltaClass: "", insignificant: false };
	}
	const curN = Number(cur) || 0;
	const prevN = Number(prev) || 0;
	const nearlyEmpty = curN !== 0 && Math.abs(prevN) < Math.abs(curN) * VARIATION_MIN_BASE_RATIO;
	if (nearlyEmpty) {
		return { delta: null, deltaText: "n.s.", deltaClass: "flat", insignificant: true };
	}
	if (prevN === 0) {
		return { delta: null, deltaText: "", deltaClass: "", insignificant: false };
	}
	const pct = Math.round(((curN - prevN) / Math.abs(prevN)) * 100);
	const up = pct > 0;
	const deltaText = (up ? "▲ +" : pct < 0 ? "▼ " : "= ") + pct + "%";
	const good = invert ? pct <= 0 : pct >= 0;
	const deltaClass = pct === 0 ? "flat" : good ? "good" : "bad";
	return { delta: pct, deltaText, deltaClass, insignificant: false };
}

// Marge réelle pondérée par la vente (même formule que aggregate_margin).
export function aggregateMargin(rows) {
	const vente = (rows || []).reduce((s, p) => s + (Number(p.vente) || 0), 0);
	const cout = (rows || []).reduce((s, p) => s + (Number(p.cout_reel) || 0), 0);
	const eur = Math.round(vente - cout);
	if (!vente) return { pct: null, eur, vente, cout };
	return { pct: Math.round(((vente - cout) / vente) * 100), eur, vente, cout };
}
