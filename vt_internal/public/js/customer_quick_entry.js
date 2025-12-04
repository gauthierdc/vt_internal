/*
 Override the Customer Quick Entry with custom fields and behavior.
 - Basic info: Désignation (customer_name), Groupe de client, Territory
 - Account details: Adresse e-mail, Numéro de mobile
 - Primary address details: Google Maps autocomplete, Address lines, City, Postal Code, Country
 On save:
 - Create Customer
 - Optionally create Address linked to Customer and mark as primary
*/

// Ensure Google Places suggestion dropdown overlays correctly above dialogs
(() => {
	const id = "dev-pac-zfix";
	if (!document.getElementById(id)) {
		const s = document.createElement("style");
		s.id = id;
		s.textContent = `.pac-container{z-index:99999 !important}`;
		document.head.appendChild(s);
	}
})();

(function () {
	function defineOverride() {
		// Ensure base class exists before defining subclass
		if (!(window.frappe && frappe.ui && frappe.ui.form && frappe.ui.form.QuickEntryForm)) {
			return false;
		}

			// Define a custom Quick Entry for Customer with custom dialog
		frappe.ui.form.CustomerQuickEntryForm = class CustomerQuickEntryForm extends frappe.ui.form.QuickEntryForm {
				render_dialog() {
					const me = this;

					const fields = [
						{ fieldtype: "Section Break", label: __("Informations client") },
						{
							fieldtype: "Data",
							fieldname: "customer_name",
							label: __("Désignation"),
							reqd: 1,
						},
						{
							fieldtype: "Link",
							fieldname: "customer_group",
							label: __("Groupe de client"),
							options: "Customer Group",
							reqd: 1,
						},
						{ fieldtype: "Column Break" },
						{
							fieldtype: "Link",
							fieldname: "territory",
							label: __("Territory"),
							options: "Territory",
							reqd: 1,
						},

						{ fieldtype: "Section Break", label: __("Détails du compte principal") },
						{
							fieldtype: "Data",
							fieldname: "email_id",
							label: __("Adresse e-mail"),
							options: "Email",
						},
						{ fieldtype: "Column Break" },
						{
							fieldtype: "Data",
							fieldname: "mobile_no",
							label: __("Numéro de mobile"),
							options: "Phone",
						},

						{ fieldtype: "Section Break", label: __("Recherche google") },
						{
							fieldtype: "HTML",
							fieldname: "gmaps_autocomplete",
							label: __("Recherche d'adresse (Google)"),
						},
						{ fieldtype: "Section Break", label: __("Détails de l'adresse principale") },

						{
							fieldtype: "Data",
							fieldname: "address_line1",
							label: __("Ligne 1 d'adresse"),
						},
						{
							fieldtype: "Data",
							fieldname: "address_line2",
							label: __("Ligne 2 d'adresse"),
						},
						{ fieldtype: "Column Break" },
						{
							fieldtype: "Data",
							fieldname: "city",
							label: __("Ville"),
						},
						{
							fieldtype: "Data",
							fieldname: "pincode",
							label: __("Code postal"),
						},
						{
							fieldtype: "Link",
							fieldname: "country",
							label: __("Pays"),
							options: "Country",
							only_select: 1,
						},
					];

					this.dialog = new frappe.ui.Dialog({
						title: __("New {0}", [__(this.doctype)], this.doctype),
						fields,
						doc: this.doc,
						primary_action_label: __("Enregistrer"),
						primary_action: () => this.handle_save(),
					});

					// Setup Google Places Autocomplete if available
					this.dialog.on_page_show = () => {
						me.setup_gmaps_autocomplete();
						// Default country if available from system defaults
						const sys_country = frappe.boot?.sysdefaults?.country;
						if (sys_country) {
							me.dialog.set_value("country", sys_country);
						}
					};

					// Clean up global quick entry reference when closed
					this.dialog.onhide = () => (frappe.quick_entry = null);

					this.dialog.show();
				}

				async handle_save() {
					if (this.dialog.working) return;

					const values = this.dialog.get_values();
					if (!values) return; // frappe will show validation errors

					try {
						this.dialog.working = true;

						// Create Customer first
						const customer_doc = {
							doctype: "Customer",
							customer_name: values.customer_name,
							customer_group: values.customer_group,
							territory: values.territory,
							email_id: values.email_id,
							mobile_no: values.mobile_no,
						};

						const insert_customer = await frappe.call({
							method: "frappe.client.insert",
							args: { doc: customer_doc },
						});

						const cust = insert_customer.message;

						// Create Address if any address field is provided
						const has_address = [
							"address_line1",
							"city",
							"pincode",
						].every((k) => !!values[k]);

						if (has_address) {
							const address_doc = {
								doctype: "Address",
								address_title: values.customer_name,
								address_type: "Billing",
								is_primary_address: 1,
								address_line1: values.address_line1 || "",
								address_line2: values.address_line2 || "",
								city: values.city || "",
								pincode: values.pincode || "",
								country: values.country || "",
								links: [
									{
										link_doctype: "Customer",
										link_name: cust.name,
									},
								],
							};

							await frappe.call({
								method: "frappe.client.insert",
								args: { doc: address_doc },
							});
						}

						// Success UI and routing
						this.dialog.animation_speed = "slow";
						this.dialog.hide();
						setTimeout(() => {
							frappe.show_alert(
								{ message: __("Nouveau client {0} créé", [cust.name.bold()]), indicator: "green" },
								3
							);
						}, 400);

						// Update calling link or open form
						if (frappe._from_link) {
							frappe.ui.form.update_calling_link(cust);
						} else if (this.after_insert) {
							this.after_insert(cust);
						} else {
							frappe.set_route("Form", cust.doctype, cust.name);
						}
					} catch (e) {
						// On error, open full form to let user complete
						if (!this.skip_redirect_on_error && this.doc) {
							this.doc.__run_link_triggers = false;
							frappe.set_route("Form", this.doctype);
						}
					} finally {
						this.dialog.working = false;
					}
				}
				

				setup_gmaps_autocomplete() {
					const field = this.dialog.get_field("gmaps_autocomplete");
					if (!field) return;
					
					// Render input
					const id = frappe.dom.get_unique_id();
					const $html = $(`
						<div class="gmaps-autocomplete">
							<input type="text" id="${id}" class="form-control" placeholder="${__(
								"Rechercher une adresse"
							)}" autocomplete="off" />
						</div>
					`);
					$(field.wrapper).empty().append($html);

					const input = document.getElementById(id);

					const init_autocomplete = () => {
						try {
							const autocomplete = new google.maps.places.Autocomplete(input, {
								types: ["geocode"],
								fields: ["address_components", "formatted_address"],
							});

							autocomplete.addListener("place_changed", () => {
								const place = autocomplete.getPlace();
								if (!place || !place.address_components) return;
								

								const comp = {};
								for (const c of place.address_components) {
									for (const t of c.types) {
										comp[t] = c;
									}
								}

								// Build address_line1 from street_number + route
								const street = [comp.street_number?.long_name, comp.route?.long_name]
									.filter(Boolean)
									.join(" ");
								const line2 = comp.subpremise?.long_name || "";
								const city =
									comp.locality?.long_name ||
									comp.postal_town?.long_name ||
									comp.administrative_area_level_2?.long_name ||
									"";
								const pincode = comp.postal_code?.long_name || "";
								const country = comp.country?.long_name || "";

								this.dialog.set_value("address_line1", street || "");
								this.dialog.set_value("address_line2", line2 || "");
								this.dialog.set_value("city", city);
								this.dialog.set_value("pincode", pincode);
								if (country) this.dialog.set_value("country", country);
							});
						} catch (err) {
							// ignore autocomplete errors
						}
					};

					// If Google Places already available, wire it up
					const has_places = window.google && google.maps && google.maps.places;
					if (has_places) {
						init_autocomplete();
						return;
					}

					// Else, fetch API key and inject the script dynamically
					frappe.call({
						method: "vt_internal.vt_internal.api.google_maps.get_google_maps_api_key",
					}).then((r) => {
						const msg = r.message || {};
						if (!msg.enabled || !msg.api_key) {
							return; // gracefully do nothing if no key
						}

						// Avoid duplicate injection
						const src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(
							msg.api_key
						)}&libraries=places&language=${encodeURIComponent(frappe.boot?.lang || "fr")}`;
						if (document.querySelector(`script[src='${src}']`)) {
							// script already there, wait a tick and init
							setTimeout(() => {
								if (window.google && google.maps && google.maps.places) init_autocomplete();
							}, 200);
							return;
						}

						const script = document.createElement("script");
						script.src = src;
						script.async = true;
						script.defer = true;
						script.onload = () => init_autocomplete();
						script.onerror = () => {};
						document.head.appendChild(script);
					});
				}
		};

		return true;
	}

	// Try immediately, then poll briefly until form bundle is available
	if (!defineOverride()) {
		const interval = setInterval(() => {
			if (defineOverride()) {
				clearInterval(interval);
			}
		}, 200);
		// Stop polling after ~10s to avoid infinite loops in edge cases
		setTimeout(() => clearInterval(interval), 10000);
	}
})();

