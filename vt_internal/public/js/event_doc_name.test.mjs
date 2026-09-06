import assert from "node:assert/strict";
import test from "node:test";
import {
	eventDocName,
	eventFormHref,
	isEventInstanceId,
	rewriteUpdateArgs,
} from "./event_doc_name.js";

test("eventDocName strips FullCalendar instance id", () => {
	assert.equal(
		eventDocName("EV02793::2026-10-12 09:15:00::Elmedhi Chaoui"),
		"EV02793"
	);
	assert.equal(
		eventDocName("EV02793%3A%3A2026-10-12%2009%3A15%3A00%3A%3AElmedhi%20Chaoui"),
		"EV02793"
	);
	assert.equal(
		eventDocName("/desk/event/EV02793%3A%3A2026-10-12%2009%3A15%3A00%3A%3AElmedhi%20Chaoui"),
		"EV02793"
	);
	assert.equal(eventDocName("https://bureau.verretransparence.fr/desk/event/EV02793"), "EV02793");
	assert.equal(eventDocName("/app/event/EV02793"), "EV02793");
	assert.equal(eventDocName("EV02793"), "EV02793");
	assert.equal(eventDocName(""), "");
	assert.equal(eventDocName(null), "");
});

test("eventDocName reads FullCalendar event objects", () => {
	assert.equal(
		eventDocName({
			id: "EV02793::2026-10-12 09:15:00::Elmedhi Chaoui",
			extendedProps: { name: "EV02793" },
		}),
		"EV02793"
	);
	assert.equal(
		eventDocName({
			event: {
				id: "EV-1::x::emp",
				name: "EV-1",
				extendedProps: { name: "EV-1" },
			},
		}),
		"EV-1"
	);
	assert.equal(eventDocName({ id: "EV-9::a::b", name: "EV-9::a::b" }), "EV-9");
});

test("eventFormHref never embeds the instance id", () => {
	assert.equal(eventFormHref("EV02793", "/desk/event/x"), "/desk/event/EV02793");
	assert.equal(
		eventFormHref("EV02793::2026-10-12 09:15:00::Elmedhi Chaoui", "/desk/list"),
		"/desk/event/EV02793"
	);
	assert.equal(eventFormHref("EV02793", "/app/event/EV00001"), "/app/event/EV02793");
	assert.ok(!eventFormHref("EV02793::x::y", "/desk").includes("::"));
	assert.ok(!eventFormHref("EV02793::x::y", "/desk").includes("%3A%3A"));
});

test("isEventInstanceId detects split calendar ids", () => {
	assert.equal(isEventInstanceId("EV02793::2026-10-12 09:15:00::Emp"), true);
	assert.equal(isEventInstanceId("EV02793%3A%3A2026-10-12"), true);
	assert.equal(isEventInstanceId("EV02793"), false);
});

test("rewriteUpdateArgs forces the real Event name", () => {
	const ev = { id: "EV-1::start::emp", extendedProps: { name: "EV-1" } };
	assert.deepEqual(rewriteUpdateArgs({ args: { name: ev.id, starts_on: "x" } }, ev), {
		args: { name: "EV-1", starts_on: "x" },
	});
	assert.deepEqual(rewriteUpdateArgs({ name: ev.id }, ev), { name: "EV-1" });
});
