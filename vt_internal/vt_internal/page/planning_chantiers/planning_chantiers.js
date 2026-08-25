// Page Desk "Planning Chantiers" (route /app/planning-chantiers).
//
// Vue PROSPECTIVE remplaçant le rapport Order book : grille hebdomadaire des
// jalons de chaque chantier (réceptions fournisseur, fabrications, poses,
// événements, réceptions faites). Même pattern que la page Chantiers.

frappe.pages["planning-chantiers"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("🗓️ Planning Chantiers"),
		single_column: true,
	});

	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => mount(wrapper));
	}
};

frappe.pages["planning-chantiers"].on_page_show = function (wrapper) {
	mount(wrapper);
};

function mount(wrapper) {
	const $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();
	frappe.require("planning_chantiers.bundle.js").then(() => {
		frappe.ui.planning_chantiers_view = new frappe.ui.PlanningChantiersView({
			wrapper: $parent,
			page: wrapper.page,
		});
	});
}
