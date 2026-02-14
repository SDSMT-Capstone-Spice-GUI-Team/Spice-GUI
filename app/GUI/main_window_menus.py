"""Menu bar construction and keybinding management for MainWindow."""

from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QDialog


class MenuBarMixin:
    """Mixin providing menu bar construction and keybinding application."""

    def create_menu_bar(self):
        """Create menu bar with File, Edit, View, Simulation, Analysis, and Settings menus"""
        menubar = self.menuBar()
        if menubar is None:
            return

        # File menu
        file_menu = menubar.addMenu("&File")
        if file_menu is None:
            return

        kb = self.keybindings

        new_action = QAction("&New", self)
        new_action.setShortcut(kb.get("file.new"))
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(kb.get("file.open"))
        open_action.triggered.connect(self._on_load)
        file_menu.addAction(open_action)

        # Open Example submenu
        self.examples_menu = file_menu.addMenu("Open &Example")
        self._populate_examples_menu()

        # Templates
        self.templates_menu = file_menu.addMenu("New from &Template")
        self._populate_templates_menu()

        save_action = QAction("&Save", self)
        save_action.setShortcut(kb.get("file.save"))
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(kb.get("file.save_as"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        save_template_action = QAction("Save as Tem&plate...", self)
        save_template_action.triggered.connect(self._on_save_as_template)
        file_menu.addAction(save_template_action)

        file_menu.addSeparator()

        new_from_template_action = QAction("New from &Template...", self)
        new_from_template_action.setToolTip("Create a new circuit from an assignment template")
        new_from_template_action.triggered.connect(self._on_new_from_template)
        file_menu.addAction(new_from_template_action)

        save_as_template_action = QAction("Save as Temp&late...", self)
        save_as_template_action.setToolTip("Save current circuit as an assignment template with metadata")
        save_as_template_action.triggered.connect(self._on_save_as_template)
        file_menu.addAction(save_as_template_action)

        file_menu.addSeparator()

        import_netlist_action = QAction("&Import SPICE Netlist...", self)
        import_netlist_action.setToolTip("Import a SPICE netlist file (.cir, .spice)")
        import_netlist_action.triggered.connect(self._on_import_netlist)
        file_menu.addAction(import_netlist_action)

        import_asc_action = QAction("Import &LTspice Schematic...", self)
        import_asc_action.setToolTip("Import an LTspice schematic file (.asc)")
        import_asc_action.triggered.connect(self._on_import_asc)
        file_menu.addAction(import_asc_action)

        export_netlist_action = QAction("Export &Netlist...", self)
        export_netlist_action.setShortcut(kb.get("file.export_netlist"))
        export_netlist_action.setToolTip("Export the generated SPICE netlist to a .cir file")
        export_netlist_action.triggered.connect(self.export_netlist)
        file_menu.addAction(export_netlist_action)

        export_img_action = QAction("Export &Image...", self)
        export_img_action.setShortcut(kb.get("file.export_image"))
        export_img_action.triggered.connect(self.export_image)
        file_menu.addAction(export_img_action)

        export_pdf_action = QAction("Export as &PDF...", self)
        export_pdf_action.setShortcut(kb.get("file.export_pdf"))
        export_pdf_action.triggered.connect(self._on_export_pdf)
        file_menu.addAction(export_pdf_action)

        export_latex_action = QAction("Export as &LaTeX...", self)
        export_latex_action.setToolTip("Export circuit as CircuiTikZ LaTeX code (.tex file)")
        export_latex_action.triggered.connect(self.export_circuitikz)
        file_menu.addAction(export_latex_action)

        export_asc_action = QAction("Export as LTspice (.&asc)...", self)
        export_asc_action.setToolTip("Export circuit as LTspice .asc schematic file")
        export_asc_action.triggered.connect(self._on_export_asc)
        file_menu.addAction(export_asc_action)

        generate_report_action = QAction("&Generate Circuit Report (PDF)...", self)
        generate_report_action.setToolTip("Generate a comprehensive PDF report with schematic, netlist, and results")
        generate_report_action.triggered.connect(self._on_generate_report)
        file_menu.addAction(generate_report_action)

        file_menu.addSeparator()

        print_action = QAction("&Print...", self)
        print_action.setShortcut(kb.get("file.print"))
        print_action.triggered.connect(self._on_print)
        file_menu.addAction(print_action)

        print_preview_action = QAction("Print Pre&view...", self)
        print_preview_action.setShortcut(kb.get("file.print_preview"))
        print_preview_action.triggered.connect(self._on_print_preview)
        file_menu.addAction(print_preview_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(kb.get("file.exit"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        if edit_menu is None:
            return

        # Undo/Redo actions
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(kb.get("edit.undo"))
        undo_action.triggered.connect(self._on_undo)
        edit_menu.addAction(undo_action)
        self.undo_action = undo_action  # Store reference to update enabled state

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(kb.get("edit.redo"))
        redo_action.triggered.connect(self._on_redo)
        edit_menu.addAction(redo_action)
        self.redo_action = redo_action  # Store reference to update enabled state

        edit_menu.addSeparator()

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(kb.get("edit.copy"))
        copy_action.triggered.connect(self.copy_selected)
        edit_menu.addAction(copy_action)

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(kb.get("edit.cut"))
        cut_action.triggered.connect(self.cut_selected)
        edit_menu.addAction(cut_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(kb.get("edit.paste"))
        paste_action.triggered.connect(self.paste_components)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(kb.get("edit.delete"))
        delete_action.triggered.connect(self.canvas.delete_selected)
        edit_menu.addAction(delete_action)

        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(kb.get("edit.select_all"))
        select_all_action.triggered.connect(self.canvas.select_all)
        edit_menu.addAction(select_all_action)

        edit_menu.addSeparator()

        copy_latex_action = QAction("Copy as La&TeX", self)
        copy_latex_action.setToolTip("Copy the CircuiTikZ environment block to the clipboard")
        copy_latex_action.triggered.connect(self.copy_circuitikz)
        edit_menu.addAction(copy_latex_action)

        copy_json_action = QAction("Copy Circuit as &JSON", self)
        copy_json_action.setToolTip("Copy entire circuit to system clipboard as JSON")
        copy_json_action.triggered.connect(self.copy_circuit_json)
        edit_menu.addAction(copy_json_action)

        paste_json_action = QAction("Paste Circuit from JS&ON", self)
        paste_json_action.setToolTip("Replace current circuit with JSON from clipboard")
        paste_json_action.triggered.connect(self.paste_circuit_json)
        edit_menu.addAction(paste_json_action)

        edit_menu.addSeparator()

        rotate_cw_action = QAction("Rotate Clockwise", self)
        rotate_cw_action.setShortcut(kb.get("edit.rotate_cw"))
        rotate_cw_action.triggered.connect(lambda: self.canvas.rotate_selected(True))
        edit_menu.addAction(rotate_cw_action)

        rotate_ccw_action = QAction("Rotate Counter-Clockwise", self)
        rotate_ccw_action.setShortcut(kb.get("edit.rotate_ccw"))
        rotate_ccw_action.triggered.connect(lambda: self.canvas.rotate_selected(False))
        edit_menu.addAction(rotate_ccw_action)

        flip_h_action = QAction("Flip Horizontal", self)
        flip_h_action.setShortcut(kb.get("edit.flip_h"))
        flip_h_action.triggered.connect(lambda: self.canvas.flip_selected(True))
        edit_menu.addAction(flip_h_action)

        flip_v_action = QAction("Flip Vertical", self)
        flip_v_action.setShortcut(kb.get("edit.flip_v"))
        flip_v_action.triggered.connect(lambda: self.canvas.flip_selected(False))
        edit_menu.addAction(flip_v_action)

        edit_menu.addSeparator()

        clear_action = QAction("&Clear Canvas", self)
        clear_action.setShortcut(kb.get("edit.clear"))
        clear_action.triggered.connect(self.clear_canvas)
        edit_menu.addAction(clear_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        if view_menu is None:
            return

        self.show_labels_action = QAction("Show Component &Labels", self)
        self.show_labels_action.setCheckable(True)
        self.show_labels_action.setChecked(True)
        self.show_labels_action.triggered.connect(self.toggle_component_labels)
        view_menu.addAction(self.show_labels_action)

        self.show_values_action = QAction("Show Component &Values", self)
        self.show_values_action.setCheckable(True)
        self.show_values_action.setChecked(True)
        self.show_values_action.triggered.connect(self.toggle_component_values)
        view_menu.addAction(self.show_values_action)

        self.show_nodes_action = QAction("Show &Node Labels", self)
        self.show_nodes_action.setCheckable(True)
        self.show_nodes_action.setChecked(True)
        self.show_nodes_action.triggered.connect(self.toggle_node_labels)
        view_menu.addAction(self.show_nodes_action)

        self.show_op_annotations_action = QAction("Show &OP Annotations", self)
        self.show_op_annotations_action.setCheckable(True)
        self.show_op_annotations_action.setChecked(True)
        self.show_op_annotations_action.triggered.connect(self.toggle_op_annotations)
        view_menu.addAction(self.show_op_annotations_action)

        view_menu.addSeparator()

        self.probe_action = QAction("&Probe Tool", self)
        self.probe_action.setCheckable(True)
        self.probe_action.setShortcut(kb.get("tools.probe"))
        self.probe_action.setToolTip("Click nodes or components to see voltage/current values")
        self.probe_action.triggered.connect(self._toggle_probe_mode)
        view_menu.addAction(self.probe_action)

        view_menu.addSeparator()

        self.show_statistics_action = QAction("Circuit &Statistics", self)
        self.show_statistics_action.setCheckable(True)
        self.show_statistics_action.setChecked(False)
        self.show_statistics_action.triggered.connect(self._toggle_statistics_panel)
        view_menu.addAction(self.show_statistics_action)

        view_menu.addSeparator()

        # Theme submenu (dynamic — includes custom themes)
        self.theme_menu = view_menu.addMenu("&Theme")
        self.theme_group = QActionGroup(self)

        self.light_theme_action = QAction("&Light", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.setChecked(True)
        self.light_theme_action.triggered.connect(lambda: self._set_theme_by_key("light"))
        self.theme_menu.addAction(self.light_theme_action)
        self.theme_group.addAction(self.light_theme_action)

        self.dark_theme_action = QAction("&Dark", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.triggered.connect(lambda: self._set_theme_by_key("dark"))
        self.theme_menu.addAction(self.dark_theme_action)
        self.theme_group.addAction(self.dark_theme_action)

        self._custom_theme_actions = []
        self._refresh_theme_menu()

        # Symbol Style submenu
        symbol_style_menu = view_menu.addMenu("&Symbol Style")
        self.ieee_style_action = QAction("&IEEE / ANSI (American)", self)
        self.ieee_style_action.setCheckable(True)
        self.ieee_style_action.setChecked(True)
        self.ieee_style_action.triggered.connect(lambda: self._set_symbol_style("ieee"))
        symbol_style_menu.addAction(self.ieee_style_action)

        self.iec_style_action = QAction("I&EC (European)", self)
        self.iec_style_action.setCheckable(True)
        self.iec_style_action.triggered.connect(lambda: self._set_symbol_style("iec"))
        symbol_style_menu.addAction(self.iec_style_action)

        self.symbol_style_group = QActionGroup(self)
        self.symbol_style_group.addAction(self.ieee_style_action)
        self.symbol_style_group.addAction(self.iec_style_action)

        # Component Colors submenu
        color_mode_menu = view_menu.addMenu("Component &Colors")
        self.color_mode_action = QAction("&Color (per component type)", self)
        self.color_mode_action.setCheckable(True)
        self.color_mode_action.setChecked(True)
        self.color_mode_action.triggered.connect(lambda: self._set_color_mode("color"))
        color_mode_menu.addAction(self.color_mode_action)

        self.monochrome_mode_action = QAction("&Monochrome", self)
        self.monochrome_mode_action.setCheckable(True)
        self.monochrome_mode_action.triggered.connect(lambda: self._set_color_mode("monochrome"))
        color_mode_menu.addAction(self.monochrome_mode_action)

        self.color_mode_group = QActionGroup(self)
        self.color_mode_group.addAction(self.color_mode_action)
        self.color_mode_group.addAction(self.monochrome_mode_action)

        view_menu.addSeparator()

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(kb.get("view.zoom_in"))
        zoom_in_action.triggered.connect(lambda: self.canvas.zoom_in())
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(kb.get("view.zoom_out"))
        zoom_out_action.triggered.connect(lambda: self.canvas.zoom_out())
        view_menu.addAction(zoom_out_action)

        zoom_fit_action = QAction("&Fit to Circuit", self)
        zoom_fit_action.setShortcut(kb.get("view.zoom_fit"))
        zoom_fit_action.triggered.connect(lambda: self.canvas.zoom_fit())
        view_menu.addAction(zoom_fit_action)

        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut(kb.get("view.zoom_reset"))
        zoom_reset_action.triggered.connect(lambda: self.canvas.zoom_reset())
        view_menu.addAction(zoom_reset_action)

        # Simulation menu
        sim_menu = menubar.addMenu("&Simulation")
        if sim_menu is None:
            return

        netlist_action = QAction("Generate &Netlist", self)
        netlist_action.setShortcut(kb.get("sim.netlist"))
        netlist_action.triggered.connect(self.generate_netlist)
        sim_menu.addAction(netlist_action)

        run_action = QAction("&Run Simulation", self)
        run_action.setShortcut(kb.get("sim.run"))
        run_action.triggered.connect(self.run_simulation)
        sim_menu.addAction(run_action)

        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")
        if analysis_menu is None:
            return

        op_action = QAction("&DC Operating Point (.op)", self)
        op_action.setCheckable(True)
        op_action.setChecked(True)
        op_action.triggered.connect(self.set_analysis_op)
        analysis_menu.addAction(op_action)

        dc_action = QAction("&DC Sweep", self)
        dc_action.setCheckable(True)
        dc_action.triggered.connect(self.set_analysis_dc)
        analysis_menu.addAction(dc_action)

        ac_action = QAction("&AC Sweep", self)
        ac_action.setCheckable(True)
        ac_action.triggered.connect(self.set_analysis_ac)
        analysis_menu.addAction(ac_action)

        tran_action = QAction("&Transient", self)
        tran_action.setCheckable(True)
        tran_action.triggered.connect(self.set_analysis_transient)
        analysis_menu.addAction(tran_action)

        temp_action = QAction("Te&mperature Sweep", self)
        temp_action.setCheckable(True)
        temp_action.triggered.connect(self.set_analysis_temp_sweep)
        analysis_menu.addAction(temp_action)

        analysis_menu.addSeparator()

        sweep_action = QAction("&Parameter Sweep...", self)
        sweep_action.setCheckable(True)
        sweep_action.setToolTip(
            "Sweep a component parameter across a range of values and overlay results from each step"
        )
        sweep_action.triggered.connect(self.set_analysis_parameter_sweep)
        analysis_menu.addAction(sweep_action)

        noise_action = QAction("&Noise...", self)
        noise_action.setCheckable(True)
        noise_action.setToolTip("Noise spectral density analysis (.noise)")
        noise_action.triggered.connect(self.set_analysis_noise)
        analysis_menu.addAction(noise_action)

        analysis_menu.addSeparator()

        mc_action = QAction("&Monte Carlo...", self)
        mc_action.setCheckable(True)
        mc_action.setToolTip("Run Monte Carlo tolerance analysis with randomized component values")
        mc_action.triggered.connect(self.set_analysis_monte_carlo)
        analysis_menu.addAction(mc_action)

        # Create action group for mutually exclusive analysis types
        self.analysis_group = QActionGroup(self)
        self.analysis_group.addAction(op_action)
        self.analysis_group.addAction(dc_action)
        self.analysis_group.addAction(ac_action)
        self.analysis_group.addAction(tran_action)
        self.analysis_group.addAction(temp_action)
        self.analysis_group.addAction(noise_action)
        self.analysis_group.addAction(sweep_action)
        self.analysis_group.addAction(mc_action)

        self.op_action = op_action
        self.dc_action = dc_action
        self.ac_action = ac_action
        self.tran_action = tran_action
        self.temp_action = temp_action
        self.noise_action = noise_action
        self.sweep_action = sweep_action

        # Store action references for keybinding re-application
        self._bound_actions = {
            "file.new": new_action,
            "file.open": open_action,
            "file.save": save_action,
            "file.save_as": save_as_action,
            "file.export_image": export_img_action,
            "file.print": print_action,
            "file.print_preview": print_preview_action,
            "file.export_pdf": export_pdf_action,
            "file.export_netlist": export_netlist_action,
            "file.exit": exit_action,
            "edit.undo": undo_action,
            "edit.redo": redo_action,
            "edit.copy": copy_action,
            "edit.cut": cut_action,
            "edit.paste": paste_action,
            "edit.delete": delete_action,
            "edit.select_all": select_all_action,
            "edit.rotate_cw": rotate_cw_action,
            "edit.rotate_ccw": rotate_ccw_action,
            "edit.flip_h": flip_h_action,
            "edit.flip_v": flip_v_action,
            "edit.clear": clear_action,
            "view.zoom_in": zoom_in_action,
            "view.zoom_out": zoom_out_action,
            "view.zoom_fit": zoom_fit_action,
            "view.zoom_reset": zoom_reset_action,
            "sim.netlist": netlist_action,
            "sim.run": run_action,
            "tools.probe": self.probe_action,
        }

        # Instructor menu
        instructor_menu = menubar.addMenu("&Instructor")
        if instructor_menu:
            create_rubric_action = QAction("&Create Rubric...", self)
            create_rubric_action.setToolTip("Open the rubric editor to create or edit a grading rubric")
            create_rubric_action.triggered.connect(self._on_create_rubric)
            instructor_menu.addAction(create_rubric_action)

            generate_rubric_action = QAction("&Generate Rubric from Circuit...", self)
            generate_rubric_action.setToolTip(
                "Auto-generate a rubric from the current circuit and open it in the editor"
            )
            generate_rubric_action.triggered.connect(self._on_generate_rubric)
            instructor_menu.addAction(generate_rubric_action)

            instructor_menu.addSeparator()

            grade_action = QAction("&Grade Student Circuit...", self)
            grade_action.setToolTip("Open the grading panel to grade a student submission")
            grade_action.triggered.connect(self._toggle_grading_panel)
            instructor_menu.addAction(grade_action)

            batch_grade_action = QAction("&Batch Grade...", self)
            batch_grade_action.setToolTip("Grade a folder of student submissions")
            batch_grade_action.triggered.connect(self._on_batch_grade)
            instructor_menu.addAction(batch_grade_action)

        # Settings menu
        settings_menu = menubar.addMenu("Se&ttings")
        if settings_menu:
            preferences_action = QAction("&Preferences...", self)
            preferences_action.triggered.connect(self._open_preferences_dialog)
            settings_menu.addAction(preferences_action)

            settings_menu.addSeparator()

            keybindings_action = QAction("&Keybindings...", self)
            keybindings_action.triggered.connect(self._open_keybindings_dialog)
            settings_menu.addAction(keybindings_action)

    def _open_preferences_dialog(self):
        """Open the unified preferences dialog (single-instance, non-modal)."""
        from .preferences_dialog import PreferencesDialog

        existing = getattr(self, "_preferences_dialog", None)
        if existing is not None and existing.isVisible():
            existing.raise_()
            existing.activateWindow()
            return
        self._preferences_dialog = PreferencesDialog(self)
        self._preferences_dialog.show()

    def _open_keybindings_dialog(self):
        """Open the keybindings preferences dialog."""
        from .keybindings_dialog import KeybindingsDialog

        dialog = KeybindingsDialog(self.keybindings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Re-apply shortcuts to all menu actions
            self._apply_keybindings()

    def _apply_keybindings(self):
        """Re-apply shortcuts from the registry to stored actions."""
        kb = self.keybindings
        for action_name, qaction in self._bound_actions.items():
            qaction.setShortcut(kb.get(action_name))

    def _refresh_theme_menu(self):
        """Rebuild custom theme entries in the Theme submenu."""
        from .styles import theme_manager

        # Remove old custom actions
        for action in self._custom_theme_actions:
            self.theme_menu.removeAction(action)
            self.theme_group.removeAction(action)
        self._custom_theme_actions.clear()

        # Add custom themes after a separator
        available = theme_manager.get_available_themes()
        custom_themes = [(name, key) for name, key in available if key.startswith("custom:")]
        if custom_themes:
            sep = self.theme_menu.addSeparator()
            self._custom_theme_actions.append(sep)
            for display_name, key in custom_themes:
                action = QAction(display_name, self)
                action.setCheckable(True)
                action.triggered.connect(lambda checked, k=key: self._set_theme_by_key(k))
                self.theme_menu.addAction(action)
                self.theme_group.addAction(action)
                self._custom_theme_actions.append(action)

        # Sync checkmarks with current theme
        current_key = theme_manager.get_theme_key()
        if current_key == "light":
            self.light_theme_action.setChecked(True)
        elif current_key == "dark":
            self.dark_theme_action.setChecked(True)
        else:
            for action in self._custom_theme_actions:
                if hasattr(action, "text") and action.text():
                    # Find matching custom action
                    for name, key in custom_themes:
                        if key == current_key and action.text() == name:
                            action.setChecked(True)
                            break

    def _set_theme_by_key(self, key):
        """Switch theme by key and apply it."""
        from .styles import theme_manager

        theme_manager.set_theme_by_key(key)
        self._apply_theme()
        self._refresh_theme_menu()
