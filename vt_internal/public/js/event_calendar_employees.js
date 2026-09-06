// Helpers purs du filtre Employés (calendrier Event).
// Importés par les tests Node et attachés sur frappe.vt.calendar_employees.

const NONE = "__none__";
const EMP_KEYS = ["custom_employé", "custom_employe", "custom_employee"];

export function serializeCalendarDate(value) {
	if (value == null || value === "") return "";
	if (typeof value === "object" && typeof value.format === "function") {
		try {
			const formatted = value.format("YYYY-MM-DD");
			if (/^\d{4}-\d{2}-\d{2}$/.test(formatted)) return formatted;
		} catch (_e) {
			/* moment-like invalide */
		}
	}
	if (typeof value === "string") {
		const trimmed = value.trim().replace(/^["']|["']$/g, "");
		const iso = trimmed.match(/^(\d{4}-\d{2}-\d{2})/);
		if (iso) return iso[1];
	}
	if (value instanceof Date && !Number.isNaN(value.getTime())) {
		const y = value.getFullYear();
		const m = String(value.getMonth() + 1).padStart(2, "0");
		const d = String(value.getDate()).padStart(2, "0");
		return `${y}-${m}-${d}`;
	}
	return "";
}

export function sanitizeCalendarFilters(raw) {
	if (raw == null || raw === "" || raw === false) return [];
	let value = raw;
	if (typeof value === "string") {
		try {
			value = JSON.parse(value);
		} catch (_e) {
			return [];
		}
	}
	if (!Array.isArray(value)) return [];
	return value.filter((row) => {
		if (Array.isArray(row)) return row.length >= 3 && row[1] != null && row[2] != null;
		if (row && typeof row === "object") return Boolean(row.fieldname && row.operator);
		return false;
	});
}

function readEmployeeField(obj) {
	if (!obj || typeof obj !== "object") return "";
	for (const key of EMP_KEYS) {
		const val = obj[key];
		if (val != null && String(val).trim()) return String(val).trim();
	}
	return "";
}

export function employeeFromInstanceId(id) {
	if (id == null) return "";
	let text = String(id);
	try {
		text = decodeURIComponent(text);
	} catch (_e) {
		/* déjà décodé */
	}
	if (text.indexOf("::") === -1) return "";
	const parts = text.split("::");
	if (parts.length < 3) return "";
	const emp = parts.slice(2).join("::").trim();
	if (!emp || emp === "_") return "";
	return emp;
}

export function eventEmployee(ev) {
	if (!ev) return "";
	if (ev.event && ev.event !== ev) return eventEmployee(ev.event);
	const bags = [
		ev,
		ev.extendedProps,
		ev.extendedProps && ev.extendedProps.extendedProps,
		ev._def && ev._def.extendedProps,
	];
	if (typeof ev.toPlainObject === "function") {
		try {
			bags.push(ev.toPlainObject());
		} catch (_e) {
			/* EventApi incomplet */
		}
	}
	for (const bag of bags) {
		const found = readEmployeeField(bag);
		if (found) return found;
	}
	const instanceId =
		ev.calendar_instance_id ||
		(ev.extendedProps && ev.extendedProps.calendar_instance_id) ||
		(ev._def && ev._def.extendedProps && ev._def.extendedProps.calendar_instance_id) ||
		ev.id;
	return employeeFromInstanceId(instanceId);
}

export function collectCalendarEvents(cal, hint) {
	if (Array.isArray(hint)) return hint;
	const fc = cal && cal.fullCalendar;
	if (!fc) return [];
	const apis = [fc, fc.calendar];
	for (const api of apis) {
		if (!api || typeof api.getEvents !== "function") continue;
		try {
			const list = api.getEvents();
			if (Array.isArray(list) && list.length) return list;
		} catch (_e) {
			/* wrapper FC incomplet */
		}
	}
	return Array.isArray(hint) ? hint : [];
}

export function employeesFromEvents(cal, hint, unassignedLabel = "Sans employé") {
	const events = collectCalendarEvents(cal, hint);
	if (!events.length) return [];
	const counts = new Map();
	const colors = new Map();
	events.forEach((ev) => {
		const name = eventEmployee(ev);
		const key = name || NONE;
		counts.set(key, (counts.get(key) || 0) + 1);
		if (!colors.has(key)) {
			const xp = (ev && ev.extendedProps) || {};
			const color = ev.backgroundColor || xp.color || ev.color;
			if (color) colors.set(key, color);
		}
	});
	return Array.from(counts.entries()).map(([key, event_count]) => ({
		name: key === NONE ? "" : key,
		employee_name: key === NONE ? unassignedLabel : key,
		color: colors.get(key) || "#94a3b8",
		event_count,
	}));
}

export function mergeEmployeeRows(fromEvents, fromApi) {
	const events = Array.isArray(fromEvents) ? fromEvents : [];
	const api = Array.isArray(fromApi) ? fromApi : [];
	if (!events.length) return api;
	const apiByKey = {};
	api.forEach((row) => {
		if (!row) return;
		apiByKey[row.name || NONE] = row;
	});
	return events.map((row) => {
		const extra = apiByKey[row.name || NONE];
		if (!extra) return row;
		return {
			...row,
			employee_name: extra.employee_name || row.employee_name,
			color: extra.color || row.color,
			event_count: row.event_count != null ? row.event_count : extra.event_count,
		};
	});
}

export function asEmployeeRows(message) {
	if (Array.isArray(message)) return message;
	if (typeof message === "string") {
		try {
			const parsed = JSON.parse(message);
			return Array.isArray(parsed) ? parsed : [];
		} catch (_e) {
			return [];
		}
	}
	return [];
}

export function stampPreparedEvent(d, { eventDocName, eventFormHref } = {}) {
	if (!d || typeof d !== "object") return d;
	const rawName = d.name || d.id || "";
	const name = eventDocName ? eventDocName(rawName) : String(rawName).split("::")[0];
	if (name) d.name = name;
	if (d.calendar_instance_id) d.id = d.calendar_instance_id;
	if (name && eventFormHref) d.url = eventFormHref(name);
	const emp = eventEmployee(d);
	d.custom_employé = emp;
	d.extendedProps = Object.assign({}, d.extendedProps, {
		custom_employé: emp,
		calendar_instance_id: d.calendar_instance_id || d.id,
		name: name || d.name,
	});
	return d;
}

export function attachCalendarEmployeeHelpers(target) {
	const root =
		target || (typeof frappe !== "undefined" ? (frappe.vt = frappe.vt || {}) : {});
	const dest = (root.calendar_employees = root.calendar_employees || {});
	dest.serializeCalendarDate = serializeCalendarDate;
	dest.sanitizeCalendarFilters = sanitizeCalendarFilters;
	dest.eventEmployee = eventEmployee;
	dest.employeeFromInstanceId = employeeFromInstanceId;
	dest.employeesFromEvents = employeesFromEvents;
	dest.mergeEmployeeRows = mergeEmployeeRows;
	dest.asEmployeeRows = asEmployeeRows;
	dest.stampPreparedEvent = stampPreparedEvent;
	dest.collectCalendarEvents = collectCalendarEvents;
	return dest;
}
