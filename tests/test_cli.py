import unittest
from cli.main import main

class TestCLI(unittest.TestCase):
    def test_cli_import(self):
        # Basic import test
        from cli.main import main
        self.assertIsNotNone(main)

if __name__ == "__main__":
    unittest.main()
