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


# Défaut lu par get_user_default("cost_center"). La clé est déjà « scrubbed »,
# donc is_default sur la User Permission ne suffit pas (contrairement à "Cost Center").
COST_CENTER_USER_DEFAULT = "cost_center"


@frappe.whitelist()
def change_cost_center(user=None, cost_center=None):
    # Bloc HTML Desk « Sélecteur de société » : arguments `user` et `cost_center`
    # (/api/method/change_cost_center). Une valeur vide lève la restriction.
    user, desired_cost_center = resolve_cost_center_switch_args(user, cost_center)
    if not user:
        frappe.throw("Utilisateur manquant")
    apply_cost_center_switch(user, desired_cost_center)


def resolve_cost_center_switch_args(user=None, cost_center=None):
    """Kwargs du whitelist, sinon form_dict (mêmes noms que le bloc HTML)."""
    if user is None:
        user = _form_dict_value("user")
    if cost_center is None:
        cost_center = _form_dict_value("cost_center")
    user = str(user).strip() if user else ""
    desired = str(cost_center).strip() if cost_center else ""
    return user, desired


def apply_cost_center_switch(user, desired_cost_center):
    """Pose ou retire la User Permission Cost Center et le défaut utilisateur."""
    current_name = frappe.db.get_value(
        "User Permission",
        {"user": user, "allow": "Cost Center"},
        "name",
    )
    if desired_cost_center:
        if current_name:
            _update_cost_center_permission(user, current_name, desired_cost_center)
        else:
            _insert_cost_center_permission(user, desired_cost_center)
        frappe.defaults.set_user_default(COST_CENTER_USER_DEFAULT, desired_cost_center, user)
    else:
        if current_name:
            frappe.delete_doc("User Permission", current_name, ignore_permissions=True)
        frappe.defaults.clear_user_default(COST_CENTER_USER_DEFAULT, user)
    frappe.cache.hdel("user_permissions", user)


def _update_cost_center_permission(user, name, cost_center):
    # Une seule permission peut être le défaut : on retire le flag des autres
    # avant save(), sinon validate_default_permission rejette le document.
    others = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": "Cost Center",
            "is_default": 1,
            "name": ["!=", name],
        },
        pluck="name",
    )
    for other in others:
        frappe.db.set_value("User Permission", other, "is_default", 0)
    doc = frappe.get_doc("User Permission", name)
    doc.for_value = cost_center
    doc.is_default = 1
    doc.save(ignore_permissions=True)


def _insert_cost_center_permission(user, cost_center):
    doc = frappe.get_doc(
        {
            "doctype": "User Permission",
            "user": user,
            "allow": "Cost Center",
            "for_value": cost_center,
            "apply_to_all_doctypes": 1,
            "is_default": 1,
        }
    )
    doc.insert(ignore_permissions=True)


def _form_dict_value(key):
    form = getattr(frappe, "form_dict", None)
    if form is None:
        return None
    getter = getattr(form, "get", None)
    if not callable(getter):
        return None
    return getter(key)



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
