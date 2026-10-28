"""Envoi planifié des Auto Email Reports « Devis relances ».

Horaires (cron dans hooks.py, timezone du site — Europe/Paris) :
  - jeudi 18:30 : Devis relances VS
  - vendredi 18:00 : Devis relances Riviera

Frappe v15 (`AutoEmailReport.send`) n'inspecte pas `enabled`. Seuls
`send_daily` / `send_monthly` filtrent `enabled = 1` (job de minuit).
Un appel direct à `.send()` part donc même si le rapport est désactivé,
sans écriture en base.

`send()` respecte `send_if_data` : sans ligne et avec l'option cochée,
`get_report_content()` renvoie None et aucun mail n'est envoyé.
"""

import frappe

REPORT_VS = "Devis relances VS"
REPORT_RIVIERA = "Devis relances Riviera"


def send_vs():
	"""Jeudi 18:30 — relances devis Vitrerie Stéphanoise."""
	_send(REPORT_VS)


def send_riviera():
	"""Vendredi 18:00 — relances devis Riviera (pas d'envoi si pas de données)."""
	_send(REPORT_RIVIERA)


def _send(name):
	try:
		frappe.get_doc("Auto Email Report", name).send()
	except Exception:
		frappe.log_error(
			title=f"Échec Auto Email Report « {name} »",
			message=frappe.get_traceback(),
		)
