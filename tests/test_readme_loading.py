"""The published loading example must not silently execute a moving revision."""

import os
from pathlib import Path
import re
import sys
from types import ModuleType
import unittest
from unittest import mock


class ReadmeLoadingTests(unittest.TestCase):
    @staticmethod
    def example():
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(
            encoding="utf-8"
        )
        examples = re.findall(r"```python\n(.*?)\n```", readme, re.DOTALL)
        selected = [code for code in examples if "get_kernel" in code]
        if len(selected) != 1:
            raise AssertionError("Expected exactly one kernel-loading example")
        return compile(selected[0], "README.md", "exec")

    def run_example(self, environment):
        module = ModuleType("kernels")
        module.get_kernel = mock.Mock(return_value=object())
        with mock.patch.dict(os.environ, environment, clear=True):
            with mock.patch.dict(sys.modules, {"kernels": module}):
                exec(self.example(), {})
        return module.get_kernel

    def test_missing_revision_refuses_before_loading(self):
        with self.assertRaises(ValueError):
            self.run_example({})

    def test_moving_or_malformed_revision_refuses_before_loading(self):
        for value in ("", "main", "v1", "latest", "a" * 39, "a" * 41, "g" * 40,
                      "a" * 40 + "\n"):
            with self.subTest(revision=value):
                module = ModuleType("kernels")
                module.get_kernel = mock.Mock()
                with mock.patch.dict(os.environ, {"SZL_INVARIANTS_HF_REVISION": value}, clear=True):
                    with mock.patch.dict(sys.modules, {"kernels": module}):
                        with self.assertRaises(ValueError):
                            exec(self.example(), {})
                module.get_kernel.assert_not_called()

    def test_explicit_revision_is_forwarded_without_a_fallback(self):
        # Synthetic ID tests argument flow only, not a real release or provenance.
        revision = "a" * 40
        loader = self.run_example({"SZL_INVARIANTS_HF_REVISION": revision})
        loader.assert_called_once_with(
            "SZLHOLDINGS/szl-invariants",
            revision=revision,
            trust_remote_code=True,
        )


if __name__ == "__main__":
    unittest.main()
