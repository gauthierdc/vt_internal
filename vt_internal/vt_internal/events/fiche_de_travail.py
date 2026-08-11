"""Événements du document Fiche de travail.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_insert(doc, method=None):
    # --- depuis Server Script « En-tête Fiche de travail » (Before Insert) ---
    doc.letter_head = frappe.db.get_value("Company", doc.company, "default_letter_head")


def validate(doc, method=None):
    # --- depuis Server Script « Fiche de travail status 2 » (Before Save) ---

    if doc.sav:
        if not doc.référence_pièce.startswith('SAV - '):
            doc.référence_pièce = 'SAV - ' + doc.référence_pièce
    else:
        if doc.référence_pièce.startswith('SAV - '):
            doc.référence_pièce = doc.référence_pièce.replace('SAV - ', '', 1)


    if doc.status == "Fait" and not doc.completion_on:
        doc.completion_on = frappe.utils.today()

    statuses = [item.status for item in doc.items]
    if "⚫️" in statuses:
        doc.avancement = "⚫️"
    if "🔴" in statuses:
        doc.avancement = "🔴"
    elif "🟠" in statuses:
        doc.avancement = "🟠"
    elif "🟢" in statuses:
        doc.avancement = "🟢"
    else: doc.avancement = ""
    if doc.sales_order:
        frappe.db.set_value("Sales Order", doc.sales_order, "custom_statut_fiche_de_travail", doc.status)
    icons = frappe.get_list("Employee", 
        filters={"name": ["in", [t.employé for t in doc.team]]}, 
        fields=["custom_icon"])

    if doc.vehicle:
        vehicule_icon = frappe.db.get_value("Vehicle", doc.vehicle, "custom_icon") or ""
    else:
        vehicule_icon = ""
    doc.calendar_description = "".join([(i.custom_icon or "") for i in icons]) + vehicule_icon + (doc.référence_pièce or "") + (doc.vehicle or "")

    if doc.projet:
        vt = frappe.db.get_value("Visite Technique", {
            "projet": doc.projet
        }, "name")
        if not doc.visite_technique:
            doc.visite_technique = vt


    doc.total_net_weight = round(sum([item.weight_per_unit*item.quantité for item in doc.items]),2)
    doc.total_qty = sum([item.quantité for item in doc.items])
    doc.color = '#2438AF'
    if doc.ends_on and doc.starts_on_2:
        if doc.full_day:
            doc.scheduled_time = max(0,len(doc.team))*doc.number_of_hours_per_day*(frappe.utils.time_diff(doc.ends_on, doc.starts_on_2).days + 1)
        else:
            doc.scheduled_time = round(max(0,len(doc.team)*frappe.utils.time_diff(doc.ends_on, doc.starts_on_2).seconds/3600),2)
    else: 
        doc.scheduled_time = 0


def before_update_after_submit(doc, method=None):
    # --- depuis Server Script « Fiche de travail status à la validation » (Before Save (Submitted Document)) ---

    if doc.sav:
        if not doc.référence_pièce.startswith('SAV - '):
            doc.référence_pièce = 'SAV - ' + doc.référence_pièce
    else:
        if doc.référence_pièce.startswith('SAV - '):
            doc.référence_pièce = doc.référence_pièce.replace('SAV - ', '', 1)



    if doc.status == "Fait" and not doc.completion_on:
        doc.completion_on = frappe.utils.today()


    statuses = [item.status for item in doc.items]
    if "🔴" in statuses:
        doc.avancement = "🔴"
    elif "🟠" in statuses:
        doc.avancement = "🟠"
    elif "🟢" in statuses:
        doc.avancement = "🟢"
    else: doc.avancement = ""

    if doc.sales_order:
        frappe.db.set_value("Sales Order", doc.sales_order, "custom_statut_fiche_de_travail", doc.status)
    doc.total_net_weight = round(sum([item.weight_per_unit*item.quantité for item in doc.items]),2)
    doc.total_qty = sum([item.quantité for item in doc.items])

    icons = frappe.get_list("Employee", 
        filters={"name": ["in", [t.employé for t in doc.team]]}, 
        fields=["custom_icon"])
    if doc.vehicle:
        vehicule_icon = frappe.db.get_value("Vehicle", doc.vehicle, "custom_icon") or ""
    else:
        vehicule_icon = ""
    doc.calendar_description = "".join([(i.custom_icon or "") for i in icons]) + vehicule_icon + (doc.référence_pièce or "") + (doc.vehicle or "")

    if doc.projet:
        vt = frappe.db.get_value("Visite Technique", {
            "projet": doc.projet
        }, "name")
        if not doc.visite_technique:
            doc.visite_technique = vt

    doc.color = '#2438AF'
    if doc.ends_on and doc.starts_on_2:
        if doc.full_day:
            doc.scheduled_time = max(0,len(doc.team))*doc.number_of_hours_per_day*(frappe.utils.time_diff(doc.ends_on, doc.starts_on_2).days + 1)
        else:
            doc.scheduled_time = round(max(0,len(doc.team)*frappe.utils.time_diff(doc.ends_on, doc.starts_on_2).seconds/3600),2)
    else: 
        doc.scheduled_time = 0


def on_cancel(doc, method=None):
    # --- depuis Server Script « Fiche de travail avant l'annulation » (After Cancel) ---
    if doc.sales_order:
        doc.status = "Annulé"
        frappe.db.set_value("Sales Order", doc.sales_order, "custom_statut_fiche_de_travail", "")


def on_trash(doc, method=None):
    # --- depuis Server Script « Fiche de travail status » (Before Delete) ---
    if doc.sales_order:
        frappe.db.set_value("Sales Order", doc.sales_order, "custom_statut_fiche_de_travail", "")


def before_print(doc, method=None, print_settings=None, **kwargs):
    # --- depuis Server Script « Impression fiche de travail » (Before Print) ---
    sales_order = frappe.get_doc("Sales Order", doc.sales_order)
