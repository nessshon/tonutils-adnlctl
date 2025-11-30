import json
import os
import typing as t

import aiohttp
from colorama import Fore, Style
from tonutils.clients import AdnlBalancer
from tonutils.types import NetworkGlobalID


def format_elapsed(seconds: float) -> str:
    if seconds < 1:
        ms = int(seconds * 1000)
        return f"{ms}ms"

    total = int(seconds)
    h = total // 3600
    total %= 3600
    m = total // 60
    s = total % 60

    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def color(text: str, fg: t.Optional[str] = None, bright: bool = False) -> str:
    parts: list[str] = []
    if bright:
        parts.append(Style.BRIGHT)
    if fg is not None:
        parts.append(fg)
    parts.append(str(text))
    parts.append(Style.RESET_ALL)
    return "".join(parts)


def print_table(
    headers: t.Sequence[str],
    rows: t.Iterable[t.Sequence[str]],
    row_styles: t.Optional[t.Sequence[t.Optional[t.Tuple[str, bool]]]] = None,
) -> None:
    plain_rows: t.List[t.List[str]] = [[str(c) for c in row] for row in rows]
    columns = len(headers)
    widths = [len(h) for h in headers]

    for row in plain_rows:
        if len(row) != columns:
            raise ValueError("Row length does not match headers length")
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def _fmt(_line: t.Sequence[str]) -> str:
        parts = [str(val).ljust(widths[_i]) for _i, val in enumerate(_line)]
        return "  ".join(parts)

    header_line = _fmt(headers)
    print(color(header_line, fg=Fore.BLUE, bright=True))

    for idx, row in enumerate(plain_rows):
        line = _fmt(row)
        style = row_styles[idx] if row_styles and idx < len(row_styles) else None
        if style is not None:
            fg, bright = style
            line = color(line, fg=fg, bright=bright)
        print(line)


def parse_network(name: str) -> NetworkGlobalID:
    name = name.lower()
    if name == "mainnet":
        return NetworkGlobalID.MAINNET
    if name == "testnet":
        return NetworkGlobalID.TESTNET
    raise ValueError(f"Unsupported network: {name!r}")


async def load_config(path_or_url: str) -> t.Dict[str, t.Any]:
    if path_or_url.startswith(("http://", "https://")):
        async with aiohttp.ClientSession() as session:
            async with session.get(path_or_url, timeout=10) as resp:
                resp.raise_for_status()
                text = await resp.text()
    else:
        if not os.path.exists(path_or_url):
            raise FileNotFoundError(f"Config not found: {path_or_url}")
        with open(path_or_url, "r", encoding="utf-8") as f:
            text = f.read()

    return json.loads(text)


async def create_balancer(
    network_name: str,
    config: t.Optional[str] = None,
) -> AdnlBalancer:
    network = parse_network(network_name)

    if config:
        config_data = await load_config(config)
        return AdnlBalancer.from_config(
            timeout=1,
            network=network,
            config=config_data,
        )

    return await AdnlBalancer.from_network_config(network=network)
