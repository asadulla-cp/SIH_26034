# Re-export all models so `from .models import X` works whether models is a
# file or a package.  The canonical definitions live in app/models.py; this
# package directory shadows that file, so we pull everything through here.

import importlib.util
import os

# Load the sibling models.py file directly to avoid circular shadowing.
_models_file = os.path.join(os.path.dirname(__file__), "..", "models.py")
_spec = importlib.util.spec_from_file_location("app._models_flat", _models_file)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

Inspection = _mod.Inspection
ExtractedField = _mod.ExtractedField
Violation = _mod.Violation
ReviewAction = _mod.ReviewAction
Report = _mod.Report
RuleRecord = _mod.RuleRecord

__all__ = ["Inspection", "ExtractedField", "Violation", "ReviewAction", "Report", "RuleRecord"]
