app_name = "vt_internal"
app_title = "VT internal"
app_publisher = "Verre & Transparence"
app_description = "Scripts personnalisés de V&T"
app_email = "gauthier@de-chezelles.com"
app_license = "mit"
# required_apps = []

fixtures = [
	{"dt": "Desktop Icon", "filters": [["name", "in", ["V&T", "Insights"]]]}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# Noms de bundles nus (sans "/assets") : c'est la seule forme que
# bundled_asset() résout via assets.json, ce qui donne un nom de fichier
# haché à chaque build et invalide le cache navigateur (les assets sont
# servis en "max-age=1an, immutable").
app_include_css = "vt_calendar.bundle.css"
app_include_js = [
	"bundle_editor_patch.bundle.js",
	"customer_quick_entry.bundle.js",
	"vt_sidebar_default.bundle.js",
	"vt_event_popup.bundle.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/vt_internal/css/vt_internal.css"
# web_include_js = "/assets/vt_internal/js/vt_internal.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "vt_internal/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# DocTypes STANDARD (custom=0) : leur JS de formulaire/liste est ici (hooks) ou,
# pour les doctypes promus (Fiche de travail, etc.), dans doctype/<nom>/<nom>.js
# chargé nativement par Frappe une fois custom=0 (cf. patch promote_custom_doctypes).
doctype_js = {
	"Quotation": "public/js/quotation.js",
	"Bank Transaction": "public/js/bank_transaction.js",
	"Customer": "public/js/customer.js",
	"Delivery Note": "public/js/delivery_note.js",
	"Event": "public/js/event.js",
	"Expense": "public/js/expense.js",
	"OCR Request": "public/js/ocr_request.js",
	"Payment Entry": "public/js/payment_entry.js",
	"Payment Order": "public/js/payment_order.js",
	"Project": "public/js/project.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Purchase Order": "public/js/purchase_order.js",
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Sales Invoice": "public/js/sales_invoice.js",
	"Sales Order": "public/js/sales_order.js",
	"Supplier Invoice": "public/js/supplier_invoice.js",
	"Supplier Quotation": "public/js/supplier_quotation.js",
	"Timesheet": "public/js/timesheet.js",
	"VT Formulaire Verre Production": "public/js/vt_formulaire_verre_production.js",
	"VT Prix De Forme": "public/js/vt_prix_de_forme.js",
}
doctype_list_js = {
	"Quotation": "public/js/quotation_list.js",
	"Customer": "public/js/customer_list.js",
	"Delivery Note": "public/js/delivery_note_list.js",
	"Issue": "public/js/issue_list.js",
	"OCR Request": "public/js/ocr_request_list.js",
	"Purchase Order": "public/js/purchase_order_list.js",
	"Purchase Receipt": "public/js/purchase_receipt_list.js",
	"Sales Invoice": "public/js/sales_invoice_list.js",
	"Sales Order": "public/js/sales_order_list.js",
	"Timesheet": "public/js/timesheet_list.js",
	"VT Prix De Forme": "public/js/vt_prix_de_forme_list.js",
}
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
doctype_calendar_js = {"Event": "public/js/event_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "vt_internal/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "vt_internal.utils.jinja_methods",
# 	"filters": "vt_internal.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "vt_internal.install.before_install"
# after_install = "vt_internal.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "vt_internal.uninstall.before_uninstall"
# after_uninstall = "vt_internal.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "vt_internal.utils.before_app_install"
# after_app_install = "vt_internal.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "vt_internal.utils.before_app_uninstall"
# after_app_uninstall = "vt_internal.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "vt_internal.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"Quotation": {
		"before_save": "vt_internal.vt_internal.events.quotation.before_save",
		"before_insert": "vt_internal.vt_internal.events.quotation.before_insert",
		"before_print": "vt_internal.vt_internal.events.quotation.before_print",
		"before_update_after_submit": "vt_internal.vt_internal.events.quotation.before_update_after_submit",
	},
	"Bank Transaction": {
		"after_insert": "vt_internal.vt_internal.events.bank_transaction.after_insert",
	},
	"Carte de travail VT": {
		"validate": "vt_internal.vt_internal.events.carte_de_travail_vt.validate",
	},
	"Customer": {
		"before_insert": "vt_internal.vt_internal.events.customer.before_insert",
		"validate": "vt_internal.vt_internal.events.customer.validate",
	},
	"Delivery Note": {
		"before_insert": "vt_internal.vt_internal.events.delivery_note.before_insert",
		"on_submit": "vt_internal.vt_internal.events.delivery_note.on_submit",
	},
	"Employee": {
		"validate": "vt_internal.vt_internal.events.employee.validate",
	},
	"Event": {
		"validate": "vt_internal.vt_internal.events.event.validate",
		"on_update": "vt_internal.vt_internal.events.event.on_update",
		"after_delete": "vt_internal.vt_internal.events.event.after_delete",
	},
	"Expense": {
		"validate": "vt_internal.vt_internal.events.expense.validate",
		"before_submit": "vt_internal.vt_internal.events.expense.before_submit",
		"on_submit": "vt_internal.vt_internal.events.expense.on_submit",
	},
	"Fabrication VT": {
		"on_update": "vt_internal.vt_internal.events.fabrication_vt.on_update",
		"on_trash": "vt_internal.vt_internal.events.fabrication_vt.on_trash",
	},
	"Fiche de travail": {
		"before_insert": "vt_internal.vt_internal.events.fiche_de_travail.before_insert",
		"validate": "vt_internal.vt_internal.events.fiche_de_travail.validate",
		"before_update_after_submit": "vt_internal.vt_internal.events.fiche_de_travail.before_update_after_submit",
		"on_cancel": "vt_internal.vt_internal.events.fiche_de_travail.on_cancel",
		"on_trash": "vt_internal.vt_internal.events.fiche_de_travail.on_trash",
		"before_print": "vt_internal.vt_internal.events.fiche_de_travail.before_print",
	},
	"Glass manufacturing costs": {
		"validate": "vt_internal.vt_internal.events.glass_manufacturing_costs.validate",
		"on_submit": "vt_internal.vt_internal.events.glass_manufacturing_costs.on_submit",
	},
	"Payment Order": {
		"validate": "vt_internal.vt_internal.events.payment_order.validate",
	},
	"Payment Request": {
		"on_submit": "vt_internal.vt_internal.events.payment_request.on_submit",
		"on_update_after_submit": "vt_internal.vt_internal.events.payment_request.on_update_after_submit",
		"on_cancel": "vt_internal.vt_internal.events.payment_request.on_cancel",
	},
	"Pending Purchase Invoice": {
		"before_insert": "vt_internal.vt_internal.events.pending_purchase_invoice.before_insert",
	},
	"Product Bundle": {
		"validate": "vt_internal.vt_internal.events.product_bundle.validate",
	},
	"Production statement": {
		"on_update": "vt_internal.vt_internal.events.production_statement.on_update",
	},
	"Project": {
		"validate": "vt_internal.vt_internal.events.project.validate",
	},
	"Purchase Invoice": {
		"validate": "vt_internal.vt_internal.events.purchase_invoice.validate",
		"after_insert": "vt_internal.vt_internal.events.purchase_invoice.after_insert",
	},
	"Purchase Order": {
		"before_validate": "vt_internal.vt_internal.events.purchase_order.before_validate",
		"validate": "vt_internal.vt_internal.events.purchase_order.validate",
		"after_insert": "vt_internal.vt_internal.events.purchase_order.after_insert",
		"on_submit": "vt_internal.vt_internal.events.purchase_order.on_submit",
		"before_update_after_submit": "vt_internal.vt_internal.events.purchase_order.before_update_after_submit",
	},
	"Purchase Receipt": {
		"on_submit": "vt_internal.vt_internal.events.purchase_receipt.on_submit",
	},
	"Quality Incident": {
		"validate": "vt_internal.vt_internal.events.quality_incident.validate",
	},
	"Quotation Approval": {
		"after_insert": "vt_internal.vt_internal.events.quotation_approval.after_insert",
	},
	"Quotation Payement Request": {
		"on_payment_authorized": "vt_internal.vt_internal.events.quotation_payement_request.on_payment_authorized",
	},
	"Sales Invoice": {
		"before_validate": "vt_internal.vt_internal.events.sales_invoice.before_validate",
		"before_insert": "vt_internal.vt_internal.events.sales_invoice.before_insert",
		"validate": "vt_internal.vt_internal.events.sales_invoice.validate",
		"on_submit": "vt_internal.vt_internal.events.sales_invoice.on_submit",
		"before_update_after_submit": "vt_internal.vt_internal.events.sales_invoice.before_update_after_submit",
		"before_print": "vt_internal.vt_internal.events.sales_invoice.before_print",
	},
	"Sales Order": {
		"before_validate": "vt_internal.vt_internal.events.sales_order.before_validate",
		"before_insert": "vt_internal.vt_internal.events.sales_order.before_insert",
		"validate": "vt_internal.vt_internal.events.sales_order.validate",
		"before_submit": "vt_internal.vt_internal.events.sales_order.before_submit",
		"on_submit": "vt_internal.vt_internal.events.sales_order.on_submit",
		"before_update_after_submit": "vt_internal.vt_internal.events.sales_order.before_update_after_submit",
		"on_cancel": "vt_internal.vt_internal.events.sales_order.on_cancel",
		"on_trash": "vt_internal.vt_internal.events.sales_order.on_trash",
		"before_print": "vt_internal.vt_internal.events.sales_order.before_print",
	},
	"Sales Order Item": {
		"on_update": "vt_internal.vt_internal.events.sales_order_item.on_update",
		"on_update_after_submit": "vt_internal.vt_internal.events.sales_order_item.on_update_after_submit",
	},
	"Timesheet": {
		"before_insert": "vt_internal.vt_internal.events.timesheet.before_insert",
		"validate": "vt_internal.vt_internal.events.timesheet.validate",
		"before_submit": "vt_internal.vt_internal.events.timesheet.before_submit",
		"on_submit": "vt_internal.vt_internal.events.timesheet.on_submit",
		"on_cancel": "vt_internal.vt_internal.events.timesheet.on_cancel",
	},
	"Work Completion Receipt": {
		"before_insert": "vt_internal.vt_internal.events.work_completion_receipt.before_insert",
		"on_submit": "vt_internal.vt_internal.events.work_completion_receipt.on_submit",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"vt_internal.tasks.all"
# 	],
# 	"daily": [
# 		"vt_internal.tasks.daily"
# 	],
# 	"hourly": [
# 		"vt_internal.tasks.hourly"
# 	],
# 	"weekly": [
# 		"vt_internal.tasks.weekly"
# 	],
# 	"monthly": [
# 		"vt_internal.tasks.monthly"
# 	],
# }

scheduler_events = {
	"hourly": [
		# Convertis depuis les Server Scripts « Scheduler Event » (un fichier par tâche
		# dans vt_internal/tasks/).
		"vt_internal.vt_internal.tasks.close_billed_projects.close_billed_projects",
	],
	"daily": [
		"vt_internal.vt_internal.tasks.update_recurring_customer_status.update_recurring_customer_status",
	],
	"weekly": [
		"vt_internal.vt_internal.tasks.weekly_expense_reminder.weekly_expense_reminder",
		"vt_internal.vt_internal.tasks.weekly_crm_notes_mail.weekly_crm_notes_mail",
	],
	"cron": {
			# Chaque vendredi à 19h
			"0 19 * * 5": [
					"vt_internal.vt_internal.weekly_hours_report.send_by_mail_weekly_hours_report"
			],
	},
}

# Testing
# -------

# before_tests = "vt_internal.install.before_tests"

# Overriding Methods
# ------------------------------

# WORKAROUND TEMPORAIRE - À SUPPRIMER quand corrigé upstream
# Issue: https://github.com/frappe/erpnext/issues/49677
# Problème: Les User Permissions ne sont pas appliquées en mode calendrier
override_whitelisted_methods = {
	"frappe.desk.doctype.event.event.get_events": "vt_internal.vt_internal.overrides.event.get_events",
	# --- Préservation des URLs courtes des anciens Server Scripts API ---
	# Les clés reproduisent l'ancien api_method (/api/method/<clé>) pour ne casser
	# les appels front (URL courte).
	# La clé peut contenir un tiret : le handler résout par simple lookup de dict.
	"change_company": "vt_internal.vt_internal.api.admin.change_company",
	"change_cost_center": "vt_internal.vt_internal.api.admin.change_cost_center",
	"create_production": "vt_internal.vt_internal.api.fabrication.create_production",
	"ft_timer_html": "vt_internal.vt_internal.api.timesheet.ft_timer_html",
	"generate_consolidate_sales_invoice": "vt_internal.vt_internal.api.sales.generate_consolidate_sales_invoice",
	"new_fabrication": "vt_internal.vt_internal.api.fabrication.new_fabrication",
	"new_visite_technique_from_quotation": "vt_internal.vt_internal.api.sales.new_visite_technique_from_quotation",
	"payment_link_from_sales_order": "vt_internal.vt_internal.api.sales.payment_link_from_sales_order",
	"reconciliation_paiement_order_to_transaction": "vt_internal.vt_internal.api.sales.reconciliation_paiement_order_to_transaction",
	"sales_order_to_chantier_a_faire": "vt_internal.vt_internal.api.sales.sales_order_to_chantier_a_faire",
	"sms_delivery_note": "vt_internal.vt_internal.api.delivery_note.sms_delivery_note",
	"timesheet_html_block": "vt_internal.vt_internal.api.timesheet.timesheet_html_block",
	"timesheet_post_api": "vt_internal.vt_internal.api.timesheet.timesheet_post_api",
	"update_bmv_prices": "vt_internal.vt_internal.api.admin.update_bmv_prices",
	"update_fiche_de_travail_status": "vt_internal.vt_internal.api.timesheet.update_fiche_de_travail_status",
	"update_manufacturing_status": "vt_internal.vt_internal.api.fabrication.update_manufacturing_status",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "vt_internal.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["vt_internal.utils.before_request"]
# after_request = ["vt_internal.utils.after_request"]
# Job Events
# ----------
# before_job = ["vt_internal.utils.before_job"]
# after_job = ["vt_internal.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"vt_internal.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

