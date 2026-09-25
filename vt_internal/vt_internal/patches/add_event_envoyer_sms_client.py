"""Ajoute le champ Event.custom_envoyer_sms_client (case à cocher SMS J-1).

MAV : envoi auto (défaut coché) → on pré-remplit les événements futurs MAV.
VS / autres : défaut décoché (l'utilisateur doit cocher).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import today


MAV = "Miroiterie Avignonnaise"


def execute():
	if not frappe.db.exists("Custom Field", {"dt": "Event", "fieldname": "custom_envoyer_sms_client"}):
		create_custom_field(
			"Event",
			{
				"fieldname": "custom_envoyer_sms_client",
				"label": "Envoyer SMS client (veille)",
				"fieldtype": "Check",
				"insert_after": "custom_company",
				"default": "0",
				"description": (
					"Si coché, un SMS de rappel est envoyé la veille à 18h "
					"(MAV : coché par défaut ; VS : à cocher manuellement)."
				),
			},
			ignore_validate=True,
			is_system_generated=False,
		)

	# Backfill : événements futurs MAV (fiche ou VT) → SMS activé, aligné sur le défaut métier.
	if frappe.db.has_column("Event", "custom_envoyer_sms_client"):
		frappe.db.sql(
			"""
			UPDATE `tabEvent`
			SET custom_envoyer_sms_client = 1
			WHERE custom_company = %s
			  AND starts_on >= %s
			  AND IFNULL(status, '') != 'Cancelled'
			  AND (
			  	IFNULL(custom_fiche_de_travail, '') != ''
			  	OR IFNULL(custom_visite_technique, '') != ''
			  )
			  AND IFNULL(custom_envoyer_sms_client, 0) = 0
			""",
			(MAV, today()),
		)
