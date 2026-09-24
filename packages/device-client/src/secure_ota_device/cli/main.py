"""Command-line entry point — the thin outermost shell.

Holds no business logic whatsoever: it parses arguments, builds a container,
calls one use case and renders the result. Everything it prints is derived from
objects the application layer returned, which is why the same behaviour is fully
testable without ever spawning a process.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from ..application.use_cases import DeviceSnapshot, UpdateReport
from ..composition import DeviceContainer, Settings
from ..domain import FirmwareVersion

_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secure-ota-device",
        description=(
            "SecureOTA device agent — verifies firmware against an on-chain "
            "release registry before installing it."
        ),
    )
    parser.add_argument("--model", help="device model identifier")
    parser.add_argument("--rpc-url", help="JSON-RPC endpoint")
    parser.add_argument("--contract", help="FirmwareRegistry contract address")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="read releases from the local fixture instead of a chain",
    )
    parser.add_argument("--fixture", type=Path, help="path to the fixture registry")
    parser.add_argument("--state", type=Path, help="path to the device state file")
    parser.add_argument("--slot", type=Path, help="path to the firmware slot directory")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show installed firmware and advertised defences")

    check = sub.add_parser(
        "check", help="verify the available update without installing it"
    )
    check.add_argument("--version", help="pin to a specific version, e.g. 1.2.0")

    update = sub.add_parser("update", help="verify and install the available update")
    update.add_argument("--version", help="pin to a specific version, e.g. 1.2.0")

    return parser


def settings_from_args(args: argparse.Namespace) -> Settings:
    """Layer CLI flags over environment and defaults."""
    settings = Settings.from_environment()
    overrides: dict[str, object] = {}

    if args.model:
        overrides["model"] = args.model
    if args.rpc_url:
        overrides["rpc_url"] = args.rpc_url
    if args.contract:
        overrides["contract_address"] = args.contract
    if args.offline:
        overrides["offline"] = True
    if args.fixture:
        overrides["fixture_path"] = args.fixture
    if args.state:
        overrides["state_path"] = args.state
    if args.slot:
        overrides["slot_path"] = args.slot

    return replace(settings, **overrides)  # type: ignore[arg-type]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    container = DeviceContainer(settings_from_args(args))

    if args.command == "status":
        _render_status(container.inspect_device.execute())
        return 0

    target = FirmwareVersion.from_semver(args.version) if args.version else None
    report = container.update_firmware.execute(
        target_version=target, dry_run=args.command == "check"
    )
    _render_report(report)
    return report.exit_code


# -- rendering -----------------------------------------------------------


def _render_status(snapshot: DeviceSnapshot) -> None:
    print(f"\n{_BOLD}SecureOTA device{_RESET}")
    print(f"  model             {snapshot.model}")
    print(f"  installed         {snapshot.installed_version}")
    print(f"  release registry  {snapshot.registry_source}")

    if snapshot.registry_error:
        print(f"  {_RED}registry error    {snapshot.registry_error}{_RESET}")
    elif snapshot.latest_release is None:
        print("  latest published  (none)")
    else:
        latest = snapshot.latest_release
        flag = f" {_RED}[REVOKED]{_RESET}" if latest.revoked else ""
        print(f"  latest published  {latest.version}{flag}")
        print(f"  expected digest   {latest.firmware_hash.short}")
        if snapshot.update_available:
            print(f"  {_GREEN}update available{_RESET}")

    print(f"\n{_BOLD}Advertised defences{_RESET}")
    for name, defends in snapshot.defences:
        print(f"  {name:<14} {_DIM}{defends}{_RESET}")
    print()


def _render_report(report: UpdateReport) -> None:
    if report.outcome.is_success:
        colour, headline = _GREEN, report.outcome.value
    elif report.is_attack_indicator:
        colour, headline = _RED, f"{report.outcome.value} (attack indicator)"
    else:
        colour, headline = _DIM, report.outcome.value

    print(f"{colour}{_BOLD}  {headline}{_RESET}")
    if report.changed_firmware:
        print(f"  firmware {report.version_before} → {report.version_after}")
    else:
        print(f"  firmware unchanged at {report.version_before}")
    if report.detail:
        print(f"  {_DIM}{report.detail}{_RESET}")
    print()


if __name__ == "__main__":
    sys.exit(main())
