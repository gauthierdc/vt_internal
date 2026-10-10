# Copyright (c) 2026, Verre & Transparence and contributors
"""Fournisseur par défaut d'un article, avec héritage dans l'arbre des groupes.

Ordre de résolution (``get_default_supplier``) :
1. Item Default de l'article pour la société ;
2. Item Group Defaults du groupe direct, puis des groupes parents jusqu'à la
   racine (premier ``default_supplier`` trouvé pour la société) ;
3. Brand Defaults de la marque de l'article ;
4. sinon ``None``.

Contrairement à ERPNext natif (``get_item_group_defaults`` ne lit que le
groupe direct), on remonte l'arbre : une ligne sur « Verres » couvre tous les
sous-groupes, une ligne sur un sous-groupe la surcharge.

Configuration : uniquement dans l'UI (Groupe d'articles › Valeurs par défaut,
Article › Valeurs par défaut). Utilisé par les règles verretransparence
« (Sélection automatique du fournisseur interne) » et « Double vitrage »
via ``frappe.call(...)`` (Dodock n'a pas de hook de globals sandbox).
"""

import frappe

MAX_DEPTH = 50  # garde-fou contre une boucle dans l'arbre


def resolve_default_supplier(item, company, get_defaults_supplier, get_parent_group):
	"""Logique pure (testable sans site).

	item : dict avec ``name``, ``item_group``, ``brand``.
	get_defaults_supplier(parenttype, parent, company) -> str | None
	get_parent_group(group) -> str | None

	>>> rows = {("Item Group", "Verres", "MAV"): "INTERNE MAV"}
	>>> tree = {"Verres float": "Verres", "Verres": "Miroiterie", "Miroiterie": None}
	>>> f = lambda pt, p, c: rows.get((pt, p, c))
	>>> resolve_default_supplier({"name": "X", "item_group": "Verres float"}, "MAV", f, tree.get)
	'INTERNE MAV'
	>>> resolve_default_supplier({"name": "X", "item_group": "Verres float"}, "EDC", f, tree.get) is None
	True
	"""
	if not item or not company:
		return None

	supplier = get_defaults_supplier("Item", item.get("name"), company)
	if supplier:
		return supplier

	group, seen = item.get("item_group"), set()
	while group and group not in seen and len(seen) < MAX_DEPTH:
		seen.add(group)
		supplier = get_defaults_supplier("Item Group", group, company)
		if supplier:
			return supplier
		group = get_parent_group(group)

	if item.get("brand"):
		supplier = get_defaults_supplier("Brand", item.get("brand"), company)
		if supplier:
			return supplier
	return None


def _defaults_supplier(parenttype, parent, company):
	return frappe.db.get_value(
		"Item Default",
		{"parenttype": parenttype, "parent": parent, "company": company},
		"default_supplier",
	)


def _parent_group(group):
	return frappe.get_cached_value("Item Group", group, "parent_item_group")


@frappe.whitelist()
def get_default_supplier(item_code=None, company=None, item=None):
	"""Fournisseur par défaut de ``item_code`` pour ``company`` (ou None).

	Appelable depuis un script serveur / sous-règle (sandbox) :
	``frappe.call("vt_internal.vt_internal.utils.item_defaults.get_default_supplier",
	item_code=doc.verre, company=company)``
	"""
	item_code = item_code or item
	if not item_code or not company:
		return None
	row = frappe.db.get_value("Item", item_code, ["name", "item_group", "brand"], as_dict=True)
	if not row:
		return None
	return resolve_default_supplier(row, company, _defaults_supplier, _parent_group)

