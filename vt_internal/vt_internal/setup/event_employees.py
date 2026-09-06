"""after_migrate : garantit le Custom Field + rejoue la migration (idempotent)."""


def after_migrate():
	from vt_internal.vt_internal.patches.add_event_employee_table import (
		ensure_custom_field,
		hide_legacy_employee_field,
		migrate_legacy_employees,
	)

	ensure_custom_field()
	hide_legacy_employee_field()
	migrate_legacy_employees()
