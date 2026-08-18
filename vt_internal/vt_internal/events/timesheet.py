"""Événements du document Timesheet.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe

from vt_internal.vt_internal.constants import (
    ACTIVITY_CHANTIER,
    FT_STATUS_IN_PROGRESS,
    FT_STATUSES_TO_START,
)
from vt_internal.vt_internal.utils.time_utils import round_to_quarter


def before_insert(doc, method=None):
    # --- depuis Server Script « Feuille de temps valeur par défaut » (Before Insert) ---
    if doc.company == "Vitrerie Stéphanoise":
        doc.custom_lunchbox = 1


def validate(doc, method=None):
    # --- depuis Server Script « Feuille de temps arrondi » (Before Save) ---
    total_hours = 0
    for row in doc.time_logs:
        # Une fiche pointée passe automatiquement « En cours ».
        if row.custom_fiche_de_travail:
            ft_status = frappe.db.get_value("Fiche de travail", row.custom_fiche_de_travail, "status")
            if ft_status in FT_STATUSES_TO_START:
                frappe.db.set_value("Fiche de travail", row.custom_fiche_de_travail, "status", FT_STATUS_IN_PROGRESS)

        # Arrondi au quart d'heure (algorithme unique, cf. time_utils.round_to_quarter)
        if row.from_time:
            row.from_time = round_to_quarter(row.from_time)
        if row.to_time:
            row.to_time = round_to_quarter(row.to_time)

        # Recalcul des heures seulement si les deux temps sont définis
        if row.from_time and row.to_time:
            row.hours = frappe.utils.time_diff_in_hours(
                frappe.utils.get_datetime(row.to_time),
                frappe.utils.get_datetime(row.from_time),
            )
        else:
            row.hours = 0.0
        total_hours += row.hours
    doc.total_hours = total_hours


def before_submit(doc, method=None):
    # --- depuis Server Script « Avant validation feuille de temps » (Before Submit) ---
    employee = frappe.get_doc("Employee", doc.employee)
    validator_employee = frappe.get_doc("Employee", {
        "user_id": frappe.session.user
    })
    superiors = employee.get_ancestors()

    if validator_employee.name not in superiors:
        frappe.throw(f"Vous n'êtes pas approbateur. Liste des approbateurs: {', '.join(superiors)}")

    for row in doc.time_logs:
        if row.activity_type == ACTIVITY_CHANTIER and not row.project:
            frappe.throw(
                f"Ligne {row.idx} : Un projet est obligatoire pour le type d'activité 'Chantier'"
            )


def _hours_per_fiche(doc):
    """Somme des heures pointées par fiche de travail sur la feuille de temps.

    Correctif : on cumule bien toutes les lignes d'une même fiche (l'ancienne
    version remettait la clé à 0 à chaque itération → seule la dernière ligne comptait).
    """
    time_per_ft = {}
    for tl in doc.time_logs:
        if tl.custom_fiche_de_travail:
            time_per_ft.setdefault(tl.custom_fiche_de_travail, 0)
            time_per_ft[tl.custom_fiche_de_travail] += tl.hours or 0
    return time_per_ft


def _apply_ft_costs(doc, sign):
    """Répartit heures et coûts de main-d'œuvre sur les fiches de travail.

    sign = +1 à la validation, -1 à l'annulation.
    """
    if not doc.total_hours:
        # Rien à répartir sans total (évite une division par zéro).
        return

    for ft, hours in _hours_per_fiche(doc).items():
        time_spent = max(0, frappe.utils.flt(frappe.db.get_value("Fiche de travail", ft, "time_spent")))
        labor_costs = max(0, frappe.utils.flt(frappe.db.get_value("Fiche de travail", ft, "labor_costs")))

        percentage_of_time = hours / doc.total_hours
        cost_delta = sign * percentage_of_time * frappe.utils.flt(doc.total_costing_amount)
        frappe.db.set_value("Fiche de travail", ft, "labor_costs", round(labor_costs + cost_delta, 2))
        frappe.db.set_value("Fiche de travail", ft, "time_spent", round(time_spent + sign * hours, 2))


def on_submit(doc, method=None):
    # --- depuis Server Script « Feuille de temps validation » (After Submit) ---
    doc.custom_day_finished = True
    _apply_ft_costs(doc, sign=1)


def on_cancel(doc, method=None):
    # --- depuis Server Script « Feuille de temps annulation » (After Cancel) ---
    _apply_ft_costs(doc, sign=-1)
