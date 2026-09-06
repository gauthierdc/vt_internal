import assert from "node:assert/strict";
import test from "node:test";
import {
	asEmployeeRows,
	applyEventCalendarPageClass,
	calendarLayoutOptions,
	CALENDAR_MOBILE_MAX_PX,
	collectCalendarEvents,
	DESKTOP_CALENDAR_HEIGHT,
	employeeFromInstanceId,
	employeesFromEvents,
	EVENT_CALENDAR_PAGE_CLASS,
	eventEmployee,
	hideEventCalendarListSidebar,
	isEventCalendarRoute,
	isMobileCalendarViewport,
	mergeEmployeeRows,
	sanitizeCalendarFilters,
	serializeCalendarDate,
	stampPreparedEvent,
} from "./event_calendar_employees.js";

test("serializeCalendarDate accepts Date, moment-like, ISO and SQL strings", () => {
	assert.equal(serializeCalendarDate("2026-09-08"), "2026-09-08");
	assert.equal(serializeCalendarDate("2026-09-08 00:00:00"), "2026-09-08");
	assert.equal(serializeCalendarDate("2026-09-08T22:00:00.000Z"), "2026-09-08");
	assert.equal(serializeCalendarDate('"2026-09-14T00:00:00.000Z"'), "2026-09-14");
	assert.equal(serializeCalendarDate({ format: () => "2026-09-08" }), "2026-09-08");
	assert.equal(serializeCalendarDate(new Date(2026, 8, 8, 0, 0, 0)), "2026-09-08");
	assert.equal(serializeCalendarDate(null), "");
	assert.equal(serializeCalendarDate(""), "");
});

test("sanitizeCalendarFilters drops broken payloads and keeps Frappe tuples", () => {
	assert.deepEqual(sanitizeCalendarFilters(null), []);
	assert.deepEqual(sanitizeCalendarFilters({}), []);
	assert.deepEqual(sanitizeCalendarFilters("not-json"), []);
	assert.deepEqual(
		sanitizeCalendarFilters('[["Event","status","=","Open",false]]'),
		[["Event", "status", "=", "Open", false]]
	);
	assert.deepEqual(
		sanitizeCalendarFilters([
			["Event", "status", "=", "Open"],
			{ broken: true },
			["Event"],
		]),
		[["Event", "status", "=", "Open"]]
	);
});

test("eventEmployee reads custom_employé from EventApi shapes and instance id", () => {
	assert.equal(eventEmployee({ custom_employé: "Elmedhi Chaoui" }), "Elmedhi Chaoui");
	assert.equal(
		eventEmployee({ extendedProps: { custom_employé: "Anthony" } }),
		"Anthony"
	);
	assert.equal(
		eventEmployee({
			extendedProps: { extendedProps: { custom_employé: "Nested" } },
		}),
		"Nested"
	);
	assert.equal(
		eventEmployee({
			_def: { extendedProps: { custom_employé: "Internal" } },
		}),
		"Internal"
	);
	assert.equal(
		eventEmployee({
			id: "EV02793::2026-10-12 09:15:00::Elmedhi Chaoui",
		}),
		"Elmedhi Chaoui"
	);
	assert.equal(
		eventEmployee({
			event: { extendedProps: { custom_employé: "ViaInfo" } },
		}),
		"ViaInfo"
	);
	assert.equal(eventEmployee({ id: "EV-1::_::_" }), "");
	assert.equal(eventEmployee(null), "");
});

test("employeeFromInstanceId strips the Event name and start", () => {
	assert.equal(
		employeeFromInstanceId("EV02793::2026-10-12 09:15:00::Elmedhi Chaoui"),
		"Elmedhi Chaoui"
	);
	assert.equal(employeeFromInstanceId("EV02793::x::_"), "");
	assert.equal(employeeFromInstanceId("EV02793"), "");
});

test("employeesFromEvents groups loaded FC events even without API", () => {
	const cal = {
		fullCalendar: {
			getEvents: () => [
				{
					id: "EV-1::2026-09-08 09:00:00::Elmedhi Chaoui",
					extendedProps: { custom_employé: "Elmedhi Chaoui", color: "#111" },
					backgroundColor: "#111",
				},
				{
					id: "EV-2::2026-09-08 10:00:00::Anthony",
					custom_employé: "Anthony",
					color: "#222",
				},
				{
					id: "EV-1::2026-09-08 09:00:00::Elmedhi Chaoui",
					extendedProps: { custom_employé: "Elmedhi Chaoui" },
				},
			],
		},
	};
	const rows = employeesFromEvents(cal);
	const byName = Object.fromEntries(rows.map((r) => [r.name, r]));
	assert.equal(byName["Elmedhi Chaoui"].event_count, 2);
	assert.equal(byName.Anthony.event_count, 1);
	assert.equal(byName["Elmedhi Chaoui"].color, "#111");
});

test("collectCalendarEvents prefers an explicit eventsSet payload, even if empty", () => {
	const cal = {
		fullCalendar: {
			getEvents: () => [{ id: "stale", custom_employé: "Old" }],
		},
	};
	assert.equal(collectCalendarEvents(cal, []).length, 0);
	assert.equal(collectCalendarEvents(cal)[0].custom_employé, "Old");
});

test("employeesFromEvents uses eventsSet hint when getEvents is missing", () => {
	const rows = employeesFromEvents({ fullCalendar: {} }, [
		{ id: "EV-9::s::Solène", extendedProps: { custom_employé: "Solène" } },
	]);
	assert.equal(rows.length, 1);
	assert.equal(rows[0].name, "Solène");
});

test("mergeEmployeeRows keeps event-derived list and enriches from API", () => {
	const fromEvents = [
		{ name: "EMP-1", employee_name: "EMP-1", color: "#aaa", event_count: 3 },
	];
	const fromApi = [
		{ name: "EMP-1", employee_name: "Alice", color: "#abc", event_count: 3 },
		{ name: "EMP-2", employee_name: "Bob", color: "#def", event_count: 1 },
	];
	const merged = mergeEmployeeRows(fromEvents, fromApi);
	assert.equal(merged.length, 1);
	assert.equal(merged[0].employee_name, "Alice");
	assert.equal(merged[0].color, "#abc");
	assert.deepEqual(mergeEmployeeRows([], fromApi), fromApi);
	assert.deepEqual(mergeEmployeeRows(fromEvents, []), fromEvents);
});

test("asEmployeeRows ignores non-array API payloads", () => {
	assert.deepEqual(asEmployeeRows([{ name: "A" }]), [{ name: "A" }]);
	assert.deepEqual(asEmployeeRows('[{"name":"A"}]'), [{ name: "A" }]);
	assert.deepEqual(asEmployeeRows({ message: [] }), []);
	assert.deepEqual(asEmployeeRows(null), []);
});

test("stampPreparedEvent keeps custom_employé on the event and in extendedProps", () => {
	const stamped = stampPreparedEvent({
		name: "EV-1",
		calendar_instance_id: "EV-1::2026-09-08 09:00:00::Elmedhi Chaoui",
		custom_employé: "Elmedhi Chaoui",
		color: "#111",
	});
	assert.equal(stamped.id, "EV-1::2026-09-08 09:00:00::Elmedhi Chaoui");
	assert.equal(stamped.custom_employé, "Elmedhi Chaoui");
	assert.equal(stamped.extendedProps.custom_employé, "Elmedhi Chaoui");
	assert.equal(stamped.extendedProps.name, "EV-1");
	assert.equal(eventEmployee(stamped), "Elmedhi Chaoui");
});

test("isEventCalendarRoute accepts List/Event/Calendar only", () => {
	assert.equal(isEventCalendarRoute(["List", "Event", "Calendar"]), true);
	assert.equal(isEventCalendarRoute(["list", "event", "calendar", "default"]), true);
	assert.equal(isEventCalendarRoute(["List", "Event", "List"]), false);
	assert.equal(isEventCalendarRoute(["Form", "Event", "EV-1"]), false);
	assert.equal(isEventCalendarRoute(["List", "Event"]), false);
	assert.equal(isEventCalendarRoute(null), false);
});

test("calendarLayoutOptions uses auto height on phone and 100svh on desktop", () => {
	assert.equal(isMobileCalendarViewport(375), true);
	assert.equal(isMobileCalendarViewport(CALENDAR_MOBILE_MAX_PX), false);
	assert.deepEqual(calendarLayoutOptions(390), { height: "auto", expandRows: false });
	assert.deepEqual(calendarLayoutOptions(1280), {
		height: DESKTOP_CALENDAR_HEIGHT,
		expandRows: true,
	});
});

test("applyEventCalendarPageClass toggles the desk body class", () => {
	const classes = new Set();
	const doc = {
		body: {
			classList: {
				toggle(name, on) {
					if (on) classes.add(name);
					else classes.delete(name);
				},
				contains(name) {
					return classes.has(name);
				},
			},
		},
	};
	assert.equal(applyEventCalendarPageClass(doc, true), true);
	assert.equal(classes.has(EVENT_CALENDAR_PAGE_CLASS), true);
	assert.equal(applyEventCalendarPageClass(doc, false), false);
	assert.equal(classes.has(EVENT_CALENDAR_PAGE_CLASS), false);
});

test("hideEventCalendarListSidebar closes list overlay and unlocks html scroll", () => {
	const overlay = {
		classList: {
			opened: true,
			remove(name) {
				if (name === "opened") this.opened = false;
			},
		},
	};
	const closer = {
		removed: false,
		remove() {
			this.removed = true;
		},
	};
	const section = {
		classList: {
			opened: true,
			remove(name) {
				if (name === "opened") this.opened = false;
			},
		},
		querySelector(sel) {
			if (sel === ".overlay-sidebar") return overlay;
			if (sel === ".close-sidebar") return closer;
			return null;
		},
	};
	const wrapper = {
		classList: {
			added: new Set(),
			add(name) {
				this.added.add(name);
			},
		},
	};
	const root = {
		documentElement: { style: { overflowY: "hidden" } },
		body: { style: { overflow: "hidden", overflowY: "hidden" } },
		querySelectorAll(sel) {
			if (sel === ".layout-side-section") return [section];
			if (sel.includes("page-container")) return [wrapper];
			return [];
		},
	};

	const result = hideEventCalendarListSidebar(root);
	assert.equal(result.hidden, 1);
	assert.equal(result.overflowRestored, true);
	assert.equal(section.classList.opened, false);
	assert.equal(overlay.classList.opened, false);
	assert.equal(closer.removed, true);
	assert.equal(root.documentElement.style.overflowY, "");
	assert.equal(wrapper.classList.added.has("no-list-sidebar"), true);
});
