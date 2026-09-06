// Vue jour sur mobile, semaine sur desktop par défaut (respecte la préférence si déjà choisie)
if (!localStorage.getItem("cal_initialView")) {
	const isMobile = window.innerWidth < 768;
	localStorage.setItem("cal_initialView", isMobile ? "timeGridDay" : "timeGridWeek");
}

frappe.views.calendar["Event"] = {
	field_map: {
		start: "starts_on",
		end: "ends_on",
		// `name` = document Event. L'id FullCalendar unique est posé après
		// prepare_events (`calendar_instance_id`) pour pouvoir afficher N blocs.
		id: "name",
		allDay: "all_day",
		title: "subject",
		status: "event_type",
		color: "color",
		rrule: "rrule",
		secondary_status: "status",
		custom_employé: "custom_employé",
	},
	secondary_status_color: {
		Public: "white",
		Private: "white",
	},
	get_events_method: "frappe.desk.doctype.event.event.get_events",
	options: {
		weekends: false,
		height: "calc(100svh - 130px)",
		expandRows: true,
		eventClassNames: function (arg) {
			const api = frappe.vt_cal_employees;
			if (!api || !api.event_employee) return [];
			const emp = api.event_employee(arg.event);
			return api.is_visible(emp) ? [] : ["vt-cal-hidden"];
		},
	},
};

// ---------------------------------------------------------------------------
// Filtre « Employés » : dropdown compact dans la barre de filtres (plus de
// sidebar). Les Events restent chargés ; on masque les blocs côté client.
// ---------------------------------------------------------------------------
frappe.provide("frappe.vt_cal_employees");
frappe.provide("frappe.vt");

(function () {
	const NONE = "__none__";
	const METHOD = "vt_internal.vt_internal.api.event_calendar.get_calendar_employees";

	const state = {
		cal: null,
		employees: [],
		userUnchecked: new Set(),
		rangeKey: "",
		applying: false,
		menuOpen: false,
	};

	function helpers() {
		return frappe.vt || {};
	}

	function eventDocName(ev) {
		if (helpers().event_doc_name) return helpers().event_doc_name(ev);
		if (!ev) return "";
		if (ev.event && ev.event !== ev) return eventDocName(ev.event);
		const xp = ev.extendedProps || {};
		if (xp.name) return String(xp.name).split("::")[0];
		if (typeof ev.name === "string" && ev.name && ev.name.indexOf("::") === -1) {
			return ev.name;
		}
		if (typeof ev.id === "string" && ev.id) return ev.id.split("::")[0];
		return "";
	}

	function eventFormHref(name) {
		if (helpers().event_form_href) return helpers().event_form_href(name);
		const doc = eventDocName(name);
		if (!doc) return "";
		const first = (window.location.pathname || "/app").split("/").filter(Boolean)[0] || "app";
		const root = first === "desk" ? "desk" : "app";
		return `/${root}/event/${encodeURIComponent(doc)}`;
	}

	function rewriteUpdateArgs(result, ev) {
		if (helpers().rewrite_update_args) return helpers().rewrite_update_args(result, ev);
		const name = eventDocName(ev);
		if (!name || !result) return result;
		if (result.args) result.args.name = name;
		else if (Object.prototype.hasOwnProperty.call(result, "name") || result.name !== undefined) {
			result.name = name;
		}
		return result;
	}

	function empKey(name) {
		return name || NONE;
	}

	function eventEmployee(ev) {
		if (!ev) return "";
		const xp = ev.extendedProps || {};
		return xp.custom_employé || ev.custom_employé || "";
	}

	function isVisible(name) {
		return !state.userUnchecked.has(empKey(name));
	}

	function safeColor(color) {
		if (typeof color === "string" && /^#[0-9A-Fa-f]{3,8}$/.test(color.trim())) {
			return color.trim();
		}
		return "#94a3b8";
	}

	function escapeHtml(text) {
		if (frappe.utils && frappe.utils.escape_html) {
			return frappe.utils.escape_html(text || "");
		}
		return $("<div>").text(text || "").html();
	}

	function $filter() {
		return $(document).find(".vt-cal-emp-filter");
	}

	function rewriteEventLinks(el, name) {
		if (!el || !name) return;
		const href = eventFormHref(name);
		if (!href) return;
		const nodes = [];
		if (el.matches && el.matches("a[href]")) nodes.push(el);
		if (el.querySelectorAll) {
			el.querySelectorAll("a[href]").forEach((a) => nodes.push(a));
		}
		nodes.forEach((a) => {
			const cur = a.getAttribute("href") || "";
			if (!cur || cur.indexOf("::") !== -1 || /%3A%3A/i.test(cur) || /\/event\//i.test(cur)) {
				a.setAttribute("href", href);
			}
		});
		if (el.dataset) {
			el.dataset.vtEventName = name;
		}
	}

	function markEventEl(info) {
		if (!info || !info.el) return;
		const emp = eventEmployee(info.event);
		info.el.dataset.vtEmployee = empKey(emp);
		info.el.classList.toggle("vt-cal-hidden", !isVisible(emp));
		const name = eventDocName(info.event);
		rewriteEventLinks(info.el, name);
		requestAnimationFrame(() => rewriteEventLinks(info.el, name));
		setTimeout(() => rewriteEventLinks(info.el, name), 0);
	}

	function applyVisibility() {
		if (state.applying) return;
		const cal = state.cal;
		if (!cal) return;
		state.applying = true;
		try {
			const fc = cal.fullCalendar;
			if (fc && typeof fc.getEvents === "function") {
				fc.getEvents().forEach((ev) => {
					const show = isVisible(eventEmployee(ev));
					if (typeof ev.setProp === "function") {
						ev.setProp("display", show ? "auto" : "none");
					}
				});
			}
			const $root = cal.$wrapper || (cal.list_view && cal.list_view.$result);
			if ($root && $root.length) {
				$root.find(".fc-event").each(function () {
					const key = this.dataset.vtEmployee || NONE;
					const emp = key === NONE ? "" : key;
					this.classList.toggle("vt-cal-hidden", !isVisible(emp));
				});
			}
		} finally {
			state.applying = false;
		}
	}

	function selectedLabel() {
		const rows = state.employees;
		if (!rows.length) return __("Aucun");
		const selected = rows.filter((row) => isVisible(row.name));
		if (selected.length === rows.length) return __("Tous");
		if (!selected.length) return __("Aucun");
		if (selected.length === 1) return selected[0].employee_name || selected[0].name || __("Sans employé");
		return __("{0} pers.", [String(selected.length)]);
	}

	function renderFilter() {
		const $el = $filter();
		if (!$el.length) return;

		$el.find(".vt-cal-emp-filter__value").text(selectedLabel());
		$el.find(".vt-cal-emp-filter__btn").attr("aria-expanded", state.menuOpen ? "true" : "false");
		$el.find(".vt-cal-emp-filter__menu").prop("hidden", !state.menuOpen);

		const $list = $el.find(".vt-cal-emp-filter__list");
		const rows = state.employees;
		if (!rows.length) {
			$list.html(
				`<p class="vt-cal-emp-filter__empty">${escapeHtml(__("Aucun employé sur cette période"))}</p>`
			);
			return;
		}

		$list.html(
			rows
				.map((row) => {
					const key = empKey(row.name);
					const checked = isVisible(row.name) ? " checked" : "";
					const color = safeColor(row.color);
					const label = row.employee_name || row.name || __("Sans employé");
					const count =
						row.event_count != null
							? ` <span class="vt-cal-emp-filter__badge">${row.event_count}</span>`
							: "";
					return `<label class="vt-cal-emp-filter__row">
						<input type="checkbox" class="vt-cal-emp-filter__cb" value="${escapeHtml(key)}"${checked} />
						<span class="vt-cal-emp-filter__swatch" style="background:${color}"></span>
						<span class="vt-cal-emp-filter__name">${escapeHtml(label)}</span>${count}
					</label>`;
				})
				.join("")
		);
	}

	function onCheckboxChange(ev) {
		const key = ev.target.value;
		if (ev.target.checked) {
			state.userUnchecked.delete(key);
		} else {
			state.userUnchecked.add(key);
		}
		renderFilter();
		applyVisibility();
	}

	function selectAll(all) {
		if (all) {
			state.employees.forEach((row) => state.userUnchecked.delete(empKey(row.name)));
		} else {
			state.employees.forEach((row) => state.userUnchecked.add(empKey(row.name)));
		}
		renderFilter();
		applyVisibility();
	}

	function employeesFromEvents(cal) {
		const fc = cal.fullCalendar;
		if (!fc || typeof fc.getEvents !== "function") return [];
		const counts = new Map();
		const colors = new Map();
		fc.getEvents().forEach((ev) => {
			const name = eventEmployee(ev);
			const key = empKey(name);
			counts.set(key, (counts.get(key) || 0) + 1);
			if (!colors.has(key)) {
				const color = ev.backgroundColor || (ev.extendedProps && ev.extendedProps.color) || ev.color;
				if (color) colors.set(key, color);
			}
		});
		return Array.from(counts.entries()).map(([key, event_count]) => ({
			name: key === NONE ? "" : key,
			employee_name: key === NONE ? __("Sans employé") : key,
			color: colors.get(key) || "#94a3b8",
			event_count,
		}));
	}

	function resolveNames(rows) {
		const ids = rows.map((r) => r.name).filter(Boolean);
		if (!ids.length) {
			return Promise.resolve(rows);
		}
		return frappe.db
			.get_list("Employee", {
				filters: { name: ["in", ids] },
				fields: ["name", "employee_name", "custom_couleur"],
				limit: 500,
			})
			.then((list) => {
				const map = {};
				(list || []).forEach((e) => {
					map[e.name] = e;
				});
				return rows.map((row) => {
					const d = map[row.name];
					if (!d) return row;
					return {
						...row,
						employee_name: d.employee_name || row.employee_name,
						color: d.custom_couleur || row.color,
					};
				});
			})
			.catch(() => rows);
	}

	function syncEmployeesFromEvents(cal) {
		const fallback = employeesFromEvents(cal);
		if (!fallback.length && !state.employees.length) return;
		const onlyUnassigned = fallback.length === 1 && !fallback[0].name;
		if (onlyUnassigned && state.employees.some((row) => row.name)) {
			return;
		}
		const known = {};
		state.employees.forEach((row) => {
			known[empKey(row.name)] = row;
		});
		state.employees = fallback.map((row) => {
			const prev = known[empKey(row.name)];
			if (!prev) return row;
			return {
				...row,
				employee_name: prev.employee_name || row.employee_name,
				color: prev.color || row.color,
			};
		});
		renderFilter();
	}

	function refreshEmployees(cal, info) {
		const start = cal.get_system_datetime ? cal.get_system_datetime(info.start) : info.start;
		const end = cal.get_system_datetime ? cal.get_system_datetime(info.end) : info.end;
		const filters =
			cal.list_view && cal.list_view.filter_area && cal.list_view.filter_area.get
				? cal.list_view.filter_area.get()
				: [];
		const rangeKey = `${start}|${end}|${JSON.stringify(filters)}`;
		state.rangeKey = rangeKey;

		frappe.call({
			method: METHOD,
			args: { start, end, filters },
			callback: (r) => {
				if (state.rangeKey !== rangeKey) return;
				state.employees = r.message || [];
				renderFilter();
				applyVisibility();
			},
			error: () => {
				resolveNames(employeesFromEvents(cal)).then((rows) => {
					if (state.rangeKey !== rangeKey) return;
					state.employees = rows;
					renderFilter();
					applyVisibility();
				});
			},
		});
	}

	function filterHost(cal) {
		const lv = cal.list_view;
		if (lv) {
			if (lv.page && lv.page.page_form && lv.page.page_form.length && lv.page.page_form.is(":visible")) {
				return lv.page.page_form;
			}
			const wrapper = lv.page && lv.page.wrapper;
			if (wrapper) {
				const $std = $(wrapper)
					.find(".page-form:visible, .standard-filter-section:visible, .filter-section:visible")
					.first();
				if ($std.length) return $std;
			}
			if (lv.$page) {
				const $fromList = lv.$page.find(".page-form:visible, .filter-section:visible").first();
				if ($fromList.length) return $fromList;
			}
		}
		return null;
	}

	function injectFilter(cal) {
		if ($(document).find(".vt-cal-emp-filter").length) return;

		const $el = $(`
			<div class="vt-cal-emp-filter" data-vt-cal-emp-filter="1">
				<button type="button" class="vt-cal-emp-filter__btn" aria-expanded="false" aria-haspopup="true">
					<span class="vt-cal-emp-filter__label">${escapeHtml(__("Employés"))}</span>
					<span class="vt-cal-emp-filter__value">${escapeHtml(__("Tous"))}</span>
				</button>
				<div class="vt-cal-emp-filter__menu" hidden>
					<div class="vt-cal-emp-filter__actions">
						<button type="button" class="vt-cal-emp-filter__link" data-action="all">${escapeHtml(
							__("Tout")
						)}</button>
						<button type="button" class="vt-cal-emp-filter__link" data-action="none">${escapeHtml(
							__("Aucun")
						)}</button>
					</div>
					<div class="vt-cal-emp-filter__list" role="group" aria-label="${escapeHtml(__("Employés"))}"></div>
				</div>
			</div>
		`);

		const $host = filterHost(cal);
		if ($host && $host.length) {
			$host.append($el);
		} else {
			const $bar = $('<div class="vt-cal-filterbar"></div>').append($el);
			if (cal.$wrapper && cal.$wrapper.length) {
				if (cal.$toolbar && cal.$toolbar.length) {
					cal.$toolbar.append($el);
				} else {
					cal.$wrapper.prepend($bar);
				}
			} else if (cal.$cal && cal.$cal.length) {
				cal.$cal.before($bar);
			}
		}

		$el.on("click", ".vt-cal-emp-filter__btn", (ev) => {
			ev.preventDefault();
			ev.stopPropagation();
			state.menuOpen = !state.menuOpen;
			renderFilter();
		});
		$el.on("change", ".vt-cal-emp-filter__cb", onCheckboxChange);
		$el.on("click", "[data-action=all]", () => selectAll(true));
		$el.on("click", "[data-action=none]", () => selectAll(false));
	}

	function closeMenuOnOutside(ev) {
		if (!state.menuOpen) return;
		if (ev.target.closest && ev.target.closest(".vt-cal-emp-filter")) return;
		state.menuOpen = false;
		renderFilter();
	}

	function bindCalendar(cal) {
		if (cal.__vt_emp_bound) return;
		const fc = cal.fullCalendar;
		if (!fc || typeof fc.on !== "function") return;
		cal.__vt_emp_bound = true;
		fc.on("datesSet", (info) => refreshEmployees(cal, info));
		fc.on("eventsSet", () => {
			syncEmployeesFromEvents(cal);
			applyVisibility();
		});
		if (fc.view) {
			refreshEmployees(cal, { start: fc.view.activeStart, end: fc.view.activeEnd });
		}
	}

	function attach(cal) {
		if (!cal || cal.doctype !== "Event") return;
		state.cal = cal;
		injectFilter(cal);
		bindCalendar(cal);
		renderFilter();
	}

	function openEventForm(name) {
		const doc = eventDocName(name);
		if (!doc) return false;
		if (!frappe.model || !frappe.model.can_read || frappe.model.can_read("Event")) {
			frappe.set_route("Form", "Event", doc);
		}
		return true;
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

	function patchCalendarClass() {
		const Calendar = frappe.views && frappe.views.Calendar;
		if (!Calendar || Calendar.prototype.__vt_emp_patched) {
			return Boolean(Calendar);
		}
		const proto = Calendar.prototype;

		const origPrepare = proto.prepare_events;
		if (typeof origPrepare === "function") {
			proto.prepare_events = function (events) {
				const prepared = origPrepare.call(this, events);
				if (this.doctype !== "Event") return prepared;
				return (prepared || []).map((d) => {
					const name = eventDocName(d.name || d.id || d);
					if (name) d.name = name;
					if (d.calendar_instance_id) {
						d.id = d.calendar_instance_id;
					}
					if (name) {
						d.url = eventFormHref(name);
					}
					return d;
				});
			};
		}

		const origGetUpdateArgs = proto.get_update_args;
		if (typeof origGetUpdateArgs === "function") {
			proto.get_update_args = function (event) {
				const result = origGetUpdateArgs.apply(this, arguments);
				if (this.doctype !== "Event") return result;
				return rewriteUpdateArgs(result, event);
			};
		}

		const origUpdate = proto.update_event;
		if (typeof origUpdate === "function") {
			proto.update_event = function (event, revertFunc) {
				if (this.doctype === "Event" && event) {
					const name = eventDocName(event);
					if (name && frappe.model && typeof frappe.model.remove_from_locals === "function") {
						frappe.model.remove_from_locals(this.doctype, name);
					}
				}
				return origUpdate.apply(this, arguments);
			};
		}

		const origSetup = proto.setup_options;
		if (typeof origSetup === "function") {
			proto.setup_options = function (defaults) {
				origSetup.call(this, defaults);
				if (this.doctype !== "Event" || !this.cal_options) return;
				const prevMount = this.cal_options.eventDidMount;
				this.cal_options.eventDidMount = (info) => {
					if (typeof prevMount === "function") prevMount.call(this, info);
					markEventEl(info);
				};
				const prevClick = this.cal_options.eventClick;
				this.cal_options.eventClick = (info) => {
					const name = eventDocName(info);
					if (name) {
						if (info && info.jsEvent && typeof info.jsEvent.preventDefault === "function") {
							info.jsEvent.preventDefault();
						}
						openEventForm(name);
						return;
					}
					if (typeof prevClick === "function") return prevClick.call(this, info);
				};
			};
		}

		const origMake = proto.make;
		if (typeof origMake === "function") {
			proto.make = function () {
				origMake.apply(this, arguments);
				if (this.doctype === "Event") attach(this);
			};
		}

		proto.__vt_emp_patched = true;
		return true;
	}

	function attachIfReady() {
		const route = frappe.get_route ? frappe.get_route() : [];
		if (!(route[0] === "List" && route[1] === "Event" && route[2] === "Calendar")) {
			state.menuOpen = false;
			return;
		}
		const cal = cur_list && cur_list.calendar;
		if (cal && cal.fullCalendar) attach(cal);
	}

	function boot() {
		patchSetRoute();
		patchCalendarClass();
		attachIfReady();
	}

	frappe.vt_cal_employees.is_visible = isVisible;
	frappe.vt_cal_employees.event_employee = eventEmployee;
	frappe.vt_cal_employees.event_doc_name = eventDocName;
	frappe.vt_cal_employees.event_form_href = eventFormHref;
	frappe.vt_cal_employees.rewrite_update_args = rewriteUpdateArgs;
	frappe.vt_cal_employees.attach = attach;

	$(document).on("click.vt-cal-emp-filter", closeMenuOnOutside);

	const started = Date.now();
	const timer = setInterval(() => {
		if (patchCalendarClass() || Date.now() - started > 15000) {
			clearInterval(timer);
			attachIfReady();
		}
	}, 40);

	if (frappe.router && typeof frappe.router.on === "function") {
		frappe.router.on("change", () => {
			patchSetRoute();
			patchCalendarClass();
			setTimeout(attachIfReady, 50);
		});
	}

	if (frappe.after_ajax) {
		frappe.after_ajax(boot);
	} else {
		boot();
	}
})();
