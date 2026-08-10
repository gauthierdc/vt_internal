"""Endpoints ventes (devis, commandes, factures, paiements).

Convertis depuis les Server Scripts ERP (type « API »).
URLs courtes historiques préservées via override_whitelisted_methods (hooks.py).
Source de vérité : ces fichiers (versionnés). Les records DB ont été supprimés.
"""

import frappe
from frappe import _

@frappe.whitelist()
def generate_consolidate_sales_invoice():
    # Converti depuis le Server Script API « generate_consolidate_sales_invoice » (/api/method/generate_consolidate_sales_invoice).
    delivery_note_to_bill = frappe.db.get_list("Delivery Note", {
        "per_billed": 0,
        "custom_livré": 0,
        "customer_name": ["like", "%*%"]
    },  ["name", "customer_name"])

    customers = list(dict.fromkeys([d.customer_name for d in delivery_note_to_bill]))

    for c in customers:
        sales_invoice = frappe.get_doc({
        'doctype': 'Sales Invoice',
        })
        items = []
        for dn in delivery_note_to_bill:
            if dn.customer_name == c:
                delivery_note = frappe.get_doc("Delivery Note", dn.name)
                sales_invoice.customer = delivery_note.customer
                sales_invoice.customer_name = delivery_note.customer_name
                sales_invoice.company = delivery_note.company
                sales_invoice.currency = delivery_note.currency
                sales_invoice.selling_price_list = delivery_note.selling_price_list
                sales_invoice.ignore_pricing_rule = delivery_note.ignore_pricing_rule
                sales_invoice.customer_name = delivery_note.customer_name
                sales_invoice.customer_name = delivery_note.customer_name
                sales_invoice.customer_name = delivery_note.customer_name
                sales_invoice.customer_name = delivery_note.customer_name
                sales_invoice.customer_name = delivery_note.customer_name
                sales_invoice.customer_name = delivery_note.customer_name
                sales_invoice.customer_name = delivery_note.customer_name
            items = dn.items
        sales_invoice.save()
        break


@frappe.whitelist()
def new_visite_technique_from_quotation():
    # Converti depuis le Server Script API « new_visite_technique_from_quotation » (/api/method/new_visite_technique_from_quotation).
    reference_piece = frappe.form_dict.get("reference_piece")
    customer = frappe.form_dict.get("customer")
    name = frappe.form_dict.get("quotation_name") or frappe.form_dict.get("sales_order_name")

    if frappe.form_dict.get("project"):
        frappe.response['message'] = {
            "project": frappe.form_dict.get("project")
        }
    else:
        project_name = f"{reference_piece} {customer} {name}" if reference_piece else f"{customer} {name}"
        project = frappe.get_doc({
            "doctype": "Project",
            "customer": frappe.form_dict.get("customer"),
            "project_name": project_name,
            "company": frappe.form_dict.get("company"),
            "address": frappe.form_dict.get("address"),
            "project_type": frappe.form_dict.get("custom_type_de_projet"),
            "cost_center": frappe.form_dict.get("cost_center")
        })

        project.insert()
        if frappe.form_dict.get("quotation_name"):
            frappe.db.set_value("Quotation", 
                frappe.form_dict.get("quotation_name"), 
                "project", project.name, 
                update_modified = False)
        elif frappe.form_dict.get("sales_order_name"):
            frappe.db.set_value("Sales Order", 
                frappe.form_dict.get("sales_order_name"), 
                "project", project.name, 
                update_modified = False)
            # update corresponding quotations
            quotations = list(dict.fromkeys([item.prevdoc_docname for item in doc.items]))
            for q in quotations:
                frappe.db.set_value("Quotation", q, "project", doc.project, update_modified = False)

        frappe.response['message'] = {
            "project": project.name
        }


@frappe.whitelist()
def payment_link_from_sales_order():
    # Converti depuis le Server Script API « payment_link_from_sales_order » (/api/method/payment_link_from_sales_order).
    data = frappe.form_dict

    sales_order = frappe.get_doc("Sales Order", data.sales_order)

    advance_item_code = data.advance_item_code
    advance_per = frappe.db.get_value("Item", advance_item_code, "down_payment_percentage")/100

    sales_invoice = frappe.call("erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice", source_name=sales_order.name)

    # Create the Sales Invoice document
    sales_invoice.is_down_payment_invoice = 1  # Mark the invoice as an advance payment
    sales_invoice.mode_of_payment = "Lien de paiement"
    advance_amount = sales_order.total*advance_per

    sales_invoice.items = []
    sales_invoice.append("items", {
        "item_code": advance_item_code,
        "qty": 1,
        "sales_order": sales_order.name,
        "rate": advance_amount,
    	"price_list_rate": advance_amount,
    	"base_rate": advance_amount,
    })
    sales_invoice.run_method("set_missing_values")
    sales_invoice.custom_create_payment_request = True

    # Save and submit the Sales Invoice
    sales_invoice.insert()
    sales_invoice.submit()

    result = {
    	"sales_invoice": sales_invoice.name
    }

    frappe.response.data = result


@frappe.whitelist()
def reconciliation_paiement_order_to_transaction():
    # Converti depuis le Server Script API « Rapprochement transaction ordre de paiement » (/api/method/reconciliation_paiement_order_to_transaction).
    # 1. Récupérer les deux documents
    bt = frappe.get_doc("Bank Transaction", frappe.form_dict.get("bt_name"))
    po = frappe.get_doc("Payment Order", frappe.form_dict.get("po_name"))

    # 2. Générer les paiements
    po.make_payments_in_batch()

    # 3. Retrouver les Payment Entry liés à cet ordre, validés
    payment_entries = frappe.get_all("Payment Entry", filters={
        "payment_order": po.name,
        "docstatus": 1
    }, fields=["name", "paid_amount"])

    if not payment_entries:
        frappe.throw("Aucun paiement validé trouvé pour cet ordre.")

    # 4. Ajouter les paiements au tableau 'payment_entries' de la transaction
    for pe in payment_entries:
        bt.append("payment_entries", {
            "payment_document": "Payment Entry",
            "payment_entry": pe.name,
            "allocated_amount": pe.paid_amount
        })

    bt.save()


@frappe.whitelist()
def sales_order_to_chantier_a_faire():
    # Converti depuis le Server Script API « sales_order_to_chantier_a_faire » (/api/method/sales_order_to_chantier_a_faire).
    sales_order = frappe.form_dict.get("sales_order")
    names = frappe.get_all(
        "Fiche de travail",
        filters={"sales_order": sales_order},
        pluck="name"
    )

    if not names:
        frappe.throw(_("Aucune fiche de travail liée à cette commande"))

    else:
        updated = 0
        for name in names:
            # Écrit directement en base et met à jour modified
            frappe.db.set_value("Fiche de travail", name, "status", "À faire", update_modified=True)
            updated = updated + 1
        frappe.db.set_value("Sales Order", sales_order, "custom_per_received", 100, update_modified=False)
        frappe.db.set_value("Sales Order", sales_order, "custom_statut_fiche_de_travail", "À faire", update_modified=False)
        frappe.msgprint(
            f"{updated} fiche(s) de travail mise(s) en 'À faire'.",
            indicator="green",
        )
