import argparse
import asyncio
import time
import typing as t

from colorama import Fore, init as colorama_init
from tonutils.clients import AdnlClient

from .__meta__ import __version__
from .metrics import probe_all_clients
from .status import print_status
from .utils import color, create_balancer, format_elapsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tonutils-adnlctl",
        description="Inspect ADNL clients (lite-servers) using tonutils.",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Show lite-server status")

    status.add_argument(
        "-n",
        "--network",
        type=str,
        choices=["mainnet", "testnet"],
        required=True,
        help="Network name.",
    )
    status.add_argument(
        "-c",
        "--config",
        type=str,
        help="Config path or HTTPS URL (JSON).",
    )
    status.add_argument(
        "--exact",
        action="store_true",
        help="Use precise archive depth check (slower).",
    )

    return parser


async def cmd_status(args: argparse.Namespace) -> int:
    print(
        color(
            "Command status running, this may take some time...",
            fg=Fore.YELLOW,
            bright=True,
        )
    )

    balancer = await create_balancer(args.network, args.config)
    clients: t.Sequence[AdnlClient] = balancer.clients

    if not clients:
        print("No clients configured.")
        return 1

    start = time.perf_counter()
    results = await probe_all_clients(clients, use_exact=args.exact)
    elapsed = time.perf_counter() - start

    print_status(results)
    print(
        color(
            f"Command status completed in {format_elapsed(elapsed)}",
            fg=Fore.GREEN,
            bright=True,
        )
    )

    return 0


async def _amain() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        return await cmd_status(args)

    raise RuntimeError(f"Unknown command: {args.command!r}")


def main() -> None:
    colorama_init()
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        print()
        print(color("Interrupted by user", fg=Fore.RED, bright=True))
