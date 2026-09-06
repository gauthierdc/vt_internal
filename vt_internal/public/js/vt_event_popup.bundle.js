// Remplace le popover d'événement natif de Dokos ("popup pourri") par un
// drawer latéral qui slide (le même que la page calendrier custom).
//
// Principe : on intercepte le clic sur un .fc-event en phase CAPTURE et on
// stoppe la propagation avant que le listener natif (qui ouvre le popover)
// ne s'exécute, puis on ouvre notre drawer Vue.

import { createApp, reactive } from "vue";
import EventDrawer from "./planning/EventDrawer.vue";
import { attachVtEventNameHelpers, eventDocName, eventFormHref } from "./event_doc_name.js";

frappe.provide("frappe.vt");
attachVtEventNameHelpers(frappe.vt);

// Store réactif partagé : on incrémente `nonce` à chaque ouverture pour
// re-déclencher le watch même si on reclique le même événement.
const store = reactive({ eventId: null, title: "", nonce: 0 });

function openDrawer(name, title) {
	store.eventId = eventDocName(name);
	store.title = title || "";
	store.nonce += 1;
}

function mountDrawer() {
	if (document.getElementById("vt-event-drawer-root")) return;
	const root = document.createElement("div");
	root.id = "vt-event-drawer-root";
	document.body.appendChild(root);
	const app = createApp(EventDrawer, { store });
	if (typeof window.SetVueGlobals === "function") window.SetVueGlobals(app);
	app.mount(root);
}

function eventNameFromEl(el) {
	if (!el) return "";
	if (el.dataset && el.dataset.vtEventName) return eventDocName(el.dataset.vtEventName);
	const parsed = parseEventHref(el);
	return eventDocName(parsed && parsed.name);
}

// Extrait { doctype_slug, name } depuis le href d'un événement de calendrier.
function parseEventHref(el) {
	const anchor = el.matches("[href]") ? el : el.querySelector("a[href]");
	const href = anchor && anchor.getAttribute("href");
	if (!href) return null;
	let path;
	try {
		path = new URL(href, window.location.origin).pathname;
	} catch (_) {
		return null;
	}
	const parts = path.split("/").filter(Boolean); // ex: ["app", "event", "EV00041"]
	if (parts.length < 2) return null;
	let name;
	try {
		name = decodeURIComponent(parts[parts.length - 1]);
	} catch (_) {
		name = parts[parts.length - 1];
	}
	return { slug: parts[parts.length - 2], name: eventDocName(name) };
}

function rewriteInstanceHrefs(eventEl) {
	const name = eventNameFromEl(eventEl);
	if (!name) return;
	const href = eventFormHref(name);
	const nodes = [];
	if (eventEl.matches && eventEl.matches("a[href]")) nodes.push(eventEl);
	if (eventEl.querySelectorAll) {
		eventEl.querySelectorAll("a[href]").forEach((a) => nodes.push(a));
	}
	nodes.forEach((a) => {
		const cur = a.getAttribute("href") || "";
		if (!cur || cur.indexOf("::") !== -1 || /%3A%3A/i.test(cur) || /\/event\//i.test(cur)) {
			a.setAttribute("href", href);
		}
	});
	if (eventEl.dataset) eventEl.dataset.vtEventName = name;
}

function isEventCalendarTarget(eventEl) {
	if ((eventEl.dataset && eventEl.dataset.vtEventName) || eventEl.closest(".vt-cal-emp-filter")) {
		return true;
	}
	const parsed = parseEventHref(eventEl);
	return Boolean(parsed && parsed.slug === "event");
}

function onCalendarClick(e) {
	const eventEl = e.target.closest && e.target.closest(".fc-event");
	if (!eventEl) return;
	if (!isEventCalendarTarget(eventEl)) return;

	rewriteInstanceHrefs(eventEl);
	const name = eventNameFromEl(eventEl);
	if (!name) return;

	const isEdit = e.target.closest("[data-action=edit]");
	if (isEdit) {
		if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
		e.preventDefault();
		e.stopImmediatePropagation();
		frappe.set_route("Form", "Event", name);
		return;
	}

	// Laisse passer : clic non-gauche, modificateurs (ouvrir dans un onglet)
	if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

	// Empêche le popover natif de s'ouvrir.
	e.preventDefault();
	e.stopImmediatePropagation();

	// Mobile : le tap a pu focus l'événement et déclencher la tooltip Bootstrap
	// (trigger "hover focus") avant ce clic. On la masque et on retire le focus.
	try {
		$(eventEl).tooltip("hide");
		eventEl.blur();
	} catch (_) {
		/* pas de jQuery/tooltip : rien à faire */
	}

	const title = (eventEl.innerText || "").trim().split("\n").pop() || "";
	openDrawer(name, title);
}

function patchSetRoute() {
	if (!frappe.set_route || frappe.set_route.__vt_event_name_patched) return;
	const orig = frappe.set_route;
	frappe.set_route = function (...args) {
		let route = args;
		if (args.length === 1 && Array.isArray(args[0])) {
			route = args[0];
		}
		if (route[0] === "Form" && route[1] === "Event" && route[2]) {
			const clean = eventDocName(route[2]);
			if (clean && clean !== route[2]) {
				if (args.length === 1 && Array.isArray(args[0])) {
					args[0] = [route[0], route[1], clean].concat(route.slice(3));
				} else {
					args[2] = clean;
				}
			}
		}
		return orig.apply(this, args);
	};
	frappe.set_route.__vt_event_name_patched = true;
}

frappe.after_ajax(() => {
	mountDrawer();
	patchSetRoute();

	// Capture-phase pour passer avant le listener natif du popover / crayon.
	document.addEventListener("click", onCalendarClick, true);

	// Désactive la tooltip native du calendrier (redondante avec le drawer, et
	// clignotante au toucher sur mobile). Le trigger Bootstrap est "hover focus" :
	// - desktop → `mouseenter`/`mouseover` (jQuery implémente mouseenter via mouseover)
	// - mobile  → `focusin` (le tap focus l'événement, sans hover)
	// On capture ces événements sur un .fc-event et on stoppe la propagation avant
	// que le déclencheur Bootstrap ne s'exécute.
	const killTooltip = (e) => {
		if (e.target.closest && e.target.closest(".fc-event")) e.stopImmediatePropagation();
	};
	document.addEventListener("mouseenter", killTooltip, true);
	document.addEventListener("mouseover", killTooltip, true);
	document.addEventListener("focusin", killTooltip, true);
});

// Expose pour usage éventuel ailleurs.
frappe.vt.open_event_drawer = openDrawer;
