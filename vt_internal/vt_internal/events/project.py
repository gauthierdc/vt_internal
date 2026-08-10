"""Événements du document Project.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Sauvegarde projet » (Before Save) ---
    doc.estimated_costing = (doc.total_expense_claim or 0) + (doc.total_purchase_cost or 0) + sum([f.montant for f in doc.custom_reste_à_facturer])
    doc.sales_order = None
