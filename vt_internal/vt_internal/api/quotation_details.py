import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def quotation_details(quotation):
    doc = frappe.get_doc("Quotation", quotation)

    # Reproduce before_print logic
    doc.weigth_of_visible_items = round(
        sum(i.total_weight for i in doc.items if i.row_print_style != "Hide Row" and i.row_type == ""), 1
    )
    doc.qty_of_visible_items = sum(
        i.qty for i in doc.items if i.row_print_style != "Hide Row" and i.row_type == ""
    )
    doc.surface_of_visible_items = 0

    items = []
    for item in doc.items:
        item_data = {
            "name": item.name,
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description,
            "qty": item.qty,
            "uom": item.uom,
            "rate": item.rate,
            "amount": item.amount,
            "row_type": item.row_type,
            "row_print_style": item.row_print_style,
            "total_weight": getattr(item, "total_weight", None),
            "bom_no": item.bom_no,
            "reference_ligne": getattr(item, "reference_ligne", None),
            "price_par_surface": getattr(item, "price_par_surface", None),
            "hauteur": None,
            "largeur": None,
            "surface": None,
        }
        if item.bom_no:
            bom = frappe.db.get_value("BOM", item.bom_no, ["reference_ligne", "hauteur", "largeur"])
            if bom:
                reference_ligne, hauteur, largeur = bom
                item_data["reference_ligne"] = reference_ligne
                surface = (hauteur or 0) / 1000 * (largeur or 0) / 1000
                item_data["price_par_surface"] = round(item.rate / surface, 2) if surface else 0
                item_data["hauteur"] = hauteur
                item_data["largeur"] = largeur
                item_data["surface"] = round(surface, 4)
                doc.surface_of_visible_items = round(
                    doc.surface_of_visible_items + (item.qty or 0) * surface, 2
                )
        items.append(item_data)

    # Taxes
    taxes = [
        {
            "description": t.description,
            "rate": t.rate,
            "tax_amount": t.tax_amount,
            "total": t.total,
            "account_head": t.account_head,
        }
        for t in (doc.taxes or [])
    ]

    frappe.response["message"] = {
        # Identité
        "name": doc.name,
        "status": doc.status,
        "transaction_date": str(doc.transaction_date) if doc.transaction_date else None,
        "valid_till": str(doc.valid_till) if doc.valid_till else None,
        "company": doc.company,
        "cost_center": getattr(doc, "cost_center", None),
        # Client
        "customer_name": doc.customer_name,
        "customer": doc.party_name,
        "contact_person": doc.contact_person,
        "contact_mobile": doc.contact_mobile,
        "contact_email": doc.contact_email,
        "customer_address": doc.customer_address,
        "address_display": doc.address_display,
        # Projet
        "project": getattr(doc, "project", None),
        # Totaux
        "total": doc.total,
        "discount_amount": doc.discount_amount,
        "grand_total": doc.grand_total,
        "rounding_adjustment": doc.rounding_adjustment,
        "rounded_total": doc.rounded_total,
        "currency": doc.currency,
        # Résumé (calculé comme au print)
        "weight_of_visible_items": doc.weigth_of_visible_items,
        "qty_of_visible_items": doc.qty_of_visible_items,
        "surface_of_visible_items": doc.surface_of_visible_items,
        # Lignes
        "items": items,
        "taxes": taxes,
        # Conditions
        "terms": doc.terms,
        # Champs personnalisés
        "custom_quotation_approval_link": getattr(doc, "custom_quotation_approval_link", None),
        "custom_probabilite_de_conversion": getattr(doc, "custom_probabilite_de_conversion", None),
        "custom_expected_amount": getattr(doc, "custom_expected_amount", None),
        "custom_dernier_statut_de_suivi": getattr(doc, "custom_dernier_statut_de_suivi", None),
        "custom_dernière_description_de_suivi": getattr(doc, "custom_dernière_description_de_suivi", None),
        "custom_insurance": getattr(doc, "custom_insurance", None),
        "custom_insurance_client": getattr(doc, "custom_insurance_client", None),
        "custom_claim_number": getattr(doc, "custom_claim_number", None),
        "custom_insurance_contract_number": getattr(doc, "custom_insurance_contract_number", None),
        "custom_expert_name": getattr(doc, "custom_expert_name", None),
        "custom_expert_tel": getattr(doc, "custom_expert_tel", None),
        "custom_expert_email": getattr(doc, "custom_expert_email", None),
    }
