// Nom du document Event vs id d'instance FullCalendar (`EV::starts_on::employé`).
// Importé par le drawer ; exposé sur frappe.vt pour event_calendar.js.

export function eventDocName(value) {
	if (value == null) return "";
	if (typeof value === "object") {
		if (value.event && value.event !== value) return eventDocName(value.event);
		const xp = value.extendedProps || {};
		if (xp.name) return eventDocName(xp.name);
		if (typeof value.name === "string" && value.name && value.name.indexOf("::") === -1) {
			return value.name;
		}
		if (typeof value.id === "string" && value.id) return eventDocName(value.id);
		return "";
	}
	let text = String(value).trim();
	if (!text) return "";
	try {
		text = decodeURIComponent(text);
	} catch (_e) {
		/* déjà décodé */
	}
	if (text.indexOf("/") !== -1) {
		const parts = text.split("/").filter(Boolean);
		text = parts[parts.length - 1] || text;
		try {
			text = decodeURIComponent(text);
		} catch (_e) {
			/* déjà décodé */
		}
	}
	const cut = text.indexOf("::");
	return cut === -1 ? text : text.slice(0, cut);
}

export function eventFormHref(name, locationPath) {
	const docName = eventDocName(name);
	if (!docName) return "";
	if (typeof frappe !== "undefined" && frappe.router && typeof frappe.router.make_url === "function") {
		try {
			const url = frappe.router.make_url(["Form", "Event", docName]);
			if (url) return url;
		} catch (_e) {
			/* repli ci-dessous */
		}
	}
	const path =
		locationPath ||
		(typeof window !== "undefined" && window.location && window.location.pathname) ||
		"/app";
	const first = String(path).split("/").filter(Boolean)[0] || "app";
	const root = first === "desk" ? "desk" : "app";
	const slug =
		(typeof frappe !== "undefined" && frappe.router && frappe.router.slug && frappe.router.slug("Event")) ||
		"event";
	return `/${root}/${slug}/${encodeURIComponent(docName)}`;
}

export function isEventInstanceId(value) {
	if (value == null) return false;
	const text = typeof value === "string" ? value : String(value);
	return text.indexOf("::") !== -1 || /%3A%3A/i.test(text);
}

export function rewriteUpdateArgs(result, ev) {
	const name = eventDocName(ev);
	if (!name || !result) return result;
	if (result.args) {
		result.args.name = name;
	} else if (Object.prototype.hasOwnProperty.call(result, "name") || result.name !== undefined) {
		result.name = name;
	}
	return result;
}

export function attachVtEventNameHelpers(target) {
	const api = target || (typeof frappe !== "undefined" ? (frappe.vt = frappe.vt || {}) : {});
	api.event_doc_name = eventDocName;
	api.event_form_href = eventFormHref;
	api.is_event_instance_id = isEventInstanceId;
	api.rewrite_update_args = rewriteUpdateArgs;
	return api;
}
