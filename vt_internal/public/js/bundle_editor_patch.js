
// Prevent forcing price in "Ensemble de produit"
// We don't want the bundled item to have a different price compared to the sum ot the bundeled items
frappe.after_ajax(() => {
  const observer = new MutationObserver(() => {
    const editor = window.cur_bundle_editor;
    const dialog = editor?.dialog;

    if (!dialog || dialog.__bundle_patch_applied) return;

    if (dialog.fields_dict?.bundle_editor_force_custom_price) {
      dialog.fields_dict.bundle_editor_force_custom_price.$wrapper.hide();
      dialog.set_value("bundle_editor_force_custom_price", 0);
      Object.defineProperty(dialog.fields_dict.bundle_editor_force_custom_price, 'value', {
        get: () => 0,
        set: () => {},
      });
    }

    ["rate", "base_unit_cost_price", "markup_percentage"].forEach(fieldname => {
      if (dialog.has_field(fieldname)) {
        dialog.set_df_property(fieldname, "read_only", 1);
        dialog.set_df_property(fieldname, "description", "");
      }
    });

    dialog.__bundle_patch_applied = true;
    console.log("✅ Patch cur_bundle_editor appliqué automatiquement");
  });

  observer.observe(document.body, { childList: true, subtree: true });
});
