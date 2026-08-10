"""Endpoints d'administration (permissions société/centre de coût, prix BMV).

Convertis depuis les Server Scripts ERP (type « API »).
URLs courtes historiques préservées via override_whitelisted_methods (hooks.py).
Source de vérité : ces fichiers (versionnés). Les records DB ont été supprimés.
"""

import frappe

@frappe.whitelist()
def change_company():
    # Converti depuis le Server Script API « change_company » (/api/method/change_company).
    user_email = frappe.form_dict.get("user_email")
    desired_companies = frappe.form_dict.desired_companies
    # Manually parse list because we don't have access to parse_json
    desired_companies = desired_companies[1:-1]
    desired_companies = [item.strip(" '\"") for item in desired_companies.split(',') if item.strip(" '\"")]
    print(user_email, desired_companies)

    # 1. Récupérer toutes les permissions "Company" de cet utilisateur
    permissions = frappe.get_all("User Permission", 
        filters={"user": user_email, "allow": "Company"}, 
        pluck="name"
    )
    print(isinstance(desired_companies, list))

    # 2. Supprimer chaque permission une par une
    for perm_name in permissions:
        print(perm_name)
        frappe.delete_doc("User Permission", perm_name, ignore_permissions=True)

    # 2. Ajouter une restriction pour chaque société
    for company in desired_companies:
        print(company)
        doc = frappe.get_doc({
            "doctype": "User Permission",
            "user": user_email,
            "allow": "Company",
            "for_value": company,
            "apply_to_all_doctypes": 1
        })
        doc.insert(ignore_permissions=True)


@frappe.whitelist()
def change_cost_center():
    # Converti depuis le Server Script API « change_cost_center » (/api/method/change_cost_center).

    user = frappe.form_dict.user
    desired_cost_center = frappe.form_dict.cost_center
    current_restriction = frappe.db.get_value("User Permission", {"user": user, "allow": "Cost Center"}, ["name", "for_value"])
    if current_restriction is None and desired_cost_center:
        doc = frappe.get_doc({
            "doctype": "User Permission",
            "user": user,
            "allow": "Cost Center",
            "for_value": desired_cost_center,
            "apply_to_all_doctypes": 1,
        })
        doc.save()
    if current_restriction is not None and not desired_cost_center:
        frappe.delete_doc("User Permission", current_restriction[0])
    if current_restriction is not None and desired_cost_center != "":
        frappe.db.set_value("User Permission", current_restriction[0], "for_value", desired_cost_center)



@frappe.whitelist()
def update_bmv_prices():
    # Converti depuis le Server Script API « update_bmv_prices » (/api/method/update_bmv_prices).
    m_price_13 = float(frappe.form_dict.get("prix_du_m_13_mm"))
    m_price_16 = float(frappe.form_dict.get("prix_du_m_16_mm"))
    m_price_99 = float(frappe.form_dict.get("prix_du_m_99_mm"))

    forme_prices = frappe.db.get_list("VT Prix De Forme", {"custom_prix_bmv": [">", 0]}, ["name", "custom_prix_bmv", "thickness_from," "thickness_to"])
    for p in forme_prices:
        if forme_prices.thickness_to < 13 :
            price = p.custom_prix_bmv*m_price_13
        elif forme_prices.thickness_to < 16 :
            price = p.custom_prix_bmv*m_price_16
        else:
            price = p.custom_prix_bmv*m_price_99

        frappe.db.set_value("VT Prix De Forme", p.name, "price", price)
