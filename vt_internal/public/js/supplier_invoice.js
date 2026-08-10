// Converti depuis le Client Script ERP 'Facture fournisseur' (Supplier Invoice / Form).
// Source de vérité : ce fichier (versionné). Le record DB a été supprimé.

frappe.ui.form.on('Supplier Invoice', {
	refresh(frm) {
		frm.trigger('show_supplier_warning');
		frm.trigger('find_matching_purchase_order');
	}
});

frappe.ui.form.on('Supplier Invoice', {

	show_supplier_warning(frm) {
		if (!frm.doc.supplier) return;

		frappe.db.get_value('Supplier', frm.doc.supplier, 'custom_supplier_alert')
			.then(({ message }) => {
				if (message && message.custom_supplier_alert) {
					frm.dashboard.set_headline_alert(
						`<div class="alert alert-warning" style="margin-bottom:0;">
							${message.custom_supplier_alert}
						</div>`
					);
				}
			});
	},

	find_matching_purchase_order(frm) {
		if (!frm.doc.supplier || !frm.doc.supplier_grand_total) return;
		if (frm.is_dirty()) return;

		let amount = frm.doc.supplier_grand_total;
		let tolerance = 0.01;

		frappe.db.get_list('Purchase Order', {
			filters: {
				supplier: frm.doc.supplier,
				grand_total: ['between', [amount - tolerance, amount + tolerance]],
				docstatus: 1,
				per_billed: ['<', 100],
				status: ['!=', 'Closed']
			},
			fields: ['name', 'grand_total', 'status', 'transaction_date', 'per_billed'],
			limit: 5
		}).then(matches => {
			if (!matches.length) return;

			matches.forEach(po => {
				frm.add_custom_button(
					__('Rapprocher avec la commande {0}', [po.name]),
					() => reconcile_with_purchase_order(frm, po.name),
					__('Rapprochement')
				);
			});
		});
	}
});

// Fonction normale, en dehors des triggers de formulaire, appelée directement par le bouton
function reconcile_with_purchase_order(frm, po_name) {
	frappe.confirm(
		__('Voulez-vous remplacer les lignes actuelles de la facture par les articles de la commande {0} ?', [po_name]),
		() => {
			frappe.call({
				method: 'get_document_item_lines',
				doc: frm.doc,
				args: {
					doctype: 'Purchase Order',
					selected_documents: [{ name: po_name }],
					allow_child_item_selection: false,
					filtered_line_items: null
				}
			}).then((res) => {
				if (!res.message || !res.message.items) {
					frappe.msgprint(__('Aucune ligne renvoyée pour cette commande.'));
					return;
				}

				frm.clear_table('items');

				if (res.message.company && !frm.doc.company) {
					frm.set_value('company', res.message.company);
				}
				if (res.message.currency && !frm.doc.currency) {
					frm.set_value('currency', res.message.currency);
				}

				res.message.items.forEach(r => {
					frm.add_child('items', {
						reference_doctype: 'Purchase Order',
						reference_docname: r.parent,
						row: r.name,
						project: r.project,
						cost_center: r.cost_center,
						price: r.price,
						item_code: r.item_code,
						rate: r.rate,
						qty: r.qty,
						amount: r.amount,
						expense_account: r.expense_account,
						description: r.description,
					});
				});

				frm.refresh_field('items');
				frm.trigger('calculate_totals');

				frappe.show_alert({
					message: __('Lignes importées depuis {0}', [po_name]),
					indicator: 'green'
				});
			}).catch(err => {
				console.error('Erreur get_document_item_lines, utilisation du fallback :', err);

				frappe.db.get_list('Purchase Order Item', {
					filters: { parent: po_name },
					fields: ['name', 'item_code', 'description', 'qty', 'rate', 'amount',
							  'project', 'cost_center', 'expense_account'],
					limit: 100
				}).then(items => {
					frm.clear_table('items');
					items.forEach(r => {
						frm.add_child('items', {
							reference_doctype: 'Purchase Order',
							reference_docname: po_name,
							row: r.name,
							project: r.project,
							cost_center: r.cost_center,
							item_code: r.item_code,
							rate: r.rate,
							qty: r.qty,
							amount: r.amount,
							expense_account: r.expense_account,
							description: r.description,
						});
					});
					frm.refresh_field('items');
					frm.trigger('calculate_totals');

					frappe.show_alert({
						message: __('Lignes importées depuis {0} (fallback)', [po_name]),
						indicator: 'green'
					});
				}).catch(err2 => {
					console.error('Erreur fallback Purchase Order Item :', err2);
					frappe.msgprint({
						title: __('Erreur'),
						message: __('Impossible de récupérer les lignes de la commande.'),
						indicator: 'red'
					});
				});
			});
		}
	);
}
