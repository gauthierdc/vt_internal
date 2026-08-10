"""Promeut 11 DocTypes custom en DocTypes d'app `vt_internal`.

Contexte : ces doctypes étaient `custom=1` (créés via l'interface). Lors d'un
`migrate`, Frappe **n'écrase pas** un DocType `custom=1` avec le fichier d'app
correspondant — le simple sync ne bascule donc jamais `custom` à 0 tout seul.

Ce patch force explicitement `custom=0` + `module="VT internal"`, puis recharge
le schéma depuis le disque (`reload_doc(..., force=True)`) pour chaque doctype.
Le schéma sur disque a été exporté depuis la prod → aucun champ perdu.

Idempotent : ré-exécutable sans effet de bord.
"""

import frappe

# nom du DocType -> nom de dossier (scrub)
DOCTYPES = {
    "Fiche de travail": "fiche_de_travail",
    "Carte de travail VT": "carte_de_travail_vt",
    "Quality Incident": "quality_incident",
    "Fabrication VT": "fabrication_vt",
    "BMV settings": "bmv_settings",
    "Consolidated invoice": "consolidated_invoice",
    "Order Satisfaction": "order_satisfaction",
    "Production statement": "production_statement",
    "VT Objective": "vt_objective",
    "Work Completion Receipt": "work_completion_receipt",
    "Quotation Approval": "quotation_approval",
}


def execute():
    # 1. Forcer custom=0 + module en base (Frappe refuse d'écraser un custom=1)
    for name in DOCTYPES:
        if frappe.db.exists("DocType", name):
            frappe.db.set_value(
                "DocType",
                name,
                {"custom": 0, "module": "VT internal"},
                update_modified=False,
            )

    frappe.clear_cache()

    # 2. Recharger le schéma depuis les fichiers de l'app vt_internal
    for name, scrub in DOCTYPES.items():
        if frappe.db.exists("DocType", name):
            frappe.reload_doc("vt_internal", "doctype", scrub, force=True)

    frappe.db.commit()
    frappe.logger().info(f"promote_custom_doctypes: {len(DOCTYPES)} doctypes promus en app")
