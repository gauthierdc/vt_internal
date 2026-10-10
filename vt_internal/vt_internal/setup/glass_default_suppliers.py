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

Écriture via l'API document standard : ``frappe.get_doc`` → ajout/mise à
jour des lignes (clé = société) → ``doc.save()`` (permissions, validations,
historique Version ; ``modified`` est mis à jour, accepté par Gauthier pour ce
changement de config). Aucun save si rien ne change.

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

# Surcharges par sous-groupe (appliquées à tout son sous-arbre, priment sur
# TEMPERED_RULES / GLASS_RULES). Décisions Gauthier 10/10/2026 (historique ventes).
GROUP_OVERRIDES = {
	("Verres feuilletés trempés", MAV): "08ALPVER",
	("Verres feuilletés trempés", VS): "CONTROL GLASS",
	("Dalles de sol", VS): "08PYROVE",
	# Dalles de sol × MAV : reste 08BMV000 (hérité du sous-arbre trempé)
}

# Item Defaults (default_supplier) sur des articles précis, rangés directement
# dans « Verres » (pas de sous-groupe). Critère : gagnant ≥ 60 % et ≥ 10 lignes
# de Commande client (Sales Order Item.supplier, via la nomenclature).
ITEM_DEFAULTS = {
	("COUPE FEU 30-186", VS): "08PYROVE",  # 53/53 lignes VS
}

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
	for (group, company), supplier in GROUP_OVERRIDES.items():
		for g in _subtree(group) if include_subgroups else [group]:
			target[(g, company)] = supplier
	return target


def _apply(doctype, name, tablefield, rows, dry_run, report):
	"""Pose default_supplier par société sur un document (API standard).

	rows : {company: supplier}. Sauvegarde uniquement si quelque chose change
	(save() normal : permissions, validations, historique Version, ``modified``).
	"""
	doc = frappe.get_doc(doctype, name)
	changed = False
	for company, supplier in sorted(rows.items()):
		row = next((r for r in doc.get(tablefield) or [] if r.company == company), None)
		key = (doctype, name, company)
		if row and row.default_supplier == supplier:
			report["ok"].append((*key, supplier))
			continue
		if row:
			report["update"].append((*key, row.default_supplier, supplier))
			row.default_supplier = supplier
		else:
			report["insert"].append((*key, supplier))
			doc.append(tablefield, {"company": company, "default_supplier": supplier})
		changed = True
	if changed and not dry_run:
		doc.save()


def run(dry_run=1, include_subgroups=1, excluded=None, with_items=1):
	dry_run, include_subgroups = int(dry_run), int(include_subgroups)
	checks = [("Item Group", TEMPERED_ROOT), ("Item Group", GLASS_ROOT)]
	for rules in (TEMPERED_RULES, GLASS_RULES):
		checks += [("Company", c) for c in rules] + [("Supplier", s) for s in rules.values()]
	for (g, c), s in GROUP_OVERRIDES.items():
		checks += [("Item Group", g), ("Company", c), ("Supplier", s)]
	for (i, c), s in ITEM_DEFAULTS.items():
		checks += [("Item", i), ("Company", c), ("Supplier", s)]
	for dt, n in checks:
		if not frappe.db.exists(dt, n):
			frappe.throw(f"{dt} introuvable : {n}")
		if dt == "Supplier" and frappe.db.get_value("Supplier", n, "disabled"):
			frappe.throw(f"Fournisseur désactivé : {n}")

	report = {"insert": [], "update": [], "ok": []}
	by_group = {}
	for (group, company), supplier in plan(include_subgroups, excluded).items():
		by_group.setdefault(group, {})[company] = supplier
	for group in sorted(by_group):
		_apply("Item Group", group, "item_group_defaults", by_group[group], dry_run, report)
	if int(with_items):
		by_item = {}
		for (item, company), supplier in ITEM_DEFAULTS.items():
			by_item.setdefault(item, {})[company] = supplier
		for item in sorted(by_item):
			_apply("Item", item, "item_defaults", by_item[item], dry_run, report)

	if not dry_run:
		frappe.db.commit()
	print(
		f"{'[DRY RUN] ' if dry_run else ''}insert={len(report['insert'])} "
		f"update={len(report['update'])} déjà_ok={len(report['ok'])}"
	)
	for k in ("insert", "update"):
		for row in report[k]:
			print(k, row)
	return report
