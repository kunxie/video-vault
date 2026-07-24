from __future__ import annotations

from app.cli import main


def test_schema_head_reports_packaged_revision(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["schema-head"]) == 0
    assert capsys.readouterr().out.strip() == "0001_initial"


def test_schema_ancestry_accepts_head_and_rejects_unknown_revision() -> None:
    assert main(["schema-descends-from", "0001_initial"]) == 0
    assert main(["schema-descends-from", "0000_unknown"]) == 1
