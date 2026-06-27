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
	},
	secondary_status_color: {
		Public: "white",
		Private: "white",
	},
	get_events_method: "frappe.desk.doctype.event.event.get_events",
	options: {
		weekends: false,
	},
};
