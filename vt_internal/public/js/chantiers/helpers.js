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
