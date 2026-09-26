"""Ajoute le champ Event.custom_envoyer_sms_client (case à cocher SMS J-1).

Règle unique : le SMS part. La case est cochée par défaut pour toutes les
sociétés ; on la décoche sur l'Event pour ne pas envoyer.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import today


def execute():
	if not frappe.db.exists("Custom Field", {"dt": "Event", "fieldname": "custom_envoyer_sms_client"}):
		create_custom_field(
			"Event",
			{
				"fieldname": "custom_envoyer_sms_client",
				"label": "Envoyer SMS client (veille)",
				"fieldtype": "Check",
				"insert_after": "custom_company",
				"default": "1",
				"description": (
					"Si coché, un SMS de rappel est envoyé la veille à 18h. "
					"Coché par défaut pour toutes les sociétés : décocher pour ne pas envoyer."
				),
			},
			ignore_validate=True,
			is_system_generated=False,
		)

	# Backfill : événements futurs (fiche ou VT), toute société → SMS activé.
	if frappe.db.has_column("Event", "custom_envoyer_sms_client"):
		frappe.db.sql(
			"""
			UPDATE `tabEvent`
			SET custom_envoyer_sms_client = 1
			WHERE starts_on >= %s
			  AND IFNULL(status, '') != 'Cancelled'
			  AND (
			  	IFNULL(custom_fiche_de_travail, '') != ''
			  	OR IFNULL(custom_visite_technique, '') != ''
			  )
			  AND IFNULL(custom_envoyer_sms_client, 0) = 0
			""",
			(today(),),
		)
