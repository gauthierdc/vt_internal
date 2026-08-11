"""Supprime en base les DocTypes dépréciés dont le code a été retiré de l'app.

Retirer le dossier d'un DocType ne le supprime PAS en base : `bench migrate`
ne nettoie jamais un DocType devenu orphelin (sa définition, sa table et ses
documents restent). Ce patch propage la suppression partout (prod comprise) au
prochain migrate.

DocTypes concernés :
- VT Bot / PO Acknowledgment : agent IA E2B/Claude Code sur AR fournisseur, abandonné ;
- Label Printer / Label Printing Log : impression d'étiquettes, abandonnée.

`force=True` droppe aussi la table (donc les documents). Idempotent
(safe_delete ignore l'absence).
"""

import frappe

DOCTYPES = [
    "PO Acknowledgment",
    "VT Bot",
    "Label Printing Log",
    "Label Printer",
]


def safe_delete(name):
    try:
        frappe.delete_doc("DocType", name, ignore_permissions=True, force=True)
    except frappe.DoesNotExistError:
        pass


def execute():
    for name in DOCTYPES:
        safe_delete(name)
    frappe.logger().info(
        f"drop_deprecated_doctypes: {len(DOCTYPES)} doctypes traités"
    )
