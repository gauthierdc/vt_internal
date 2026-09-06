import assert from "node:assert/strict";
import test from "node:test";
import {
	asEmployeeRows,
	collectCalendarEvents,
	employeeFromInstanceId,
	employeesFromEvents,
	eventEmployee,
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
