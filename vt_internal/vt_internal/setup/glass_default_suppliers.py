# Copyright (c) 2026, Verre & Transparence and contributors
"""Écrit les Item Group Defaults « fournisseur par défaut » des verres.

Source de vérité unique : ``RULES`` ci-dessous. Idempotent, NON lancé au
migrate. Usage :

	bench --site <site> execute vt_internal.vt_internal.setup.glass_default_suppliers.run
	bench --site <site> execute vt_internal.vt_internal.setup.glass_default_suppliers.run --kwargs "{'dry_run': 0}"
	# seulement les 4 lignes « racine » (sans copie dans les sous-groupes) :
	... --kwargs "{'dry_run': 0, 'include_subgroups': 0}"

Règle maison : un correctif de masse ne doit JAMAIS changer ``modified``.
→ insertion des lignes enfant via ``Document.db_insert()`` (pas de save du
parent, pas de hook, ``modified`` du Item Group intact) et mise à jour via
``frappe.db.set_value(..., update_modified=False)``.

Pourquoi copier dans les sous-groupes : le natif ERPNext
(``get_item_group_defaults``) ne lit que le groupe DIRECT de l'article pour
Commande fournisseur / Demande de matériel. vt_internal remonte l'arbre
(``utils.item_defaults``), mais pour que le natif marche aussi on écrit la
même valeur sur chaque sous-groupe. Un sous-groupe plus spécifique de RULES
gagne (on traite les règles de la plus profonde à la moins profonde).
"""

import frappe

MAV = "Miroiterie Avignonnaise"
VS = "Vitrerie Stéphanoise"

# (groupe racine, société, fournisseur)
RULES = [
	("Verres trempés - feuilletés trempés", MAV, "08BMV000"),
	("Verres trempés - feuilletés trempés", VS, "08BMV000"),
	("Verres", MAV, "INTERNE MAV"),
	("Verres", VS, "INTERNE"),
]


def plan(include_subgroups=True):
	"""Retourne {(groupe, société): fournisseur} attendu."""
	target = {}
	# plus profond d'abord (lft le plus grand) → il gagne
	rules = sorted(RULES, key=lambda r: -frappe.db.get_value("Item Group", r[0], "lft"))
	for group, company, supplier in rules:
		lft, rgt = frappe.db.get_value("Item Group", group, ["lft", "rgt"])
		groups = (
			frappe.get_all("Item Group", filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, pluck="name")
			if include_subgroups
			else [group]
		)
		for g in groups:
			target.setdefault((g, company), supplier)
	return target


def run(dry_run=1, include_subgroups=1):
	dry_run, include_subgroups = int(dry_run), int(include_subgroups)
	for g, c, s in RULES:
		for dt, n in (("Item Group", g), ("Company", c), ("Supplier", s)):
			if not frappe.db.exists(dt, n):
				frappe.throw(f"{dt} introuvable : {n}")

	report = {"insert": [], "update": [], "ok": []}
	for (group, company), supplier in sorted(plan(include_subgroups).items()):
		existing = frappe.db.get_value(
			"Item Default",
			{"parenttype": "Item Group", "parentfield": "item_group_defaults", "parent": group, "company": company},
			["name", "default_supplier"],
			as_dict=True,
		)
		if existing and existing.default_supplier == supplier:
			report["ok"].append((group, company, supplier))
			continue
		if existing:
			report["update"].append((group, company, existing.default_supplier, supplier))
			if not dry_run:
				frappe.db.set_value("Item Default", existing.name, "default_supplier", supplier, update_modified=False)
			continue
		report["insert"].append((group, company, supplier))
		if not dry_run:
			idx = (
				frappe.db.sql(
					"select max(idx) from `tabItem Default` where parenttype='Item Group' and parent=%s",
					group,
				)[0][0]
				or 0
			)
			child = frappe.get_doc(
				{
					"doctype": "Item Default",
					"parenttype": "Item Group",
					"parentfield": "item_group_defaults",
					"parent": group,
					"idx": idx + 1,
					"company": company,
					"default_supplier": supplier,
				}
			)
			child.db_insert()  # n'altère pas le modified du Item Group

	if not dry_run:
		frappe.db.commit()
		frappe.clear_cache(doctype="Item Group")
	print(
		f"{'[DRY RUN] ' if dry_run else ''}insert={len(report['insert'])} "
		f"update={len(report['update'])} déjà_ok={len(report['ok'])}"
	)
	for k in ("insert", "update"):
		for row in report[k]:
			print(k, row)
	return report
