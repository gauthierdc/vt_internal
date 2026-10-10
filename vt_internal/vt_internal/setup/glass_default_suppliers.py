# Copyright (c) 2026, Verre & Transparence and contributors
"""Écrit les Item Group Defaults « fournisseur par défaut » des verres.

Source de vérité unique : constantes ci-dessous. Idempotent, NON lancé au
migrate. Usage :

	bench --site <site> execute vt_internal.vt_internal.setup.glass_default_suppliers.run
	bench --site <site> execute vt_internal.vt_internal.setup.glass_default_suppliers.run --kwargs "{'dry_run': 0}"
	# sans recopier la ligne trempé dans son sous-arbre (2 lignes au lieu de 12) :
	... --kwargs "{'dry_run': 0, 'include_subgroups': 0}"
	# liste d'exclusion personnalisée :
	... --kwargs "{'dry_run': 0, 'excluded': ['Menuiserie', 'Miroir']}"

Règle maison : un correctif de masse ne doit JAMAIS changer ``modified``.
→ insertion des lignes enfant via ``Document.db_insert()`` (pas de save du
parent, pas de hook, ``modified`` du Item Group intact) et mise à jour via
``frappe.db.set_value(..., update_modified=False)``.

Pourquoi copier dans les sous-groupes : le natif ERPNext
(``get_item_group_defaults``) ne lit que le groupe DIRECT de l'article pour
Commande fournisseur / Demande de matériel. vt_internal remonte l'arbre
(``utils.item_defaults``), mais pour que le natif marche aussi on écrit la
même valeur sur chaque sous-groupe. Les groupes EXCLUDED restent vides.
"""

import frappe

MAV = "Miroiterie Avignonnaise"
VS = "Vitrerie Stéphanoise"

# Sous-arbre trempé : une ligne sur le groupe de tête, tout le sous-arbre hérite.
TEMPERED_ROOT = "Verres trempés - feuilletés trempés"
TEMPERED_RULES = {MAV: "08BMV000", VS: "08BMV000"}

# Verres « internes » : PAS de ligne sur « Verres » lui-même (sinon les groupes
# exclus hériteraient via get_default_supplier). Une ligne sur chaque vrai
# sous-groupe verre du sous-arbre GLASS_ROOT, hors TEMPERED_ROOT et hors EXCLUDED.
GLASS_ROOT = "Verres"
GLASS_RULES = {MAV: "INTERNE MAV", VS: "INTERNE"}

# Groupes (et tout leur sous-arbre) qui doivent rester SANS fournisseur par
# défaut, en natif (PO/MR) comme dans get_default_supplier. Leurs ancêtres
# dans l'arbre Verres (ex. « Verres monolithiques », « Verres filmés ») ne
# reçoivent pas non plus de ligne, sinon l'héritage la leur transmettrait.
EXCLUDED = [
	"Menuiserie",
	"Miroir",
	"Laqué",
	"Autres miroir",
	"Miroirs filmés",
]


def _subtree(group):
	lft, rgt = frappe.db.get_value("Item Group", group, ["lft", "rgt"])
	return frappe.get_all("Item Group", filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, pluck="name")


def _ancestors(group):
	out, g = [], frappe.db.get_value("Item Group", group, "parent_item_group")
	while g:
		out.append(g)
		g = frappe.db.get_value("Item Group", g, "parent_item_group")
	return out


def plan(include_subgroups=True, excluded=None):
	"""Retourne {(groupe, société): fournisseur} attendu."""
	excluded = EXCLUDED if excluded is None else excluded
	target = {}

	tempered = set(_subtree(TEMPERED_ROOT))
	for g in tempered if include_subgroups else [TEMPERED_ROOT]:
		for company, supplier in TEMPERED_RULES.items():
			target[(g, company)] = supplier

	skip = {GLASS_ROOT} | tempered
	for ex in excluded:
		if not frappe.db.exists("Item Group", ex):
			continue
		skip |= set(_subtree(ex))
		skip |= set(_ancestors(ex))
	for g in _subtree(GLASS_ROOT):
		if g in skip:
			continue
		for company, supplier in GLASS_RULES.items():
			target[(g, company)] = supplier
	return target


def run(dry_run=1, include_subgroups=1, excluded=None):
	dry_run, include_subgroups = int(dry_run), int(include_subgroups)
	checks = [("Item Group", TEMPERED_ROOT), ("Item Group", GLASS_ROOT)]
	for rules in (TEMPERED_RULES, GLASS_RULES):
		checks += [("Company", c) for c in rules] + [("Supplier", s) for s in rules.values()]
	for dt, n in checks:
		if not frappe.db.exists(dt, n):
			frappe.throw(f"{dt} introuvable : {n}")

	report = {"insert": [], "update": [], "ok": []}
	for (group, company), supplier in sorted(plan(include_subgroups, excluded).items()):
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
