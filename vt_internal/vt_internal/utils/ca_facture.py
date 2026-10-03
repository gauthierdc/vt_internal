# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""Définition unique du CA facturé (page Chantiers et script report).

HT : ``tabSales Invoice.total`` (hors taxes, pas le TTC).
Net des avoirs : les factures de retour (``is_return`` = 1) restent dans la
somme. En ERPNext / Dokos leur ``total`` est négatif, donc elles diminuent
le CA. Les acomptes (``is_down_payment_invoice``) restent exclus.
Aucun seuil d'heures estimées : un chantier à 0 h compte dans le CA.

L'alias SQL de la facture doit être ``si``.
"""

# Base de comparaison inférieure à cette part de la valeur courante :
# la variation en % n'est pas interprétable (ex. centre de coût créé en
# cours de période précédente).
VARIATION_MIN_BASE_RATIO = 0.05


def ca_facture_conditions():
	"""Fragments SQL AND-ables. Alias facture : ``si``."""
	return [
		"si.docstatus = 1",
		"(si.is_down_payment_invoice = 0 OR si.is_down_payment_invoice IS NULL)",
	]


def ca_facture_predicate():
	"""Prédicat SQL (sans AND initial) pour toutes les agrégations de CA facturé."""
	return " AND ".join(ca_facture_conditions())


def aggregate_margin(rows):
	"""Marge réelle pondérée d'une sélection de chantiers.

	Chaque ligne expose ``vente`` (base de vente, la même que la marge par
	chantier) et ``cout_reel``. ``pct`` vaut None quand la vente est nulle.
	"""
	vente = sum((r.get("vente") or 0) for r in rows)
	cout = sum((r.get("cout_reel") or 0) for r in rows)
	eur = round(vente - cout)
	if not vente:
		return {"pct": None, "eur": eur, "vente": vente, "cout": cout}
	return {
		"pct": round((vente - cout) / vente * 100),
		"eur": eur,
		"vente": vente,
		"cout": cout,
	}


def period_variation(cur, prev, invert=False):
	"""Libellé de variation vs la période précédente de même durée.

	Retourne ``delta`` (pourcentage arrondi, ou None), ``delta_text``,
	``delta_class`` (``good`` / ``bad`` / ``flat``) et ``insignificant``.

	Affiche « n.s. » quand la base est nulle ou inférieure à 5 % de la
	valeur courante : un pourcentage serait alors non significatif.
	``invert`` marque une baisse comme favorable (coûts, heures SAV).
	"""
	if prev is None:
		return {"delta": None, "delta_text": "", "delta_class": "", "insignificant": False}

	cur_n = float(cur or 0)
	prev_n = float(prev or 0)
	nearly_empty = cur_n != 0 and abs(prev_n) < abs(cur_n) * VARIATION_MIN_BASE_RATIO
	if nearly_empty:
		return {"delta": None, "delta_text": "n.s.", "delta_class": "flat", "insignificant": True}
	if prev_n == 0:
		return {"delta": None, "delta_text": "", "delta_class": "", "insignificant": False}

	pct = round((cur_n - prev_n) / abs(prev_n) * 100)
	if pct > 0:
		delta_text = f"▲ +{pct}%"
	elif pct < 0:
		delta_text = f"▼ {pct}%"
	else:
		delta_text = f"= {pct}%"
	good = (pct <= 0) if invert else (pct >= 0)
	delta_class = "flat" if pct == 0 else ("good" if good else "bad")
	return {"delta": pct, "delta_text": delta_text, "delta_class": delta_class, "insignificant": False}
