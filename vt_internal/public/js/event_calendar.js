// Vue jour sur mobile, semaine sur desktop par défaut (respecte la préférence si déjà choisie)
if (!localStorage.getItem("cal_initialView")) {
	const isMobile = window.innerWidth < 768;
	localStorage.setItem("cal_initialView", isMobile ? "timeGridDay" : "timeGridWeek");
}

frappe.views.calendar["Event"] = {
	field_map: {
		start: "starts_on",
		end: "ends_on",
		id: "name",
		allDay: "all_day",
		title: "subject",
		status: "event_type",
		color: "color",
		rrule: "rrule",
		secondary_status: "status",
		// Expose le Link Employee pour filtrer la vue (sidebar multi-employés).
		custom_employé: "custom_employé",
	},
	secondary_status_color: {
		Public: "white",
		Private: "white",
	},
	get_events_method: "frappe.desk.doctype.event.event.get_events",
	options: {
		weekends: false,
		// Utilise toute la hauteur disponible (le header "Statut" et le
		// footer sont masqués via calendar.css) et étire les créneaux
		// horaires pour supprimer le vide blanc en bas.
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
// Sidebar « Employés » : cases à cocher pour comparer 2–3 personnes (ou plus)
// sur le même FullCalendar. Les Events restent chargés ; on masque côté client.
// ---------------------------------------------------------------------------
frappe.provide("frappe.vt_cal_employees");

(function () {
	const NONE = "__none__";
	const METHOD = "vt_internal.vt_internal.api.event_calendar.get_calendar_employees";
	const COLLAPSE_KEY = "vt_cal_emp_collapsed";

	const state = {
		cal: null,
		employees: [],
		userUnchecked: new Set(),
		rangeKey: "",
		applying: false,
	};

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

	function defaultCollapsed() {
		const stored = localStorage.getItem(COLLAPSE_KEY);
		if (stored === "1") return true;
		if (stored === "0") return false;
		return window.innerWidth < 768;
	}

	function $aside() {
		return state.cal && state.cal.$wrapper ? state.cal.$wrapper.find(".vt-cal-employees") : $();
	}

	function markEventEl(info) {
		if (!info || !info.el) return;
		const emp = eventEmployee(info.event);
		info.el.dataset.vtEmployee = empKey(emp);
		info.el.classList.toggle("vt-cal-hidden", !isVisible(emp));
	}

	function applyVisibility() {
		if (state.applying) return;
		const $root = state.cal && state.cal.$wrapper;
		if (!$root || !$root.length) return;
		const events = $root.find(".fc-event").toArray();
		const marked = events.some((el) => el.dataset.vtEmployee);
		if (!marked && state.cal.fullCalendar && typeof state.cal.fullCalendar.render === "function") {
			state.applying = true;
			try {
				state.cal.fullCalendar.render();
			} finally {
				state.applying = false;
			}
			return;
		}
		events.forEach((el) => {
			const key = el.dataset.vtEmployee || NONE;
			const emp = key === NONE ? "" : key;
			el.classList.toggle("vt-cal-hidden", !isVisible(emp));
		});
	}

	function renderList() {
		const $list = $aside().find(".vt-cal-employees__list");
		if (!$list.length) return;

		const rows = state.employees;
		$aside()
			.find(".vt-cal-employees__count")
			.text(rows.length ? String(rows.length) : "");

		if (!rows.length) {
			$list.html(
				`<p class="vt-cal-employees__empty">${escapeHtml(
					__("Aucun employé sur cette période")
				)}</p>`
			);
			return;
		}

		const html = rows
			.map((row) => {
				const key = empKey(row.name);
				const checked = isVisible(row.name) ? " checked" : "";
				const color = safeColor(row.color);
				const label = row.employee_name || row.name || __("Sans employé");
				const count = row.event_count != null ? ` <span class="vt-cal-employees__badge">${row.event_count}</span>` : "";
				return `<label class="vt-cal-employees__row">
					<input type="checkbox" class="vt-cal-employees__cb" value="${escapeHtml(key)}"${checked} />
					<span class="vt-cal-employees__swatch" style="background:${color}"></span>
					<span class="vt-cal-employees__name">${escapeHtml(label)}</span>${count}
				</label>`;
			})
			.join("");
		$list.html(html);
	}

	function setCollapsed(collapsed) {
		const $el = $aside();
		$el.toggleClass("is-collapsed", collapsed);
		$el.find(".vt-cal-employees__toggle").attr("aria-expanded", collapsed ? "false" : "true");
		localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
	}

	function onCheckboxChange(ev) {
		const key = ev.target.value;
		if (ev.target.checked) {
			state.userUnchecked.delete(key);
		} else {
			state.userUnchecked.add(key);
		}
		applyVisibility();
	}

	function selectAll(all) {
		if (all) {
			state.employees.forEach((row) => state.userUnchecked.delete(empKey(row.name)));
		} else {
			state.employees.forEach((row) => state.userUnchecked.add(empKey(row.name)));
		}
		renderList();
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
		renderList();
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
				renderList();
				applyVisibility();
			},
			error: () => {
				resolveNames(employeesFromEvents(cal)).then((rows) => {
					if (state.rangeKey !== rangeKey) return;
					state.employees = rows;
					renderList();
					applyVisibility();
				});
			},
		});
	}

	function injectSidebar(cal) {
		if (!cal.$cal || !cal.$cal.length) return;
		if (cal.$wrapper.find(".vt-cal-layout").length) return;

		const $layout = $('<div class="vt-cal-layout"></div>');
		const $asideEl = $(`
			<aside class="vt-cal-employees" aria-label="${escapeHtml(__("Employés"))}">
				<div class="vt-cal-employees__head">
					<button type="button" class="vt-cal-employees__toggle" aria-expanded="true">
						<span class="vt-cal-employees__title">${escapeHtml(__("Employés"))}</span>
						<span class="vt-cal-employees__count"></span>
					</button>
				</div>
				<div class="vt-cal-employees__body">
					<div class="vt-cal-employees__actions">
						<button type="button" class="vt-cal-employees__link" data-action="all">${escapeHtml(
							__("Tout sélectionner")
						)}</button>
						<button type="button" class="vt-cal-employees__link" data-action="none">${escapeHtml(
							__("Tout désélectionner")
						)}</button>
					</div>
					<div class="vt-cal-employees__list" role="group" aria-label="${escapeHtml(
						__("Employés")
					)}"></div>
				</div>
			</aside>
		`);
		cal.$cal.wrap($layout);
		cal.$cal.parent().prepend($asideEl);
		if (cal.fullCalendar && typeof cal.fullCalendar.updateSize === "function") {
			cal.fullCalendar.updateSize();
		}

		if (defaultCollapsed()) {
			setCollapsed(true);
		}

		$asideEl.on("click", ".vt-cal-employees__toggle", () => {
			setCollapsed(!$asideEl.hasClass("is-collapsed"));
		});
		$asideEl.on("change", ".vt-cal-employees__cb", onCheckboxChange);
		$asideEl.on("click", "[data-action=all]", () => selectAll(true));
		$asideEl.on("click", "[data-action=none]", () => selectAll(false));
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
		injectSidebar(cal);
		bindCalendar(cal);
	}

	function patchCalendarClass() {
		const Calendar = frappe.views && frappe.views.Calendar;
		if (!Calendar || Calendar.prototype.__vt_emp_patched) {
			return Boolean(Calendar);
		}
		const proto = Calendar.prototype;

		const origSetup = proto.setup_options;
		if (typeof origSetup === "function") {
			proto.setup_options = function (defaults) {
				origSetup.call(this, defaults);
				if (this.doctype !== "Event" || !this.cal_options) return;
				const prev = this.cal_options.eventDidMount;
				this.cal_options.eventDidMount = (info) => {
					if (typeof prev === "function") prev.call(this, info);
					markEventEl(info);
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
			return;
		}
		const cal = cur_list && cur_list.calendar;
		if (cal && cal.fullCalendar) attach(cal);
	}

	function boot() {
		patchCalendarClass();
		attachIfReady();
	}

	frappe.vt_cal_employees.is_visible = isVisible;
	frappe.vt_cal_employees.event_employee = eventEmployee;
	frappe.vt_cal_employees.attach = attach;

	const started = Date.now();
	const timer = setInterval(() => {
		if (patchCalendarClass() || Date.now() - started > 15000) {
			clearInterval(timer);
			attachIfReady();
		}
	}, 40);

	if (frappe.router && typeof frappe.router.on === "function") {
		frappe.router.on("change", () => {
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
