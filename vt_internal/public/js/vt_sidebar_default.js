// Désactive le ListDashboard sur toutes les listes
frappe.after_ajax(() => {
	frappe.ui.ListDashboard = class {};
});

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
