"""
Rerun prompting agent.

At the end of a simulation, this agent uses Fireworks to propose an improved
next input (a modified StudySpec) to try to get a better result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from aonp.llm.fireworks_client import FireworksError, chat_completion, extract_text
from aonp.schemas.study import StudySpec


def _try_extract_keff(outputs_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Best-effort extraction of k-effective from an OpenMC statepoint.
    Returns dict like {"keff": float, "uncertainty": float, "statepoint": "statepoint.X.h5"}.
    """
    statepoints = sorted(outputs_dir.glob("statepoint.*.h5"))
    if not statepoints:
        return None

    # Prefer latest by filename sort
    sp_path = statepoints[-1]

    try:
        import openmc  # type: ignore
    except Exception:
        return {"statepoint": sp_path.name, "note": "openmc not available to parse keff"}

    try:
        with openmc.StatePoint(str(sp_path)) as sp:
            # OpenMC returns uncertainties as ufloat-like; keep simple primitives
            keff = getattr(sp, "k_combined", None) or getattr(sp, "keff", None)
            if keff is None:
                return {"statepoint": sp_path.name, "note": "keff not found in statepoint"}
            return {
                "statepoint": sp_path.name,
                "keff": float(getattr(keff, "nominal_value", keff)),
                "uncertainty": float(getattr(keff, "std_dev", 0.0)),
            }
    except Exception as e:
        return {"statepoint": sp_path.name, "note": f"failed to parse keff: {e}"}


def _build_prompt(
    *,
    study_spec: Dict[str, Any],
    manifest: Dict[str, Any],
    results_summary: Optional[Dict[str, Any]],
    objective: str,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    system = {
        "role": "system",
        "content": (
            "You are an expert OpenMC simulation tuning assistant. "
            "Given a prior StudySpec input and run results, propose a new StudySpec "
            "that is likely to improve the objective while remaining valid."
        ),
    }

    user_payload = {
        "objective": objective,
        "run_manifest": manifest,
        "results_summary": results_summary,
        "current_study_spec": study_spec,
        "instructions": (
            "Return STRICT JSON (no markdown) with keys:\n"
            "1) suggested_study_spec: a full StudySpec object\n"
            "2) changes: array of concise strings describing edits\n"
            "3) rationale: short paragraph\n"
            "Constraints:\n"
            "- Keep it valid for the StudySpec schema.\n"
            "- Prefer small, targeted edits.\n"
            "- If results are missing, propose safer settings changes (batches/particles/seed) "
            "or material/temperature adjustments.\n"
        ),
    }

    user = {"role": "user", "content": json.dumps(user_payload, sort_keys=True)}
    return system, user


def generate_rerun_suggestion(
    run_dir: Path,
    *,
    objective: str = "Improve the simulation outcome (e.g., a more reasonable/target k-effective with lower uncertainty) while keeping runtime reasonable.",
    timeout_s: float = 30.0,
) -> Optional[Dict[str, Any]]:
    """
    Generate and persist a rerun suggestion for a completed/failed run.

    Writes (best-effort):
    - suggested_study_spec.json
    - suggested_study_spec.yaml
    - rerun_suggestion.raw.txt (if parsing/validation fails)
    """
    run_dir = Path(run_dir)
    study_path = run_dir / "study_spec.json"
    manifest_path = run_dir / "run_manifest.json"
    outputs_dir = run_dir / "outputs"

    if not study_path.exists() or not manifest_path.exists():
        return None

    study_spec = json.loads(study_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results_summary = _try_extract_keff(outputs_dir)

    system, user = _build_prompt(
        study_spec=study_spec,
        manifest=manifest,
        results_summary=results_summary,
        objective=objective,
    )

    try:
        resp = chat_completion(messages=[system, user], timeout_s=timeout_s)
        text = extract_text(resp).strip()
    except FireworksError:
        # No key / call failed: just skip silently at runtime (runner will print message)
        return None

    # Parse assistant JSON
    suggestion_obj: Optional[Dict[str, Any]] = None
    try:
        suggestion_obj = json.loads(text)
    except Exception:
        # Sometimes the model returns YAML-like or extra text; keep raw for debugging
        (run_dir / "rerun_suggestion.raw.txt").write_text(text, encoding="utf-8")
        return {"raw_text_path": str(run_dir / "rerun_suggestion.raw.txt")}

    suggested_spec = suggestion_obj.get("suggested_study_spec")
    if suggested_spec is None:
        (run_dir / "rerun_suggestion.raw.txt").write_text(text, encoding="utf-8")
        return {"raw_text_path": str(run_dir / "rerun_suggestion.raw.txt")}

    # If model embedded it as a string, try parsing as JSON/YAML
    if isinstance(suggested_spec, str):
        try:
            suggested_spec = json.loads(suggested_spec)
        except Exception:
            suggested_spec = yaml.safe_load(suggested_spec)

    # Validate suggested spec
    try:
        suggested_model = StudySpec(**suggested_spec)
    except Exception as e:
        (run_dir / "rerun_suggestion.raw.txt").write_text(
            text + f"\n\n[VALIDATION_ERROR]\n{e}\n", encoding="utf-8"
        )
        return {"raw_text_path": str(run_dir / "rerun_suggestion.raw.txt")}

    # Persist the validated suggestion
    suggested_json_path = run_dir / "suggested_study_spec.json"
    suggested_yaml_path = run_dir / "suggested_study_spec.yaml"
    suggested_json_path.write_text(
        json.dumps(suggested_model.model_dump(), sort_keys=True, indent=2),
        encoding="utf-8",
    )
    suggested_yaml_path.write_text(
        yaml.safe_dump(suggested_model.model_dump(), sort_keys=False),
        encoding="utf-8",
    )

    result: Dict[str, Any] = {
        "suggested_spec_hash": suggested_model.get_canonical_hash(),
        "suggested_study_spec_json": str(suggested_json_path),
        "suggested_study_spec_yaml": str(suggested_yaml_path),
        "changes": suggestion_obj.get("changes"),
        "rationale": suggestion_obj.get("rationale"),
    }

    return result


