from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "deploy" / "overlays" / "macmini-lab"


def test_deployment_contract_uses_platform_image_slots() -> None:
    contract = json.loads((ROOT / "deploy" / "contract.json").read_text())

    assert contract["application"] == "video-vault"
    assert contract["platform"] == "linux/arm64"
    assert contract["imageSlots"] == {
        "runtime": "platform-runtime-image",
        "migration": "platform-migration-image",
    }
    assert contract["migration"]["headCommand"] == ["schema-head"]


def test_overlay_keeps_secrets_external_and_network_default_denied() -> None:
    rendered_source = "\n".join(path.read_text() for path in sorted(OVERLAY.glob("*.yaml")))

    assert "kind: Secret" not in rendered_source
    assert "name: video-vault-default-deny" in rendered_source
    assert "ingressClassName: tailscale" in rendered_source
    assert "image: platform-runtime-image" in rendered_source
    assert "image: platform-migration-image" in rendered_source
