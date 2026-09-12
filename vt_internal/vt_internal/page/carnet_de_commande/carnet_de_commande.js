// Page Desk « Carnet de commande » (route /app/carnet-de-commande).
//
// Remplace le shell Script Report `query-report/Order book` par une page Vue
// (même pattern que Chantiers / Planning Chantiers) : filtres riches et
// cellules composant (ARC, événements, statuts).

frappe.pages["carnet-de-commande"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Carnet de commande"),
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => mount(wrapper));
	}
};

frappe.pages["carnet-de-commande"].on_page_show = function (wrapper) {
	mount(wrapper);
};

function mount(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	frappe.require("carnet_de_commande.bundle.js").then(() => {
		frappe.ui.carnet_de_commande_view = new frappe.ui.CarnetDeCommandeView({
			wrapper: $parent,
			page: wrapper.page,
		});
	});
}
