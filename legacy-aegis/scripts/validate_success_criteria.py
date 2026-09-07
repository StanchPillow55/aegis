from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {"id", "criterion", "verify", "pass", "artifact"}


def main() -> int:
    path = ROOT / "success_criteria.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert isinstance(data, dict), "success_criteria.yaml root must be a dict"
    assert "criteria" in data, "success_criteria.yaml must contain criteria"
    assert isinstance(data["criteria"], list), "criteria must be a list"

    for index, criterion in enumerate(data["criteria"]):
        assert isinstance(criterion, dict), f"criterion {index} must be a dict"
        missing = REQUIRED_FIELDS - set(criterion)
        assert not missing, f"criterion {criterion.get('id', index)} missing {sorted(missing)}"

    print("success_criteria.yaml OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
