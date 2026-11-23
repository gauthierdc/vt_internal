"""Texte public de paiement par carte pour le Web Form bon-pour-accord-devis.

Le formulaire est custom (en base, is_standard = 0). On ne le versionne pas :
un Web Form standard écraserait les éditions de Solène. Le client lit
uniquement la phrase ci-dessous. Aucun autre champ de Quotation n'est renvoyé.
"""

from __future__ import annotations

import html

import frappe

# Company.custom_texte_paiement_cb — créé par le patch set_texte_paiement_cb.
TEXTE_PAIEMENT_CB_FIELD = "custom_texte_paiement_cb"
_MAX_QUOTATION_NAME = 140


def _quotation_name(quotation) -> str:
	"""Nom de devis utilisable en paramètre, ou chaîne vide."""
	if not isinstance(quotation, str):
		return ""
	name = quotation.strip()
	if not name or len(name) > _MAX_QUOTATION_NAME:
		return ""
	if any(ord(char) < 32 for char in name):
		return ""
	return name


def _escape(text: str) -> str:
	"""Échappe le texte société. Repli stdlib si l'échappement Frappe laisse des chevrons."""
	escaped = frappe.utils.escape_html(text)
	if not isinstance(escaped, str):
		escaped = str(escaped)
	if "<" in escaped or ">" in escaped:
		return html.escape(text, quote=True)
	return escaped


def _texte_for_quotation(quotation) -> str:
	name = _quotation_name(quotation)
	if not name:
		return ""
	company = frappe.db.get_value("Quotation", name, "company")
	if not company:
		return ""
	raw = frappe.db.get_value("Company", company, TEXTE_PAIEMENT_CB_FIELD) or ""
	if not isinstance(raw, str):
		raw = str(raw)
	text = raw.strip()
	if not text:
		return ""
	return _escape(text)


@frappe.whitelist(allow_guest=True)
def get_texte_paiement_cb(quotation: str | None = None) -> str:
	"""Phrase CB de la société du devis, échappée, ou chaîne vide.

	Chaîne vide si le paramètre manque, si le devis est inconnu, ou si la
	société n'a pas de texte : le formulaire garde alors la phrase générique.
	Une erreur base ne remonte pas au visiteur (même repli).
	"""
	try:
		return _texte_for_quotation(quotation)
	except Exception:
		try:
			frappe.log_error(title="Texte paiement CB", message=frappe.get_traceback())
		except Exception:
			pass
		return ""
