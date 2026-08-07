// Désactive le ListDashboard sur toutes les listes
frappe.provide('frappe.ui');
frappe.ui.ListDashboard = class {
	constructor() {}
	refresh() {}
};

// FIX sidebar : certains libellés de rapport contiennent un "%" (ex :
// "P&L — Marges brute & nette (%)"), dont le href /desk/query-report/...(%)
// fait lever URIError "URI malformed" à decodeURIComponent() dans
// Sidebar.is_route_in_sidebar(). Cette exception casse la construction des
// Pages custom (zone principale blanche). On protège la méthode : en cas
// d'erreur on renvoie false (pas de surbrillance) au lieu de tout casser.
(function guardSidebarRouteDecode() {
	const patch = () => {
		const proto = frappe.ui && frappe.ui.Sidebar && frappe.ui.Sidebar.prototype;
		if (!proto || proto.__vt_route_guard) return false;
		const orig = proto.is_route_in_sidebar;
		if (typeof orig !== 'function') return false;
		proto.is_route_in_sidebar = function () {
			try {
				return orig.apply(this, arguments);
			} catch (e) {
				console.warn('[VT] is_route_in_sidebar protégé (href mal formé) :', e.message);
				return false;
			}
		};
		proto.__vt_route_guard = true;
		return true;
	};
	if (!patch()) {
		const t = setInterval(() => { if (patch()) clearInterval(t); }, 100);
		setTimeout(() => clearInterval(t), 10000);
	}
})();

// Force la barre latérale V&T sur toutes les pages
frappe.after_ajax(() => {
	const wait = setInterval(() => {
		if (!frappe.app?.sidebar?.setup) return;
		clearInterval(wait);

		const sidebar = frappe.app.sidebar;
		const _orig_setup = sidebar.setup.bind(sidebar);
		let _in_setup = false;

		// Intercepte TOUS les appels à setup() quelle que soit leur origine
		// (navigation normale, Ctrl+K, route_options.sidebar, etc.)
		sidebar.setup = function (workspace_title) {
			if (_in_setup) return;
			_in_setup = true;
			try {
				_orig_setup('V&T');
			} finally {
				_in_setup = false;
			}
		};

		// Garde aussi set_workspace_sidebar par sécurité
		sidebar.set_workspace_sidebar = function () {
			this.setup('V&T');
		};
	}, 100);
});
