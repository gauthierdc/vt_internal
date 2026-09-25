"""Permissions Cost Center sur Purchase Order et Expense.

Avec `apply_strict_user_permissions` = 0, Frappe laisse passer les documents
dont le lien est vide (`ifnull(cost_center, '') = '' OR cost_center IN (...)`).
Un utilisateur qui a une User Permission Cost Center voyait donc les bons de
commande et les notes de frais sans centre de coût.

On ne refait pas le filtre des valeurs autorisées (parent + descendants) :
les User Permissions standard s'en chargent. Ici on exclut seulement le vide.
"""

import frappe

PURCHASE_ORDER = "Purchase Order"
EXPENSE = "Expense"
COST_CENTER = "Cost Center"


def get_purchase_order_permission_query_conditions(user, doctype=None):
	return permission_query_conditions(user, PURCHASE_ORDER)


def get_expense_permission_query_conditions(user, doctype=None):
	return permission_query_conditions(user, EXPENSE)


def permission_query_conditions(user, doctype):
	"""Condition de liste : exclut `cost_center` null ou vide si l'utilisateur est restreint."""
	user = _resolve_user(user)
	if not _restricted_to_cost_center(user, doctype):
		return None
	table = f"`tab{doctype}`"
	return f"({table}.`cost_center` is not null and {table}.`cost_center` != '')"


def has_permission(doc, ptype=None, user=None, debug=False):
	"""Refuse le document sans centre de coût. Ne donne aucun droit supplémentaire.

	Retourner None laisse les User Permissions standard décider (y compris
	les descendants). False bloque uniquement le cost_center vide.
	"""
	if not doc:
		return None
	doctype = getattr(doc, "doctype", None)
	user = _resolve_user(user)
	if not _restricted_to_cost_center(user, doctype):
		return None
	cost_center = doc.get("cost_center") if hasattr(doc, "get") else None
	if cost_center is None or str(cost_center).strip() == "":
		return False
	return None


def _resolve_user(user):
	if user:
		return user
	session = getattr(frappe, "session", None)
	return getattr(session, "user", None) if session is not None else None


def _restricted_to_cost_center(user, doctype):
	"""Vrai si une User Permission Cost Center s'applique à ce doctype.

	`applicable_for` vide = tous les doctypes. Une permission limitée à un
	autre doctype ne restreint pas celui-ci. Les descendants sont déjà
	développés par `get_user_permissions` et portent le même `applicable_for`.
	"""
	if doctype not in (PURCHASE_ORDER, EXPENSE):
		return False
	if not user or user in ("Administrator", "Guest"):
		return False
	permissions = frappe.permissions.get_user_permissions(user).get(COST_CENTER) or []
	for perm in permissions:
		applicable_for = perm.get("applicable_for")
		if not applicable_for or applicable_for == doctype:
			return True
	return False
