"""Endpoints fabrication / production.

Convertis depuis les Server Scripts ERP (type « API »).
URLs courtes historiques préservées via override_whitelisted_methods (hooks.py).
Source de vérité : ces fichiers (versionnés). Les records DB ont été supprimés.
"""

import frappe

from vt_internal.vt_internal.utils.phone import is_french_landline

@frappe.whitelist()
def create_production():
    # Converti depuis le Server Script API « create_production » (/api/method/create_production).
    if frappe.form_dict.get("project"):
        frappe.response['message'] = {
            "project": frappe.form_dict.get("project")
        }
    else:
        project = frappe.get_doc({
            "doctype": "Project",
            "customer": frappe.form_dict.get("customer"),
            "project_name": frappe.form_dict.get("quotation_name").split("/")[-1],
            "company": frappe.form_dict.get("company"),
            "address": frappe.form_dict.get("address")
        })

        project.insert()
        if frappe.form_dict.get("quotation_name"):
            frappe.db.set_value("Quotation", 
                frappe.form_dict.get("quotation_name"), 
                "project", project.name, 
                update_modified = False)
        elif frappe.form_dict.get("sales_order_name"):
            frappe.db.set_value("Sales Order", 
                frappe.form_dict.get("sales_order_name"), 
                "project", project.name, 
                update_modified = False)
            # update corresponding quotations
            quotations = list(dict.fromkeys([item.prevdoc_docname for item in doc.items]))
            for q in quotations:
                frappe.db.set_value("Quotation", q, "project", doc.project, update_modified = False)

        frappe.response['message'] = {
            "project": project.name
        }


@frappe.whitelist()
def new_fabrication():
    # Converti depuis le Server Script API « new_fabrication » (/api/method/new_fabrication).
    sales_order_name = frappe.form_dict.get("sales_order")
    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    items = frappe.form_dict.get("items").split(",")
    delivery_date = frappe.form_dict.get("delivery_date")

    for i in items:
        item = sales_order.items[int(i)]
        bom = frappe.get_doc("BOM", item.bom_no)

        fab = frappe.get_doc({
            'doctype': 'Fabrication VT',
            "manufacturing_costs": item.qty * item.base_unit_cost_price,
            "quantity": item.qty,
            "project": sales_order.project,
            "company": sales_order.company,
            "description": item.description,
            "article": bom.items[0].item_code,
            "client": sales_order.customer,
            "nomenclature": item.bom_no,
            "largeur": bom.largeur,
            "longueur": bom.hauteur,
            "date_de_fin_prévue": delivery_date,
            "row_item_code": item.name,
            "customer_order": sales_order.name,
        })
        fab.insert()

        # Extraire les opérations uniques, en filtrant celles qui sont vides
        unique_operations = list(dict.fromkeys(
            o.operation for o in bom.operations if (o.operation and o.operation != "Opération générique")
        ))

        # S'il y a des opérations, créer des cartes de travail
        for o in unique_operations:
            carte_de_travail = frappe.get_doc({
                "doctype": 'Carte de travail VT',
                "nomenclature": item.bom_no,
                "article": bom.items[0].item_code,
                "operation": o,
                "company": sales_order.company,
                "description": item.description,
                "date_de_fin_prévue": delivery_date,
                "customer_order": sales_order.name,
                "fabrication_vt": fab.name,
                "quantity": item.qty,
            })
            carte_de_travail.insert()


@frappe.whitelist()
def update_manufacturing_status(fabrication=None, carte_travail=None):
    # Converti depuis le Server Script API « Mise à jour des statuts de fabrication » (/api/method/update_manufacturing_status).
    # Les paramètres peuvent être passés en argument (appel interne, ex-`run_script`)
    # ou récupérés depuis form_dict (appel via l'endpoint whitelisted).
    if carte_travail is None:
        carte_travail = frappe.form_dict.get("carte_travail")
    if fabrication is None:
        fabrication = frappe.form_dict.get("fabrication")

    # Mettre à jour les cartes de travail si la fabrication est passé à faite
    if fabrication and fabrication.status == "Fait":
        cartes = frappe.db.get_list('Carte de travail VT',
            filters={
                'fabrication_vt': fabrication.name
            }
        )
        for c in cartes:
            frappe.db.set_value("Carte de travail VT", c, "status", "Fait")



    if not fabrication and carte_travail:
        fabrication = frappe.get_doc("Fabrication VT", carte_travail.fabrication_vt)

    new_fabrication_status = fabrication.status

    if carte_travail:
        if carte_travail.date_de_fin:
            carte_travail.status = "Fait"

        if carte_travail.status == "Fait":
            others = frappe.get_all('Carte de travail VT',
            filters={
                'fabrication_vt': carte_travail.fabrication_vt,
                'status': 'À faire',
                "name": ('!=', carte_travail.name)
            })
            if not others:
                new_fabrication_status = "Fait"
            else:
                new_fabrication_status = 'En cours'
        else:
            others = frappe.get_all('Carte de travail VT',
            filters={
                'fabrication_vt': carte_travail.fabrication_vt,
                'status': 'Fait',
                "name": ('!=', carte_travail.name)
            })
            if not others:
                new_fabrication_status = 'À faire'
            else:
                new_fabrication_status = 'En cours'


    if carte_travail and fabrication.status != new_fabrication_status:
        frappe.db.set_value("Fabrication VT", fabrication.name, "status", new_fabrication_status)


    custom_statut_interne = "⚫️" if new_fabrication_status in ["À faire", "Annulé"] else "🟠" if new_fabrication_status == "En cours" else "🟢"

    fiche_de_travail_item = frappe.db.get_value('Fiche de travaux - Todo', {"row_item_code": fabrication.row_item_code}, "name")
    if fiche_de_travail_item:
        frappe.db.set_value('Fiche de travaux - Todo', fiche_de_travail_item, "status", custom_statut_interne)
    if(frappe.db.get_value('Sales Order Item', fabrication.row_item_code, "custom_statut_interne") != custom_statut_interne):
        frappe.db.set_value('Sales Order Item', fabrication.row_item_code, "custom_statut_interne", custom_statut_interne)
        update_manufacturing_status_in_order(doc=frappe.get_doc("Sales Order", fabrication.customer_order))


@frappe.whitelist()
def update_manufacturing_status_in_order(doc=None):
    # Converti depuis le Server Script API « Mise à jour des statuts de fabrication dans la commande » (sans api_method).
    # `doc` peut être passé en argument (appel interne, ex-`run_script`) ou via form_dict.
    if doc is None:
        doc = frappe.form_dict.doc

    items_status = [el.custom_statut_interne for el in doc.items]
    total_ordered = sum([ 1 if el != "" else 0 for el in items_status])
    if total_ordered > 0:
        total_received = sum([ 1 if el == "🟢" else 0 for el in items_status])
        total_started = sum([ 1 if el == "🟠" or el == "⚫️" else 0 for el in items_status])
        if total_received == 0 and total_started > 0:
            custom_per_received = 5
        else:
            custom_per_received = total_received/total_ordered*100
    else:
        custom_per_received = 0

    if custom_per_received != doc.custom_per_received:
        frappe.db.set_value("Sales Order", doc.name, "custom_per_received", custom_per_received)
        if custom_per_received == 100:
            cts = frappe.db.get_list("Fiche de travail", {
                "sales_order": doc.name,
                "status": "En attente de fabrication",
                "docstatus": ["!=", 2],
            })
            frappe.db.set_value("Sales Order", doc.name, "custom_order_ready_date", frappe.utils.now())

            notification = frappe.get_doc("Notification", "Réception des fabrications")
            doc = frappe.get_doc("Sales Order", doc.name)
            notification.send(doc)

            if doc.custom_auto_notify_delivery_ready_mail:
                notification = frappe.get_doc('Notification', 'Commande prête mail')
                message = frappe.render_template(notification.message, {"doc": doc})
                subject = frappe.render_template(notification.subject, {"doc": doc})
                frappe.sendmail(
                    recipients=[doc.contact_email],
                    subject=subject,
                    message=message,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name
                )
            if doc.custom_auto_create_bl:
                delivery_note = frappe.call("erpnext.selling.doctype.sales_order.sales_order.make_delivery_note", source_name=doc.name)
                delivery_note.insert()
                delivery_note.submit()
            if doc.custom_auto_notify_delivery_ready_sms:
                # AllMySMS refuse les fixes 04 (HTTP 400) : on saute le SMS, le
                # reste du flux (BL, mails, statut fiche) continue.
                if is_french_landline(doc.contact_mobile):
                    frappe.get_doc(
                        {
                            "doctype": "Comment",
                            "comment_type": "Comment",
                            "comment_email": frappe.session.user,
                            "reference_doctype": doc.doctype,
                            "reference_name": doc.name,
                            "comment_by": frappe.session.user_fullname,
                            "content": (
                                f"<u><b>SMS commande prête non envoyé</b></u> : "
                                f"le numéro {doc.contact_mobile} est un fixe 04 "
                                f"(AllMySMS le refuse)."
                            ),
                        }
                    ).insert(ignore_permissions=True)
                else:
                    notification = frappe.get_doc('Notification', 'Commande prête sms')
                    message = frappe.render_template(notification.message, {"doc": doc})
                    frappe.call("frappe.core.doctype.sms_settings.sms_settings.send_sms", receiver_list=[doc.contact_mobile], msg=message)
            if len(cts) > 0:
                if frappe.db.exists("Event",{"project": ["=",doc.project]}):
                    fiche_de_travail_status = "À faire"
                else:
                    fiche_de_travail_status = "À planifier"
                for ct in cts:
                    frappe.db.set_value("Fiche de travail", ct.name, "status", fiche_de_travail_status)
                frappe.db.set_value("Sales Order", doc.name, "custom_statut_fiche_de_travail", fiche_de_travail_status)
