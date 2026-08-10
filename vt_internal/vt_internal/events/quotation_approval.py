"""Événements du document Quotation Approval.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def after_insert(doc, method=None):
    # --- depuis Server Script « Bon pour accord devis » (After Insert) ---
    quotation = frappe.get_doc("Quotation", doc.quotation)
    if not doc.refusal_reason:

        quotation.custom_quotation_approval_description = doc.description
        quotation.custom_signature = doc.signature

    else:
        quotation.status="Lost"
        quotation.custom_quotation_approval_description = doc.description
        quotation.append("custom_status_internes", {
            "statut": "Relance automatique",
            "date": frappe.utils.today(),
            "description": doc.description
        })
        quotation.custom_dernier_statut_de_suivi = "Relance automatique"
        quotation.custom_dernière_description_de_suivi = doc.description,
        quotation.save(ignore_permissions=True)
        quotation.submit()

    quotation.save(ignore_permissions=True)
    doc.submit()
