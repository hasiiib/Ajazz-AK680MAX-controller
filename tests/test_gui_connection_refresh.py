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

    def test_connection_timer_is_periodic_and_starts_after_initial_scan(self):
        self.assertIn("self.connection_timer.setInterval(1500)", self.source)
        self.assertIn(
            "self.connection_timer.timeout.connect(self.refresh_connection_status)",
            self.source,
        )
        self.assertIn("self.scan()\n        self.connection_timer.start()", self.source)


if __name__ == "__main__":
    unittest.main()
