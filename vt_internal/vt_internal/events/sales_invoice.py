"""Événements du document Sales Invoice.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_validate(doc, method=None):
    # --- depuis Server Script « Facture de vente ignore pricing rule » (Before Validate) ---
    doc.flags.ignore_pricing_rule = True


def before_insert(doc, method=None):
    # --- depuis Server Script « Facture de vente à la création » (Before Insert) ---
    if doc.customer and not doc.is_down_payment_invoice:
        doc.custom_follow_up_automatically = frappe.db.get_value("Customer", doc.customer, "custom_follow_up_automatically")

    # Contact de facturation lié au client (le plus récent)
    rows = frappe.get_all(
        "Contact",
        filters=[
            ["is_billing_contact", "=", 1],
            ["Dynamic Link", "link_doctype", "=", "Customer"],
            ["Dynamic Link", "link_name", "=", doc.customer],
        ],
        fields=["name", "full_name", "email_id", "phone", "mobile_no"],
    )
    if rows:

        c = rows[0]

        # Si c'est déjà le contact présent sur la facture, ne rien faire
        if doc.contact_person != c["name"]:

            def set_if_diff(field, value):
                if doc.get(field) != value:
                    doc.set(field, value)
            doc.contact_person = c["name"]
            doc.contact_display = c.get("full_name")
            doc.contact_email = c.get("email_id")
            doc.contact_phone = c.get("phone")
            doc.contact_mobile = c.get("mobile_no")


def validate(doc, method=None):
    # --- depuis Server Script « Compte de produit » (Before Save) ---
    naming_series_for_company = {
        "Vision d'O": 'FV/VO-.FY.',
        "Vitrerie Stéphanoise": 'FV/VS-.FY.',
        "Miroiterie Avignonnaise": 'FV/MAV-.FY.',
        "Serrurerie Ferronnerie Métallerie du Luberon": 'FV/SFML-.FY.',
        "EDC SARL": 'FV/EDC-.FY.',
    }
    doc.naming_series = naming_series_for_company[doc.company]
    if doc.custom_type_de_projet is not None and not doc.is_down_payment_invoice:
        t = frappe.db.get_value("Accounting project type", {
            "parent": doc.custom_type_de_projet,
            "company": doc.company,
        }, ["default_product_account"])

        if t is not None:
            if t != "":
                doc.custom_compte_de_produit = t


    if doc.custom_compte_de_produit is not None and doc.custom_compte_de_produit != "" and not doc.is_down_payment_invoice:
        for item in doc.items:
            item.income_account = doc.custom_compte_de_produit

    if doc.custom_insurance:
        doc.custom_follow_up_automatically = 0

    num_of_hours = 0
    for i in doc.items:
        if frappe.db.get_value("Item", i.item_code, "custom_pose_vt"):
            num_of_hours = num_of_hours + i.qty*frappe.db.get_value("Item", i.item_code, "custom_number_of_labor_hours")
    for i in doc.packed_items:
        if frappe.db.get_value("Item", i.item_code, "custom_pose_vt"):
            num_of_hours = num_of_hours + i.qty*frappe.db.get_value("Item", i.item_code, "custom_number_of_labor_hours")
    doc.custom_labour_hours = num_of_hours


def on_submit(doc, method=None):
    # --- depuis Server Script « Cocher livré sur bon de livraison » (After Submit) ---

    # On parcourt chaque ligne de la facture
    for item in doc.items:
        # Vérifie qu'une référence au Delivery Note existe
        if item.delivery_note:
            # Mise à jour du champ custom_livre à 1 (True)
            frappe.db.set_value("Delivery Note", item.delivery_note, "custom_livré", 1)


def before_update_after_submit(doc, method=None):
    # --- depuis Server Script « Après enregistrement » (Before Save (Submitted Document)) ---
    if doc.status == "Paid":
        doc.custom_disputed = 0
        doc.custom_déposé_sur_chorus = 0


def before_print(doc, method=None, print_settings=None, **kwargs):
    # --- depuis Server Script « Avant l'impression » (Before Print) ---
    sales_orders = list(dict.fromkeys([item.sales_order for item in doc.items if item.sales_order]))
    doc.is_consolidated = len(sales_orders) > 1


    if doc.is_consolidated:
        last_sales_order = ""
        for item in doc.items:
            if last_sales_order != item.sales_order and item.sales_order:
                last_sales_order = item.sales_order
                item.display_sales_order = True
                item.reference_piece = frappe.db.get_value("Sales Order", item.sales_order, "reference_piece")


    if doc.is_progress_invoice:
        # 1) Déterminer une Sales Order de référence (s'il y en a une)
        sales_order = None
        for item in doc.items:
            if item.sales_order:
                sales_order = item.sales_order
                break

        # 2) Récupérer les lignes de la commande (peut être vide si aucune SO)
        order_items = []
        if sales_order:
            order_items = frappe.get_all(
                "Sales Order Item",
                filters={"parent": sales_order},
                fields=[
                    "item_code", "item_name", "qty", "rate", "amount", "name",
                    "row_type", "row_print_style", "description", "idx", "with_subtotal"
                ],
                order_by="idx asc"
            )

        # 3) Associer aux factures et calculer les montants facturés
        result = []
        section_items = []
        with_subtotal = False

        for i, item in enumerate(order_items):
            # Mise à jour du flag de sous-total par section si on rencontre un "title1"
            if item.get("row_type") == "title1":
                with_subtotal = bool(item.get("with_subtotal"))

            # Si on démarre une nouvelle section ("title1") et qu'on a accumulé la précédente, pousser son total
            if item.get("row_type") == "title1" and section_items:
                section_total_amount = sum(x["amount"] for x in section_items)
                section_total_invoiced_amount = sum(x["total_invoiced_amount"] for x in section_items)
                section_current_invoiced_amount = sum(x["current_invoiced_amount"] for x in section_items)
                section_remaining_amount = sum(x["remaining_amount"] for x in section_items)
                section_invoiced_percentage = (section_total_invoiced_amount / section_total_amount) * 100 if section_total_amount > 0 else 0
                section_current_percentage = (section_current_invoiced_amount / section_total_amount) * 100 if section_total_amount > 0 else 0

                result.append({
                    "description": "Total Section",
                    "total_invoiced_amount": round(section_total_invoiced_amount, 2),
                    "amount": round(section_total_amount, 2),
                    "invoiced_percentage": round(section_invoiced_percentage, 2),
                    "current_invoiced_amount": round(section_current_invoiced_amount, 2),
                    "current_percentage": round(section_current_percentage, 2),
                    "remaining_amount": round(section_remaining_amount, 2),
                    "row_type": "total",
                    "row_print_style": "",
                    "idx": 0,
                })
                section_items = []

            # Lignes de factures précédentes (uniquement factures de situation validées, avant la présente)
            previous_invoice_items = frappe.db.sql(
                """
                SELECT si_item.parent AS invoice, si_item.qty, si_item.rate, si_item.amount
                FROM `tabSales Invoice Item` si_item
                JOIN `tabSales Invoice` si ON si.name = si_item.parent
                WHERE si_item.so_detail = %s
                  AND si.is_progress_invoice = 1
                  AND si.docstatus = 1
                  AND si.progress_invoice_no < %s
                """,
                (item["name"], doc.progress_invoice_no),
                as_dict=True
            )

            # Lignes de la facture courante pour cet article de commande
            current_invoice_items = frappe.db.sql(
                """
                SELECT si_item.parent AS invoice, si_item.qty, si_item.rate, si_item.amount
                FROM `tabSales Invoice Item` si_item
                JOIN `tabSales Invoice` si ON si.name = si_item.parent
                WHERE si_item.so_detail = %s
                  AND si.name = %s
                """,
                (item["name"], doc.name),
                as_dict=True
            )

            total_invoiced_amount = sum(inv["amount"] for inv in previous_invoice_items)
            invoiced_percentage = (total_invoiced_amount / item["amount"]) * 100 if item["amount"] > 0 else 0

            current_invoiced_amount = sum(inv["amount"] for inv in current_invoice_items)
            current_percentage = (current_invoiced_amount / item["amount"]) * 100 if item["amount"] > 0 else 0

            remaining_amount = round(item["amount"] - (total_invoiced_amount + current_invoiced_amount), 2)

            item_data = {
                **item,
                "invoices": previous_invoice_items + current_invoice_items,
                "total_invoiced_amount": total_invoiced_amount,
                "invoiced_percentage": round(invoiced_percentage, 2),
                "current_invoiced_amount": current_invoiced_amount,
                "current_percentage": round(current_percentage, 2),
                "remaining_amount": remaining_amount
            }

            # Accumuler dans la section si on est dans une section avec sous-totaux et que la ligne n'est pas un titre
            if with_subtotal and item.get("row_type") != "title1":
                section_items.append(item_data)

            result.append(item_data)

        # Si la dernière section doit être totalisée
        if section_items:
            section_total_amount = sum(x["amount"] for x in section_items)
            section_total_invoiced_amount = sum(x["total_invoiced_amount"] for x in section_items)
            section_current_invoiced_amount = sum(x["current_invoiced_amount"] for x in section_items)
            section_remaining_amount = sum(x["remaining_amount"] for x in section_items)
            section_invoiced_percentage = (section_total_invoiced_amount / section_total_amount) * 100 if section_total_amount > 0 else 0
            section_current_percentage = (section_current_invoiced_amount / section_total_amount) * 100 if section_total_amount > 0 else 0

            result.append({
                "description": "Total Section",
                "total_invoiced_amount": round(section_total_invoiced_amount, 2),
                "invoiced_percentage": round(section_invoiced_percentage, 2),
                "amount": round(section_total_amount, 2),
                "current_invoiced_amount": round(section_current_invoiced_amount, 2),
                "current_percentage": round(section_current_percentage, 2),
                "remaining_amount": round(section_remaining_amount, 2),
                "row_type": "total",
                "row_print_style": "",
                "idx": 0,
            })

        # 4) SECTION "Articles hors commande" (items de la facture sans sales_order)
        hors_commande_items = []
        # Titre de section pour cohérence d'affichage
        has_hors_commande = any(not it.sales_order for it in doc.items)
        if has_hors_commande:
            result.append({
                "item_name": "ARTICLES HORS COMMANDE",
                "description": "ARTICLES HORS COMMANDE",
                "row_type": "title1",
                "row_print_style": "",
                "idx": 0,
            })

        for sales_invoice_item in doc.items:
            if not sales_invoice_item.sales_order:
                # Par définition ici, tout est "courant" (sur cette facture)
                current_invoiced_amount = sales_invoice_item.amount

                item_data = {
                    **sales_invoice_item.as_dict(),
                    "invoices": [{
                        "invoice": doc.name,
                        "qty": sales_invoice_item.qty,
                        "rate": sales_invoice_item.rate,
                        "amount": sales_invoice_item.amount
                    }],
                    "total_invoiced_amount": 0,
                    "invoiced_percentage": 0,   # pas de pourcentage antérieur vs SO
                    "current_invoiced_amount": current_invoiced_amount,
                    "current_percentage": 100,  # 100% de ce qui est facturé ici
                    "remaining_amount": 0
                }
                hors_commande_items.append(item_data)
                result.append(item_data)

        # Total de la section "Articles hors commande"
        if hors_commande_items:
            section_total_amount = sum(x["amount"] for x in hors_commande_items)
            section_total_invoiced_amount = sum(x["total_invoiced_amount"] for x in hors_commande_items)
            section_current_invoiced_amount = sum(x["current_invoiced_amount"] for x in hors_commande_items)
            section_remaining_amount = sum(x["remaining_amount"] for x in hors_commande_items)

            result.append({
                "description": "Total Section",
                "amount": round(section_total_amount, 2),
                "total_invoiced_amount": round(section_total_invoiced_amount, 2),
                "invoiced_percentage": 0,
                "current_invoiced_amount": round(section_current_invoiced_amount, 2),
                "current_percentage": 100,
                "remaining_amount": 0,
                "row_type": "total",
                "row_print_style": "",
                "idx": 0,
            })

        # 5) TOTAL GÉNÉRAL (inclut les items hors commande, exclut titres et lignes de total)
        total_amount = sum(i.get("amount", 0) for i in result if not i.get("row_type"))
        total_invoiced_amount = sum(i.get("total_invoiced_amount", 0) for i in result if not i.get("row_type"))
        total_current_invoiced_amount = sum(i.get("current_invoiced_amount", 0) for i in result if not i.get("row_type"))
        total_remaining_amount = sum(i.get("remaining_amount", 0) for i in result if not i.get("row_type"))

        total_invoiced_percentage = (total_invoiced_amount / total_amount) * 100 if total_amount > 0 else 0
        total_current_percentage = (total_current_invoiced_amount / total_amount) * 100 if total_amount > 0 else 0

        result.append({
            "description": "Total Général",
            "amount": round(total_amount, 2),
            "total_invoiced_amount": round(total_invoiced_amount, 2),
            "invoiced_percentage": round(total_invoiced_percentage, 2),
            "current_invoiced_amount": round(total_current_invoiced_amount, 2),
            "current_percentage": round(total_current_percentage, 2),
            "remaining_amount": round(total_remaining_amount, 2),
            "row_type": "total",
            "row_print_style": "",
            "idx": 0,
        })


        doc.sales_order_items = result
