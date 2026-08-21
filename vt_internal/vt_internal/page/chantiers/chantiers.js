// Page Desk "Chantiers" (route /app/chantiers).
//
// Le contrôleur crée la page-cadre puis charge le bundle Vue (esbuild construit
// chantiers.bundle.js). Le bundle expose frappe.ui.ChantiersView, une classe qui
// monte l'app Vue dans le corps de la page. Même pattern que workflow_builder.

frappe.pages["chantiers"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("👷 Chantiers"),
		single_column: true,
	});

	// Rechargement à chaud en développement.
	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => mount(wrapper));
	}
};

frappe.pages["chantiers"].on_page_show = function (wrapper) {
	mount(wrapper);
};

function mount(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	frappe.require("chantiers.bundle.js").then(() => {
		frappe.ui.chantiers_view = new frappe.ui.ChantiersView({
			wrapper: $parent,
			page: wrapper.page,
		});
	});
}
