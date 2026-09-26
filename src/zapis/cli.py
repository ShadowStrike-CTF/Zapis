# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
"""Zapis CLI — `zapis` launches the web UI, `zapis create` exports a writeup."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from zapis.core.export import FORMATS, export, filename_for
from zapis.core.schema import CATEGORIES, WriteupSchema


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zapis", description="CTF writeup templating and export tool. by ShadowStrike."
    )
    sub = parser.add_subparsers(dest="command")
    create = sub.add_parser("create", help="export a writeup to md, html or pdf")
    create.add_argument("--challenge-name", required=True)
    create.add_argument("--ctf-name", required=True)
    create.add_argument("--category", required=True, choices=CATEGORIES)
    create.add_argument("--difficulty", required=True, type=int, choices=(1, 2, 3))
    create.add_argument("--tool", action="append", default=[], dest="tools_used",
                        help="tool used (repeatable)")
    create.add_argument("--approach", required=True)
    create.add_argument("--flag", required=True)
    create.add_argument("--notes", default="")
    create.add_argument("--author", default="ShadowStrike")
    create.add_argument("--date", help="ISO date (default: today)")
    create.add_argument("--format", default="md", choices=FORMATS, dest="fmt")
    create.add_argument("-o", "--output", type=Path,
                        help="output path (default: ./<challenge-slug>.<format>)")
    return parser


def _create(args: argparse.Namespace) -> int:
    fields = dict(
        challenge_name=args.challenge_name,
        ctf_name=args.ctf_name,
        category=args.category,
        difficulty=args.difficulty,
        tools_used=args.tools_used,
        approach=args.approach,
        flag=args.flag,
        notes=args.notes,
        author=args.author,
    )
    if args.date:
        fields["date"] = args.date
    try:
        schema = WriteupSchema(**fields)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out = args.output or Path(filename_for(schema, args.fmt))
    out.write_bytes(export(schema, args.fmt))
    print(out)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "create":
        return _create(args)
    from zapis.main import main as launch
    launch()
    return 0


if __name__ == "__main__":
    sys.exit(main())
