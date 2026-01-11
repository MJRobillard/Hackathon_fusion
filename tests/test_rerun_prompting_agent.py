import json
from pathlib import Path

import pytest

import sys

# Add project root to path (mirrors other tests)
sys.path.insert(0, str(Path(__file__).parent.parent))

from aonp.agents.rerun_prompting_agent import generate_rerun_suggestion


class _FakeHTTPResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_generate_rerun_suggestion_writes_valid_spec(tmp_path: Path, monkeypatch):
    run_dir = tmp_path / "runs" / "run_test"
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True)

    # Minimal valid StudySpec
    study = {
        "name": "test_study",
        "description": "Test",
        "materials": {
            "fuel": {
                "density": 10.4,
                "density_units": "g/cm3",
                "temperature": 900.0,
                "nuclides": [
                    {"name": "U235", "fraction": 0.7, "fraction_type": "ao"},
                    {"name": "O16", "fraction": 0.3, "fraction_type": "ao"},
                ],
            }
        },
        "geometry": {"type": "script", "script": "test_geometry.py"},
        "settings": {"batches": 100, "inactive": 20, "particles": 1000, "seed": 42},
        "nuclear_data": {"library": "endfb71", "path": "/data"},
    }

    (run_dir / "study_spec.json").write_text(json.dumps(study), encoding="utf-8")
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": "run_test", "spec_hash": "abc", "status": "completed"}),
        encoding="utf-8",
    )

    # Fake Fireworks response returning a valid StudySpec (small tweak: seed)
    assistant_obj = {
        "suggested_study_spec": {**study, "settings": {**study["settings"], "seed": 43}},
        "changes": ["Change settings.seed from 42 to 43 to explore a different random stream."],
        "rationale": "Small exploration change.",
    }
    fake_fw = {"choices": [{"message": {"content": json.dumps(assistant_obj)}}]}

    monkeypatch.setenv("FIREWORKS", "fake-key")

    import aonp.llm.fireworks_client as fw

    def _fake_urlopen(req, timeout=None):
        return _FakeHTTPResponse(json.dumps(fake_fw))

    monkeypatch.setattr(fw.urllib.request, "urlopen", _fake_urlopen)

    suggestion = generate_rerun_suggestion(run_dir)
    assert suggestion is not None
    assert (run_dir / "suggested_study_spec.json").exists()
    assert (run_dir / "suggested_study_spec.yaml").exists()
    assert "suggested_spec_hash" in suggestion


