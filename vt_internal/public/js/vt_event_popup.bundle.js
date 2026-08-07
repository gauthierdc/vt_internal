// Remplace le popover d'événement natif de Dokos ("popup pourri") par un
// drawer latéral qui slide (le même que la page calendrier custom).
//
// Principe : on intercepte le clic sur un .fc-event en phase CAPTURE et on
// stoppe la propagation avant que le listener natif (qui ouvre le popover)
// ne s'exécute, puis on ouvre notre drawer Vue.

import { createApp, reactive } from "vue";
import EventDrawer from "./planning/EventDrawer.vue";

// Store réactif partagé : on incrémente `nonce` à chaque ouverture pour
// re-déclencher le watch même si on reclique le même événement.
const store = reactive({ eventId: null, title: "", nonce: 0 });

function openDrawer(name, title) {
	store.eventId = name;
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
	return { slug: parts[parts.length - 2], name };
}

function onCalendarClick(e) {
	// Laisse passer : clic non-gauche, modificateurs (ouvrir dans un onglet), bouton "éditer"
	if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
	const eventEl = e.target.closest(".fc-event");
	if (!eventEl) return;
	if (e.target.closest("[data-action=edit]")) return;

	const parsed = parseEventHref(eventEl);
	// On ne prend en charge que le calendrier des Événements.
	if (!parsed || parsed.slug !== "event") return;

	// Empêche le popover natif de s'ouvrir.
	e.preventDefault();
	e.stopImmediatePropagation();

	const title = (eventEl.innerText || "").trim().split("\n").pop() || "";
	openDrawer(parsed.name, title);
}

frappe.after_ajax(() => {
	mountDrawer();

	// Capture-phase pour passer avant le listener natif du popover.
	document.addEventListener("click", onCalendarClick, true);

	// Désactive la tooltip "hover" native du calendrier (redondante avec le drawer,
	// et clignotante au toucher sur mobile). jQuery implémente `mouseenter` via un
	// `mouseover` natif, donc on capture les deux sur un .fc-event et on stoppe la
	// propagation avant que le déclencheur Bootstrap ne s'exécute.
	const killTooltip = (e) => {
		if (e.target.closest && e.target.closest(".fc-event")) e.stopImmediatePropagation();
	};
	document.addEventListener("mouseenter", killTooltip, true);
	document.addEventListener("mouseover", killTooltip, true);
});

// Expose pour usage éventuel ailleurs.
frappe.provide("frappe.vt");
frappe.vt.open_event_drawer = openDrawer;
