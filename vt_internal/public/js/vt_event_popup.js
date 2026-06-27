// Enrichit le popup calendrier : liens FDT/VT, Google Maps, description

frappe.after_ajax(() => {
	const observer = new MutationObserver((mutations) => {
		for (const mutation of mutations) {
			for (const node of mutation.addedNodes) {
				if (node.nodeType !== 1 || !node.classList?.contains('evp-popover')) continue;
				vt_enhance_event_popup(node);
			}
		}
	});
	observer.observe(document.body, { childList: true });
});

async function vt_enhance_event_popup(popover_el) {
	try {
		const trigger = document.querySelector(`[aria-describedby="${popover_el.id}"]`);
		if (!trigger?.href) return;

		const event_name = decodeURIComponent(new URL(trigger.href).pathname.split('/').pop());
		if (!event_name) return;

		const doc = await frappe.model.with_doc('Event', event_name);
		if (!doc) return;

		const has_fdt = !!doc.custom_fiche_de_travail;
		const has_vt = !!doc.custom_visite_technique;

		if (!has_fdt && !has_vt) return;

		// Le document de référence pour l'adresse et la description (FDT prioritaire)
		const primary_doctype = has_fdt ? 'Fiche de travail' : 'Visite Technique';
		const primary_name = has_fdt ? doc.custom_fiche_de_travail : doc.custom_visite_technique;

		let address_display = null;
		let linked_description = null;

		try {
			const r = await frappe.db.get_value(primary_doctype, primary_name, ['address', 'description']);
			const data = r?.message || {};

			if (data.description) {
				linked_description = data.description;
			}

			if (data.address) {
				const addr_r = await frappe.db.get_value('Address', data.address,
					['address_line1', 'address_line2', 'city', 'pincode']);
				const addr = addr_r?.message || {};
				const parts = [
					addr.address_line1,
					addr.address_line2,
					addr.pincode && addr.city ? `${addr.pincode} ${addr.city}` : (addr.city || addr.pincode),
				].filter(Boolean);
				if (parts.length > 0) {
					address_display = parts.join(', ');
				}
			}
		} catch (_) {}

		const body = popover_el.querySelector('.evp-scroller');
		if (!body) return;

		const section = document.createElement('div');
		section.style.cssText = 'border-top:1px solid var(--border-color);padding-top:10px;margin-top:4px;display:flex;flex-direction:column;gap:6px;';

		// Bouton Google Maps
		if (address_display) {
			const maps_url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address_display)}`;
			const btn = vt_make_popup_btn(`📍 ${address_display}`, maps_url, 'blue');
			btn.target = '_blank';
			btn.rel = 'noopener noreferrer';
			section.appendChild(btn);
		}

		// Lien vers la Fiche de travail
		if (has_fdt) {
			section.appendChild(vt_make_popup_btn(
				`🔧 Fiche : ${doc.custom_fiche_de_travail}`,
				frappe.utils.get_form_link('Fiche de travail', doc.custom_fiche_de_travail),
				'green'
			));
		}

		// Lien vers la Visite Technique
		if (has_vt) {
			section.appendChild(vt_make_popup_btn(
				`🔍 Visite : ${doc.custom_visite_technique}`,
				frappe.utils.get_form_link('Visite Technique', doc.custom_visite_technique),
				'orange'
			));
		}

		// Description issue de la FDT ou VT
		if (linked_description) {
			const stripped = linked_description.replace(/<[^>]+>/g, '').trim();
			if (stripped) {
				const desc_div = document.createElement('div');
				desc_div.style.cssText = [
					'padding: 8px 10px',
					'background: var(--fg-color)',
					'border-radius: var(--border-radius)',
					'font-size: var(--text-sm)',
					'color: var(--text-color)',
					'border: 1px solid var(--border-color)',
					'max-height: 120px',
					'overflow-y: auto',
				].join(';');
				desc_div.innerHTML = linked_description;
				section.appendChild(desc_div);
			}
		}

		body.appendChild(section);
	} catch (_) {
		// Silencieux
	}
}

function vt_make_popup_btn(html, href, color) {
	const a = document.createElement('a');
	a.innerHTML = html;
	a.href = href;
	a.style.cssText = `
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		border-radius: var(--border-radius);
		font-size: var(--text-sm);
		font-weight: 500;
		text-decoration: none;
		background: var(--${color}-100, #eff6ff);
		color: var(--${color}-600, #2563eb);
		border: 1px solid var(--${color}-200, #bfdbfe);
		transition: opacity 0.15s;
	`;
	a.addEventListener('mouseenter', () => a.style.opacity = '0.8');
	a.addEventListener('mouseleave', () => a.style.opacity = '1');
	return a;
}
