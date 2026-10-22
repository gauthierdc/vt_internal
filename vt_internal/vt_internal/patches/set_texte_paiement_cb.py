"""Ajoute Company.custom_texte_paiement_cb et renseigne MAV et VS.

Les autres sociétés (EDC SARL, Serrurerie Ferronnerie Métallerie du Luberon,
Vision d'O) restent vides : le bon pour accord affiche la phrase générique,
sans numéro. Un texte déjà saisi n'est pas écrasé.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

TEXTE_PAIEMENT_CB_FIELD = "custom_texte_paiement_cb"

# Coordonnées téléphoniques, pas la phrase entière. Le formulaire public
# les ajoute à « Carte bancaire, à distance il suffit de nous contacter par téléphone. »
TEXTES_PAIEMENT_CB = {
	"Miroiterie Avignonnaise": (
		"04.90.86.63.19 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)"
	),
	"Vitrerie Stéphanoise": (
		"04 77 50 92 29 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)"
	),
}


def insert_after_field(has_quotation_terms: bool) -> str:
	"""À côté des conditions de devis si le champ existe, sinon sous le téléphone."""
	if has_quotation_terms:
		return "custom_quotation_terms"
	return "phone_no"


def _is_blank(value) -> bool:
	if value is None:
		return True
	if not isinstance(value, str):
		value = str(value)
	return not value.strip()


def execute():
	if not frappe.db.table_exists("Company"):
		return
	if not frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": TEXTE_PAIEMENT_CB_FIELD}):
		insert_after = insert_after_field(bool(frappe.db.has_column("Company", "custom_quotation_terms")))
		create_custom_field(
			"Company",
			{
				"fieldname": TEXTE_PAIEMENT_CB_FIELD,
				"label": "Texte paiement CB (bon pour accord)",
				"fieldtype": "Small Text",
				"insert_after": insert_after,
				"translatable": 0,
				"description": (
					"Coordonnées téléphoniques de paiement par carte, affichées sur le "
					"formulaire public bon-pour-accord-devis pour les devis de cette société. "
					"Laisser vide pour garder la phrase générique, sans numéro."
				),
			},
			ignore_validate=True,
			is_system_generated=False,
		)

	if not frappe.db.has_column("Company", TEXTE_PAIEMENT_CB_FIELD):
		return

	for company, text in TEXTES_PAIEMENT_CB.items():
		if not frappe.db.exists("Company", company):
			continue
		current = frappe.db.get_value("Company", company, TEXTE_PAIEMENT_CB_FIELD)
		if not _is_blank(current):
			continue
		frappe.db.set_value("Company", company, TEXTE_PAIEMENT_CB_FIELD, text)
