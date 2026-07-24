from __future__ import annotations

import argparse
import os
import re
from collections.abc import Callable

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.db import get_engine
from app.storage import get_storage

_REVISION_ID = re.compile(r"[0-9A-Za-z][0-9A-Za-z_.-]{0,31}")


def _alembic_config() -> Config:
    return Config("alembic.ini")


def _packaged_head() -> tuple[ScriptDirectory, str]:
    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError("the packaged migration graph must have exactly one head")
    return script, heads[0]


def _serve(_args: argparse.Namespace) -> int:
    os.execvp(
        "uvicorn",
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    )


def _migrate(_args: argparse.Namespace) -> int:
    command.upgrade(_alembic_config(), "head")
    return 0


def _schema_head(_args: argparse.Namespace) -> int:
    _, head = _packaged_head()
    print(head)
    return 0


def _schema_descends_from(args: argparse.Namespace) -> int:
    revision = str(args.revision)
    if _REVISION_ID.fullmatch(revision) is None:
        raise ValueError("the requested schema revision is invalid")
    script, head = _packaged_head()
    revisions = script.walk_revisions(base="base", head=head)
    return 0 if any(item.revision == revision for item in revisions) else 1


def _verify_services(_args: argparse.Namespace) -> int:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    get_storage().check_bucket()
    print("service verification succeeded (PostgreSQL and object storage; no writes)")
    return 0


def _parser() -> argparse.ArgumentParser:
    version = os.environ.get("VIDEO_VAULT_VERSION", "0.0.0")
    revision = os.environ.get("VIDEO_VAULT_BUILD_REVISION", "uncommitted")
    parser = argparse.ArgumentParser(prog="video-vault")
    parser.add_argument(
        "--version",
        action="version",
        version=f"video-vault {version} (revision {revision})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("serve").set_defaults(handler=_serve)
    subparsers.add_parser("migrate").set_defaults(handler=_migrate)
    subparsers.add_parser("schema-head").set_defaults(handler=_schema_head)
    ancestry = subparsers.add_parser("schema-descends-from")
    ancestry.add_argument("revision")
    ancestry.set_defaults(handler=_schema_descends_from)
    subparsers.add_parser("verify-services").set_defaults(handler=_verify_services)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
