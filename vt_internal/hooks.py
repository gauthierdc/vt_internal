app_name = "vt_internal"
app_title = "VT internal"
app_publisher = "Verre & Transparence"
app_description = "Scripts personnalisés de V&T"
app_email = "gauthier@de-chezelles.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/vt_internal/css/vt_internal.css"
app_include_js = "/assets/vt_internal/js/bundle_editor_patch.js"

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
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

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
	"cron": {
			# Chaque vendredi à 19h
			"0 19 * * 5": [
					"vt_internal.vt_internal.weekly_hours_report.run_weekly_hours_report"
			]
	}
}

# Testing
# -------

# before_tests = "vt_internal.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "vt_internal.event.get_events"
# }
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

