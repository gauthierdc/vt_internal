import frappe

_STATUT_ATTENTE_FOURNISSEUR = "En attente réponse fournisseur"


def execute():
    if not frappe.db.exists("Custom Field", "Quotation-custom_sent_date"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Quotation",
            "fieldname": "custom_sent_date",
            "label": "Date d'envoi du devis",
            "fieldtype": "Date",
            "insert_after": "custom_dernier_statut_de_suivi",
            "allow_on_submit": 1,
            "in_list_view": 0,
            "in_standard_filter": 0,
        }).insert(ignore_permissions=True)

    child_dt = frappe.db.get_value(
        "Custom Field",
        {"dt": "Quotation", "fieldname": "custom_status_internes"},
        "options"
    )
    if not child_dt:
        return

    quotations = frappe.get_all(
        "Quotation",
        filters=[
            ["custom_dernier_statut_de_suivi", "not in", ["", None, _STATUT_ATTENTE_FOURNISSEUR]],
            ["custom_sent_date", "is", "not set"],
        ],
        fields=["name"],
    )

    for q in quotations:
        rows = frappe.get_all(
            child_dt,
            filters={"parent": q.name, "statut": ["!=", _STATUT_ATTENTE_FOURNISSEUR]},
            fields=["creation"],
            order_by="idx asc",
            limit=1,
        )
        if rows:
            sent_date = rows[0].creation.date()
            frappe.db.set_value("Quotation", q.name, "custom_sent_date", sent_date, update_modified=False)

    frappe.db.commit()
