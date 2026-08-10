"""Événements du document Timesheet.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_insert(doc, method=None):
    # --- depuis Server Script « Feuille de temps valeur par défaut » (Before Insert) ---
    if doc.company == "Vitrerie Stéphanoise":
        doc.custom_lunchbox = 1


def validate(doc, method=None):
    # --- depuis Server Script « Feuille de temps arrondi » (Before Save) ---
    total_hours = 0
    for row in doc.time_logs:
        # Arrondi pour from_time si non None
        if row.custom_fiche_de_travail:
            custom_fiche_de_travail_status = frappe.db.get_value("Fiche de travail", row.custom_fiche_de_travail, "status")
            if custom_fiche_de_travail_status == "À faire" or custom_fiche_de_travail_status == "En attente de fabrication":
                frappe.db.set_value("Fiche de travail", row.custom_fiche_de_travail, "status", "En cours")
        if row.from_time:
            from_time_dt = frappe.utils.get_datetime(row.from_time)  # Convertit en datetime si string
            minutes = from_time_dt.minute
            rounded_minutes = round(minutes / 15.0) * 15
            delta = rounded_minutes - minutes
            row.from_time = frappe.utils.add_to_date(from_time_dt, minutes=delta, as_datetime=True)

        # Arrondi pour to_time si non None
        if row.to_time:
            to_time_dt = frappe.utils.get_datetime(row.to_time)  # Convertit en datetime si string
            minutes = to_time_dt.minute
            rounded_minutes = round(minutes / 15.0) * 15
            delta = rounded_minutes - minutes
            row.to_time = frappe.utils.add_to_date(to_time_dt, minutes=delta, as_datetime=True)

        # Recalcul des heures seulement si les deux temps sont définis
        if row.from_time and row.to_time:
            # Assurons-nous qu'ils sont en datetime pour le calcul
            from_time_dt = frappe.utils.get_datetime(row.from_time)
            to_time_dt = frappe.utils.get_datetime(row.to_time)
            row.hours = frappe.utils.time_diff_in_hours(to_time_dt, from_time_dt)
        else:
            row.hours = 0.0  # Ou None si préféré
        total_hours = total_hours + row.hours
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
        if row.activity_type == "Chantier" and not row.project:
            frappe.throw(
                f"Ligne {row.idx} : Un projet est obligatoire pour le type d'activité 'Chantier'"
            )


def on_submit(doc, method=None):
    # --- depuis Server Script « Feuille de temps validation » (After Submit) ---
    doc.custom_day_finished = True
    time_per_ft = {}
    for tl in doc.time_logs:
        if tl.custom_fiche_de_travail:
            time_per_ft[tl.custom_fiche_de_travail] = 0
            if tl.custom_fiche_de_travail not in time_per_ft:
                time_per_ft[tl.custom_fiche_de_travail] = 0
            time_per_ft[tl.custom_fiche_de_travail] = time_per_ft[tl.custom_fiche_de_travail] + tl.hours

    for k in time_per_ft:
        time_spent = max(0, frappe.db.get_value("Fiche de travail", k, "time_spent"))
        labor_costs = max(0, frappe.db.get_value("Fiche de travail", k, "labor_costs"))

        percentage_of_time = time_per_ft[k]/doc.total_hours
        frappe.db.set_value("Fiche de travail", k, "labor_costs", round(labor_costs + percentage_of_time*doc.total_costing_amount, 2))
        frappe.db.set_value("Fiche de travail", k, "time_spent", round(time_spent+time_per_ft[k], 2))


def on_cancel(doc, method=None):
    # --- depuis Server Script « Feuille de temps annulation » (After Cancel) ---
    time_per_ft = {}
    for tl in doc.time_logs:
        if tl.custom_fiche_de_travail:
            time_per_ft[tl.custom_fiche_de_travail] = 0
            if tl.custom_fiche_de_travail not in time_per_ft:
                time_per_ft[tl.custom_fiche_de_travail] = 0
            time_per_ft[tl.custom_fiche_de_travail] = time_per_ft[tl.custom_fiche_de_travail] + tl.hours

    for k in time_per_ft:
        time_spent = max(0, frappe.db.get_value("Fiche de travail", k, "time_spent"))
        labor_costs = max(0, frappe.db.get_value("Fiche de travail", k, "labor_costs"))
        percentage_of_time = time_per_ft[k]/doc.total_hours
        frappe.db.set_value("Fiche de travail", k, "labor_costs", round(labor_costs - percentage_of_time*doc.total_costing_amount, 2))
        frappe.db.set_value("Fiche de travail", k, "time_spent", round(time_spent-time_per_ft[k], 2))
