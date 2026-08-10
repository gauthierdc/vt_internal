"""Tâche planifiée « Client récurrent » (fréquence : Daily).

Convertie depuis le Server Script ERP (type « Scheduler Event »).
Câblage de la fréquence dans hooks.py (scheduler_events).
Source de vérité : ce fichier (versionné). Le record DB a été supprimé.
"""

import frappe


def update_recurring_customer_status():
    # Ce script identifie les clients ayant passé plus de deux commandes au cours des 12 derniers mois
    # et met à jour leur statut interne de "Ponctuel" à "Récurrent" dans la fiche client.
    # et vice versa


    # Calcul de la date il y a 365 jours
    date_limit = frappe.utils.add_days(frappe.utils.today(), -365)

    # Requête SQL avec le statut client inclus
    results = frappe.db.sql("""
        SELECT so.customer, COUNT(so.name) AS order_count, c.custom_internal_status
        FROM `tabSales Order` so
        JOIN `tabCustomer` c ON so.customer = c.name
        WHERE so.docstatus = 1 AND so.transaction_date >= %s
        GROUP BY so.customer, c.custom_internal_status
        HAVING COUNT(so.name) > 2 AND c.custom_internal_status = 'Ponctuel'
    """, (date_limit,), as_dict=True)

    # Mise à jour des clients
    for row in results:
        customer = frappe.get_doc("Customer", row.customer)
        customer.custom_internal_status = "Récurrent"
        customer.add_comment("Comment", f"Le client a effectué plus de deux commandes cette année : son statut passe de <b>Ponctuel</b> à <b>Récurrent</b>.")
        customer.save()

    # Requête SQL avec le statut client inclus
    results = frappe.db.sql("""
        SELECT so.customer, COUNT(so.name) AS order_count, c.custom_internal_status
        FROM `tabSales Order` so
        JOIN `tabCustomer` c ON so.customer = c.name
        WHERE so.docstatus = 1 AND so.transaction_date >= %s
        GROUP BY so.customer, c.custom_internal_status
        HAVING COUNT(so.name) < 2 AND c.custom_internal_status = 'Récurrent'
    """, (date_limit,), as_dict=True)

    # Mise à jour des clients
    for row in results:
        customer = frappe.get_doc("Customer", row.customer)
        customer.custom_internal_status = "Ponctuel"
        customer.add_comment("Comment", f"Le client a effectué moins de trois commandes cette année : son statut passe de <b>Récurrent</b> à <b>Ponctuel</b>.")
        customer.save()
