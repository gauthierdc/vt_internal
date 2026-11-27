// Le calendrier Event figeait depuis le bundle FullCalendar du 26/11/2026 :
// eventsSet -> applyVisibility -> setProp("display") -> eventsSet, en boucle.
// setProp réémet eventsSet en microtâche, donc le garde synchrone ne coupait rien.
// Ce fichier charge le script réel (sans jsdom) et vérifie que le handler
// ne rappelle plus setProp, et qu'un setProp qui réémet eventsSet ne boucle pas.

import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const SRC_URL = new URL("./event_calendar.js", import.meta.url);
const src = fs.readFileSync(SRC_URL, "utf8");
const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("le source ne mute plus display et ne branche eventsSet qu'une fois", () => {
	assert.equal(code.includes('setProp("display"'), false);
	assert.equal(code.includes("setProp('display'"), false);
	assert.equal(code.includes("fc.on(\"eventsSet\""), false);
	const bindings = code.match(/cal_options\.eventsSet\s*=/g) || [];
	assert.deepEqual(bindings, ["cal_options.eventsSet ="]);
	assert.match(code, /eventClassNames/);
	assert.match(code, /classList\.toggle\(\s*"vt-cal-hidden"/);
});

test("eventsSet ne boucle plus et le filtre ne passe que par vt-cal-hidden", async () => {
	const harness = loadEventCalendar();
	const { frappe, fcOns, domEvents, setPropCalls, eventsSetCalls } = harness;

	const change = harness.handlers.find(
		(row) => row.event === "change" && row.selector === ".vt-cal-emp-filter__cb"
	);
	assert.ok(change, "le filtre Employés doit exposer son change");

	change.fn({ target: { value: "Alice", checked: false } });
	assert.equal(setPropCalls(), 0);
	assert.equal(domEvents[0].classList.hidden, true);

	const eventClassNames = frappe.views.calendar.Event.options.eventClassNames;
	assert.deepEqual(
		eventClassNames({ event: { extendedProps: { custom_employé: "Alice" } } }),
		["vt-cal-hidden"]
	);
	assert.deepEqual(
		eventClassNames({ event: { extendedProps: { custom_employé: "Bob" } } }),
		[]
	);

	assert.equal(
		fcOns.includes("eventsSet"),
		false,
		"fc.on(eventsSet) ferait un second handler"
	);
	assert.equal(typeof harness.cal.cal_options.eventsSet, "function");

	harness.cal.cal_options.eventsSet(harness.fcEvents);
	await new Promise((resolve) => setTimeout(resolve, 30));

	assert.equal(eventsSetCalls(), 1);
	assert.equal(setPropCalls(), 0);
	assert.equal(domEvents[0].classList.hidden, true);

	harness.cleanup();
});

function loadEventCalendar() {
	const intervals = [];
	const timeouts = [];
	const origSetInterval = global.setInterval;
	const origSetTimeout = global.setTimeout;
	global.setInterval = (fn, ms, ...args) => {
		const id = origSetInterval(fn, ms, ...args);
		intervals.push(id);
		return id;
	};
	global.setTimeout = (fn, ms, ...args) => {
		const id = origSetTimeout(fn, ms, ...args);
		timeouts.push(id);
		return id;
	};
	global.requestAnimationFrame = (fn) => global.setTimeout(fn, 0);

	const handlers = [];
	function jquery() {
		const api = {
			length: 0,
			on(event, selector, fn) {
				if (typeof selector === "function") {
					handlers.push({ event, selector: null, fn: selector });
				} else {
					handlers.push({ event, selector, fn });
				}
				return api;
			},
			find() {
				return jquery();
			},
			each() {
				return api;
			},
			append() {
				return api;
			},
			prepend() {
				return api;
			},
			text(value) {
				if (arguments.length) {
					api._text = value;
					return api;
				}
				return api._text || "";
			},
			html() {
				return api._text || "";
			},
			attr() {
				return api;
			},
			prop() {
				return api;
			},
			closest() {
				return null;
			},
			addClass() {
				return api;
			},
			before() {
				return api;
			},
		};
		return api;
	}

	const domEvents = [
		{
			dataset: { vtEmployee: "Alice" },
			classList: {
				hidden: false,
				toggle(name, on) {
					if (name === "vt-cal-hidden") this.hidden = Boolean(on);
				},
			},
		},
	];

	let setPropCount = 0;
	let eventsSetCount = 0;
	const fcOns = [];
	const fcEvents = [];

	class Calendar {
		setup_options() {
			this.cal_options = {};
		}
		make() {}
		prepare_events(events) {
			return events || [];
		}
		get_update_args() {
			return { args: {} };
		}
		update_event() {}
		set_calendar_height() {}
	}

	const frappe = {
		provide(path) {
			let cur = globalThis;
			for (const part of String(path).split(".")) {
				if (!cur[part] || typeof cur[part] !== "object") cur[part] = {};
				cur = cur[part];
			}
		},
		views: { calendar: {}, Calendar },
		utils: {
			escape_html: (value) => String(value ?? ""),
			debounce: (fn) => fn,
		},
		router: { on() {} },
		after_ajax(fn) {
			fn();
		},
		get_route() {
			return ["List", "Event", "Calendar", "default"];
		},
		set_route() {},
		model: { can_read: () => true },
		db: { get_list: () => Promise.resolve([]) },
		call() {},
	};

	global.localStorage = {
		getItem: () => "timeGridWeek",
		setItem() {},
		removeItem() {},
	};
	global.window = globalThis;
	global.innerWidth = 1280;
	global.frappe = frappe;
	global.$ = jquery;
	global.document = {
		body: { classList: { toggle() {} } },
	};
	global.cur_list = null;
	global.__ = (text) => text;

	vm.runInThisContext(fs.readFileSync(SRC_URL, "utf8"), { filename: "event_calendar.js" });

	const cal = {
		doctype: "Event",
	};
	const fc = {
		on(name) {
			fcOns.push(name);
		},
		getEvents() {
			return fcEvents;
		},
	};
	cal.fullCalendar = fc;
	cal.$wrapper = {
		length: 1,
		prepend() {},
		find(selector) {
			assert.equal(selector, ".fc-event");
			return {
				each(fn) {
					domEvents.forEach((el) => fn.call(el));
				},
			};
		},
	};

	Calendar.prototype.setup_options.call(cal, {});
	const realEventsSet = cal.cal_options.eventsSet;
	assert.equal(typeof realEventsSet, "function");
	cal.cal_options.eventsSet = (events) => {
		eventsSetCount += 1;
		// Plafond : l'ancien setProp réémettait eventsSet sans jamais s'arrêter.
		if (eventsSetCount > 8) return;
		return realEventsSet.call(cal, events);
	};

	fcEvents.push({
		id: "EV-1::2026-11-27 09:00:00::Alice",
		extendedProps: { custom_employé: "Alice", name: "EV-1" },
		setProp() {
			setPropCount += 1;
			const fire = cal.cal_options.eventsSet;
			queueMicrotask(() => fire(fcEvents));
		},
	});

	Calendar.prototype.make.call(cal);

	return {
		frappe,
		cal,
		fcOns,
		fcEvents,
		domEvents,
		handlers,
		setPropCalls: () => setPropCount,
		eventsSetCalls: () => eventsSetCount,
		cleanup() {
			for (const id of intervals) clearInterval(id);
			for (const id of timeouts) clearTimeout(id);
			global.setInterval = origSetInterval;
			global.setTimeout = origSetTimeout;
		},
	};
}
