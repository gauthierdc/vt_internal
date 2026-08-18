"""Utilitaires temps partagés (feuilles de temps / pointage)."""

import frappe


def round_to_quarter(dt):
    """Arrondit un datetime au quart d'heure le plus proche (arrondi banquier).

    Source unique de vérité : utilisée par `timesheet_post_api` (à l'écriture) et
    par l'event `validate` du Timesheet (à l'enregistrement), pour éviter deux
    algorithmes d'arrondi divergents.
    """
    dt = frappe.utils.get_datetime(dt)
    delta = round(dt.minute / 15.0) * 15 - dt.minute
    return frappe.utils.add_to_date(
        dt.replace(second=0, microsecond=0), minutes=delta, as_datetime=True
    )
