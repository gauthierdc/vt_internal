"""Événements du document Sales Order.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_validate(doc, method=None):
    # --- depuis Server Script « Ignore pricing rule » (Before Validate) ---
    doc.flags.ignore_pricing_rule = True


def before_insert(doc, method=None):
    # --- depuis Server Script « Rafraichir les termes » (Before Insert) ---
    raw_terms = (frappe.db.get_value("Company", doc.company, "custom_sales_order_terms") or "") + "\n" + (frappe.db.get_value("Cost Center", doc.cost_center, "custom_sales_order_terms") or "")
    # 3. Écrase doc.terms avec le HTML final
    doc.terms = raw_terms


def validate(doc, method=None):
    # --- depuis Server Script « Montant restant dû (avant sauvegarde) » (Before Save) ---


    doc.custom_remaining_amount = doc.grand_total - doc.advance_paid
    doc.total_qty = sum([i.qty if i.row_print_style != "Hide Row" and i.row_type == ""  else 0 for i in doc.items])

    num_of_hours = 0
    for i in doc.items:
        if frappe.db.get_value("Item", i.item_code, "custom_pose_vt"):
            num_of_hours = num_of_hours + i.qty*frappe.db.get_value("Item", i.item_code, "custom_number_of_labor_hours")
    for i in doc.packed_items:
        if frappe.db.get_value("Item", i.item_code, "custom_pose_vt"):
            num_of_hours = num_of_hours + i.qty*frappe.db.get_value("Item", i.item_code, "custom_number_of_labor_hours")
    doc.custom_labour_hours = num_of_hours


    for item in doc.items:
        if not item.project:
            item.project = doc.project
        if not item.cost_center:
            item.cost_center = doc.cost_center

    if doc.project:
        for i in doc.items:
            i.project = doc.project
        updates = {}
        updates["cost_center"] = doc.cost_center
        updates["project_type"] = doc.custom_type_de_projet
        updates["insurance"] = doc.custom_insurance_client
        updates["secteur_vt"] = doc.secteur_vt
        updates["custom_construction_manager"] = doc.custom_construction_manager

        if updates:
            frappe.db.set_value("Project", doc.project, updates)


def before_submit(doc, method=None):
    # --- depuis Server Script « Commande client projet » (Before Submit) ---
    doc.flags.ignore_pricing_rule = True
    doc.payment_schedule = []

    project_name = f"{doc.reference_piece}-{doc.customer_name}-{doc.name}" if doc.reference_piece else f"{doc.customer_name}-{doc.name}"
    if not doc.project:
        project = frappe.get_doc({
            "doctype": "Project",
            "project_name": project_name,
            "company": doc.company,
            "address": doc.shipping_address_name
        })
        project.insert()
        doc.project = project.name
    else:
        frappe.db.set_value("Project", doc.project, "project_name", project_name)
    # Update project in quotations
    quotations = [item.prevdoc_docname for item in doc.items]
    quotations = list(dict.fromkeys(quotations))
    print(quotations)
    for q in quotations:
        frappe.db.set_value("Quotation", q, "project", doc.project)


def on_submit(doc, method=None):
    # --- depuis Server Script « Sales Order automation » (After Submit) ---
    # Update project hours
    hours = frappe.db.sql("""
        SELECT SUM(custom_labour_hours)
        FROM `tabSales Order`
        WHERE docstatus = 1 AND project = %s
    """, (doc.project,))[0][0] or 0

    frappe.db.set_value("Project", doc.project, "custom_estimated_labor_hours", hours)

    # Reprendre les fichiers du devis
    if doc.items[0] and doc.items[0].prevdoc_docname:
        attachments = frappe.get_all("File", filters={
            "attached_to_doctype": "Quotation",
            "attached_to_name": doc.items[0].prevdoc_docname
        }, fields=["name", "file_url", "file_name", "is_private"])
        for att in attachments:
            try:
                frappe.get_doc({
                    "doctype": "File",
                    "file_url": att.file_url,
                    "file_name": att.file_name,
                    "is_private": att.is_private,
                    "attached_to_doctype": "Sales Order",
                    "attached_to_name": doc.name
                }).insert(ignore_permissions=True)
            except Exception:
                pass


def before_update_after_submit(doc, method=None):
    # --- depuis Server Script « Montant restan dû » (Before Save (Submitted Document)) ---
    doc.custom_remaining_amount = doc.grand_total - doc.advance_paid
    #doc.total_qty = sum([i.qty if i.row_print_style != "Hide Row" and i.row_type == ""  else 0 for i in doc.items])

    doc.flags.ignore_pricing_rule = True

    num_of_hours = 0
    for i in doc.items:
        if frappe.db.get_value("Item", i.item_code, "custom_pose_vt"):
            num_of_hours = num_of_hours + i.qty*frappe.db.get_value("Item", i.item_code, "custom_number_of_labor_hours")
    for i in doc.packed_items:
        if frappe.db.get_value("Item", i.item_code, "custom_pose_vt"):
            num_of_hours = num_of_hours + i.qty*frappe.db.get_value("Item", i.item_code, "custom_number_of_labor_hours")
    doc.custom_labour_hours = num_of_hours

    if doc.project:
        for i in doc.items:
            i.project = doc.project
        updates = {}
        updates["cost_center"] = doc.cost_center
        updates["project_type"] = doc.custom_type_de_projet
        updates["insurance"] = doc.custom_insurance_client
        updates["secteur_vt"] = doc.secteur_vt
        updates["custom_construction_manager"] = doc.custom_construction_manager


        if updates:
            frappe.db.set_value("Project", doc.project, updates)


def on_cancel(doc, method=None):
    # --- depuis Server Script « Commande client annulation » (After Cancel) ---
    fabrication_vts = frappe.db.get_list("Fabrication VT", {"customer_order": doc.name})
    for f in fabrication_vts:
        frappe.db.set_value("Fabrication VT", f.name, "status", "Annulé")

    carte_de_travails = frappe.db.get_list("Carte de travail VT", {"customer_order": doc.name})
    for c in carte_de_travails:
        frappe.delete_doc('Carte de travail VT', c.name)

    # update project hours
    hours = frappe.db.sql("""
        SELECT SUM(custom_labour_hours)
        FROM `tabSales Order`
        WHERE docstatus = 1 AND project = %s
    """, (doc.project,))[0][0] or 0

    frappe.db.set_value("Project", doc.project, "custom_estimated_labor_hours", hours)


def on_trash(doc, method=None):
    # --- depuis Server Script « Suppression Commande Client » (Before Delete) ---
    try:
        ft = frappe.db.get_list('Fiche de travail',
            filters={
                'sales_order': doc.name
            }
        )
        for f in ft:
            f_doc = frappe.get_doc("Fiche de travail", f)
            f_doc.sales_order = ""
            f_doc.save()

    except:
        print("Error")


def before_print(doc, method=None, print_settings=None, **kwargs):
    # --- depuis Server Script « Commande client impression » (Before Print) ---


    doc.weigth_of_visible_items = round(sum([i.total_weight if i.row_print_style != "Hide Row" and i.row_type == "" else 0 for i in doc.items]),1)
    doc.qty_of_visible_items = sum([i.qty if i.row_print_style != "Hide Row" and i.row_type == ""  else 0 for i in doc.items])

    if doc.company == "Vitrerie Stéphanoise":
        doc.horraire = frappe.db.get_value("Company", doc.company, "custom_opening_hours")
    for item in doc.items:
        if item.bom_no:
            item.reference_ligne = frappe.db.get_value("BOM", item.bom_no, "reference_ligne")
