# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.password import get_decrypted_password


def run_on_po_acknowledgment(docname):
	"""
	Background job : traite un PO Acknowledgment dans un sandbox E2B via OpenCode.
	Appelé depuis POAcknowledgment.after_insert via frappe.enqueue.
	"""
	from e2b_code_interpreter import Sandbox

	# Clés API depuis le singleton VT Bot
	anthropic_key = get_decrypted_password("VT Bot", "VT Bot", "anthropic_api_key")
	e2b_key = get_decrypted_password("VT Bot", "VT Bot", "e2b_api_key")
	erp_api_key = get_decrypted_password("VT Bot", "VT Bot", "erp_api_key")
	erp_secret_api = get_decrypted_password("VT Bot", "VT Bot", "erp_secret_api")

	if not anthropic_key or not e2b_key:
		frappe.log_error("VT Bot : clés API manquantes dans VT Bot settings", "VT Bot")
		return

	# Skills depuis Prompt IA (skill_for_vt_bot = 1)
	skills = frappe.get_all(
		"Prompt IA",
		filters={"skill_for_vt_bot": 1},
		fields=["title", "prompt"],
	)

	doc = frappe.get_doc("PO Acknowledgment", docname)
	site_url = frappe.utils.get_url()

	# Chercher la Communication liée (créée après le doc par Frappe)
	communication_name = frappe.db.get_value(
		"Communication",
		{"reference_doctype": "PO Acknowledgment", "reference_name": docname},
		"name",
	)

	sandbox = Sandbox(api_key=e2b_key)
	try:
		# Upload des skills dans ~/.claude/skills/<nom>/SKILL.md
		for skill in skills:
			skill_name = skill.title.lower().replace(" ", "-")
			sandbox.commands.run(f"mkdir -p /home/user/.claude/skills/{skill_name}")
			sandbox.files.write(
				f"/home/user/.claude/skills/{skill_name}/SKILL.md",
				skill.prompt.encode(),
			)

		# Config OpenCode
		config = (
			'{"$schema":"https://opencode.ai/config.json",'
			'"model":"anthropic/claude-sonnet-4-5"}'
		)
		sandbox.files.write("/home/user/opencode.json", config.encode())

		# Installation OpenCode
		sandbox.commands.run("sudo npm install -g opencode-ai", timeout=120)

		# Construction du prompt
		communication_url = (
			f"{site_url}/app/communication/{communication_name}"
			if communication_name
			else "non disponible"
		)
		prompt = (
			f"Traite cet accusé de réception de commande fournisseur : "
			f"{site_url}/app/po-acknowledgment/{docname} . "
			f"La communication source (email avec pièces jointes) est : {communication_url} . "
			f"Fournisseur : {doc.supplier or 'inconnu'} . "
			f"Sujet : {doc.subject or ''} . "
			f"Récupère le PDF joint via l'API ERP, retrouve la commande fournisseur, "
			f"vérifie les articles, dimensions, prix et date de livraison, "
			f"mets à jour la commande si nécessaire et poste un commentaire de synthèse."
		)

		result = sandbox.commands.run(
			f'cd /home/user && ANTHROPIC_API_KEY={anthropic_key}'
			f' ERP_API_KEY={erp_api_key} ERP_SECRET_API={erp_secret_api}'
			f' opencode run "{prompt}"',
			timeout=300,
		)

		if result.stderr:
			frappe.log_error(result.stderr[:2000], f"VT Bot stderr – {docname}")

	except Exception:
		frappe.log_error(frappe.get_traceback(), f"VT Bot – {docname}")
	finally:
		sandbox.kill()
