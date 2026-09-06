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

		// Hard reload of a deep link (ex. Event calendar) often paints the
		// module sidebar before this patch is installed. Re-apply V&T once.
		sidebar.setup('V&T');
	}, 100);
});

// Mobile : si Frappe a laissé html/body en overflow:hidden alors qu'aucun
// overlay n'est ouvert, on rétablit le scroll (tout le Desk, pas seulement
// le calendrier). vt_common installe le même garde-fou ; cet appel est
// idempotent et sert si le bundle commun arrive plus tard.
(function guardMobileDeskScroll() {
	const tryInstall = () => {
		const api = typeof frappe !== 'undefined' && frappe.vt && frappe.vt.desk_mobile_scroll;
		if (!api || typeof api.installDeskMobileScrollGuard !== 'function') return false;
		api.installDeskMobileScrollGuard({
			doc: document,
			pageProto: frappe.ui && frappe.ui.Page && frappe.ui.Page.prototype,
			router: frappe.router,
			getWidth: () => window.innerWidth,
		});
		return true;
	};
	if (tryInstall()) return;
	const t = setInterval(() => {
		if (tryInstall()) clearInterval(t);
	}, 100);
	setTimeout(() => clearInterval(t), 15000);
})();
