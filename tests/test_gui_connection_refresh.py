import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_SOURCE = ROOT / "app" / "main.py"


class GuiConnectionRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = MAIN_SOURCE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_inventory_formatter_accepts_pre_enumerated_inventory(self):
        function = next(
            node for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_hid_inventory_text"
        )
        argument_names = [arg.arg for arg in function.args.args]
        self.assertEqual(argument_names, ["inventory", "inventory_error"])
        self.assertEqual(len(function.args.defaults), 2)

    def test_inventory_report_uses_real_newlines_not_literal_escape_text(self):
        start = self.source.index("def _hid_inventory_text")
        end = self.source.index("\n\n\ndef collect", start)
        formatter = self.source[start:end]
        self.assertNotIn("\\\\n", formatter)

    def test_scan_reuses_the_inventory_instead_of_enumerating_twice(self):
        self.assertIn(
            "self.log.setPlainText(collect(inventory, inventory_error))",
            self.source,
        )

    def test_background_refresh_is_metadata_only(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        refresh = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "refresh_connection_status"
        )
        called_names = {
            node.func.id
            for node in ast.walk(refresh)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertEqual(called_names, {"inspect_keyboard_interfaces", "evaluate_connection"})
        self.assertNotIn("identify_keyboard_details", called_names)

    def test_disconnect_refresh_aborts_stream_when_analog_pair_disappears(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        refresh = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "refresh_connection_status"
        )
        source = ast.get_source_segment(self.source, refresh)
        self.assertIn("state.analog_pair_candidate", source)
        self.assertIn("self._abort_analog_stream(", source)
        self.assertIn("except IdentifyError", source)

    def test_abort_cleanup_stops_timers_clears_samples_and_restores_controls(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        abort = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_abort_analog_stream"
        )
        source = ast.get_source_segment(self.source, abort)
        self.assertNotIn("\\\\n", source)
        for required in (
            "self.stream_timer.stop()",
            "self.stream_session.stop()",
            "self.latest_samples.clear()",
            'self.stream_button.setText("Start Analog Monitor")',
            "self.identify_button.setEnabled(True)",
        ):
            self.assertIn(required, source)

    def test_analog_warning_reports_bounded_evidence_and_remaining_limits(self):
        self.assertIn("self.analog_warning = QLabel(", self.source)
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        initializer = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        warning_assignment = next(
            node for node in initializer.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute)
                and target.attr == "analog_warning"
                for target in node.targets
            )
        )
        warning_call = warning_assignment.value
        self.assertIsInstance(warning_call, ast.Call)
        self.assertIsInstance(warning_call.args[0], ast.Constant)
        warning = warning_call.args[0].value
        self.assertIn(
            "SUSTAINED ANALOG MONITORING IS NOT VERIFIED ON PHYSICAL BOARD 2255",
            warning,
        )
        self.assertIn("16 valid Report ID 5 samples", warning)
        self.assertIn("sent the stop request", warning)
        self.assertIn("stop effectiveness", warning)
        self.assertIn("disconnect recovery", warning)
        self.assertIn("values are raw counts", warning.lower())
        self.assertIn("physical unit and calibrated range", warning)
        self.assertIn("No persistent setting-write opcode is used", warning)
        self.assertIn("layout.addWidget(self.analog_warning)", self.source)

    def test_analog_display_reports_observed_samples_not_unverified_active_state(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        poll = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "poll_analog_stream"
        )
        source = ast.get_source_segment(self.source, poll)
        self.assertIn("self.analog_samples_received += len(samples)", source)
        self.assertIn("slots observed:", source)
        self.assertIn("latest slot:raw counts", source)
        self.assertNotIn("active slots:", source)
        self.assertNotIn("no keys currently moving/held", source)

    def test_analog_status_exposes_sample_freshness_without_expiring_values(self):
        self.assertIn("from time import monotonic", self.source)
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        poll = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "poll_analog_stream"
        )
        source = ast.get_source_segment(self.source, poll)
        self.assertIn("if samples:", source)
        self.assertIn("self.last_analog_sample_at = monotonic()", source)
        self.assertIn("last sample {age_ms} ms ago", source)
        self.assertIn("waiting for first sample", source)
        self.assertNotIn("latest_samples.pop", source)
        self.assertNotIn("latest_samples.clear", source)

    def test_window_close_stops_both_background_timers(self):
        self.assertIn("self.connection_timer.stop()", self.source)
        self.assertIn("self.stream_timer.stop()", self.source)

    def test_connection_timer_is_periodic_and_starts_after_initial_scan(self):
        self.assertIn("self.connection_timer.setInterval(1500)", self.source)
        self.assertIn("self.stream_timer.setInterval(33)", self.source)
        self.assertIn("self.stream_session.poll(max_reports=16)", self.source)
        self.assertIn(
            "self.connection_timer.timeout.connect(self.refresh_connection_status)",
            self.source,
        )
        self.assertIn("self.scan()\n        self.connection_timer.start()", self.source)


    def test_input_error_callback_aborts_session_and_resets_status(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        poll = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "poll_analog_stream"
        )
        source = ast.get_source_segment(self.source, poll)
        self.assertIn("except AnalogStreamError", source)
        self.assertIn("self._abort_analog_stream(", source)
        self.assertIn("self.analog_status.setText(", source)

    def test_abort_path_is_idempotent_after_session_self_cleanup(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        abort = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "_abort_analog_stream"
        )
        source = ast.get_source_segment(self.source, abort)
        self.assertIn("self.stream_session.stop()", source)
        self.assertIn("finally:", source)
        self.assertIn("self.latest_samples.clear()", source)
        session_source_path = ROOT / "app" / "analog_stream.py"
        session_source = session_source_path.read_text(encoding="utf-8")
        self.assertIn("if self._control is not None and self._active:", session_source)
        self.assertIn("self._close_handles()", session_source)

    def test_window_close_best_effort_stops_session(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        close = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "closeEvent"
        )
        source = ast.get_source_segment(self.source, close)
        self.assertIn("self.stream_session.stop()", source)
        self.assertIn("except Exception:", source)
        self.assertIn("super().closeEvent(event)", source)


    def test_manual_stop_clears_stale_samples_and_restores_controls(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        completion = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_on_analog_stop_finished"
        )
        source = ast.get_source_segment(self.source, completion)
        self.assertIn("self.latest_samples.clear()", source)
        self.assertIn('self.stream_button.setText("Start Analog Monitor")', source)
        self.assertIn("self.stream_button.setEnabled(True)", source)
        self.assertIn("self.identify_button.setEnabled(True)", source)
        self.assertIn("if error is None:", source)


    def test_manual_stop_runs_hid_stop_off_gui_thread(self):
        main_class = next(
            node for node in self.tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Main"
        )
        stop = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "stop_analog_stream"
        )
        source = ast.get_source_segment(self.source, stop)
        self.assertIn("self.stream_timer.stop()", source)
        self.assertIn("Thread(", source)
        self.assertIn("target=self._stop_analog_stream_worker", source)
        self.assertNotIn("self.stream_session.stop()", source)

        worker = next(
            node for node in main_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_stop_analog_stream_worker"
        )
        worker_source = ast.get_source_segment(self.source, worker)
        self.assertIn("self.stream_session.stop()", worker_source)
        self.assertIn("self.stream_stop_notifier.finished.emit(error)", worker_source)

    def test_stop_completion_updates_qt_controls_via_signal_handler(self):
        self.assertIn("finished = Signal(object)", self.source)
        self.assertIn(
            "self.stream_stop_notifier.finished.connect(self._on_analog_stop_finished)",
            self.source,
        )
        self.assertIn("self.stream_button.setEnabled(True)", self.source)


if __name__ == "__main__":
    unittest.main()
