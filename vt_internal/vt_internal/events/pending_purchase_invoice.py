"""Événements du document Pending Purchase Invoice.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_insert(doc, method=None):
    # --- depuis Server Script « Facture d'achat en attente création » (Before Insert) ---
    grand_total = doc.supplier_grand_total or 0
    tax_amount = doc.supplier_tax_amount or 0
    net_amount = doc.supplier_net_amount or 0

    # 1) Cas deviné : TVA fixe 20% → recalcul TTC
    if grand_total == 0 and tax_amount == 20:
        doc.supplier_grand_total = round(net_amount * 1.2, 2)

    # 2) Cas où le HT = TTC → TTC = HT + TVA
    elif net_amount == grand_total and tax_amount > 0:
        doc.supplier_grand_total = round(net_amount + tax_amount, 2)
