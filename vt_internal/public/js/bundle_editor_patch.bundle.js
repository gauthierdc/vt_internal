
// Prevent forcing price in "Ensemble de produit"
// We don't want the bundled item to have a different price compared to the sum ot the bundeled items
//
// Au lieu d'un MutationObserver permanent sur tout le document.body (qui se
// déclenchait à CHAQUE mutation DOM de CHAQUE page Desk et saturait le thread
// principal sur les fiches lourdes), on intercepte l'assignation de
// window.cur_bundle_editor : le patch ne coûte plus rien tant qu'aucun éditeur
// d'ensemble de produit n'est ouvert.
frappe.after_ajax(() => {
  const patch_dialog = (dialog) => {
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
  };

  // Le dialog n'existe pas toujours au moment exact de l'assignation :
  // on tente immédiatement, puis on laisse passer un tick au cas où.
  const try_patch = (editor) => {
    if (!editor) return;
    if (editor.dialog) {
      patch_dialog(editor.dialog);
    } else {
      setTimeout(() => patch_dialog(editor?.dialog), 0);
    }
  };

  let _editor = window.cur_bundle_editor;
  if (_editor) try_patch(_editor); // éditeur déjà ouvert avant ce hook

  Object.defineProperty(window, "cur_bundle_editor", {
    configurable: true,
    get: () => _editor,
    set: (val) => {
      _editor = val;
      try_patch(val);
    },
  });
});
