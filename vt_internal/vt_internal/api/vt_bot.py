# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.password import get_decrypted_password


def run_on_po_acknowledgment(docname):
	"""
	Background job : traite un PO Acknowledgment dans un sandbox E2B via Claude Code.
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

	import os
	import logging
	logging.getLogger("e2b").setLevel(logging.WARNING)

	os.environ["E2B_API_KEY"] = e2b_key
	sandbox = Sandbox.create(timeout=1000)
	try:
		# Upload des skills dans ~/.claude/skills/<nom>/SKILL.md
		for skill in skills:
			skill_name = skill.title.lower().replace(" ", "-")
			sandbox.commands.run(f"mkdir -p /home/user/.claude/skills/{skill_name}")
			sandbox.files.write(
				f"/home/user/.claude/skills/{skill_name}/SKILL.md",
				skill.prompt.encode(),
			)

		# Installation Claude Code
		sandbox.commands.run("sudo npm install -g @anthropic-ai/claude-code", timeout=180)

		# Construction du prompt
		prompt = (
			f"Traite cet accusé de réception de commande fournisseur : {docname} . "
			f"Fournisseur : {doc.supplier or 'inconnu'} . "
			f"Sujet : {doc.subject or ''} . "
			f"Utilise le skill /erp-ar-validation."
		)

		result = sandbox.commands.run(
			f'cd /home/user && ANTHROPIC_API_KEY={anthropic_key}'
			f' ERP_API_KEY={erp_api_key} ERP_SECRET_API={erp_secret_api}'
			f' claude --dangerously-skip-permissions -p "{prompt}" > /tmp/claude.log 2>&1',
			timeout=900,
		)

		if result.stderr:
			frappe.log_error(result.stderr[:2000], f"VT Bot stderr – {docname}")

	except Exception:
		frappe.log_error(frappe.get_traceback(), f"VT Bot – {docname}")
	finally:
		sandbox.kill()
