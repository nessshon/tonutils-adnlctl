import typing as t
from dataclasses import dataclass, field

from colorama import Fore

from .utils import color, print_table


@dataclass
class ProviderStatus:
    index: int
    host: str
    port: int

    connect_ms: t.Optional[int] = None
    request_ms: t.Optional[int] = None
    ping_ms: t.Optional[float] = None
    version: t.Optional[str] = None

    time_value: t.Optional[int] = None
    time_label: t.Optional[str] = None

    last_block_seqno_raw: t.Optional[int] = None
    last_block_seqno_label: t.Optional[str] = None
    shards: t.Dict[str, int] = field(default_factory=dict)

    archive_depth_label: t.Optional[str] = None

    mc_lag: bool = False
    shard_lag: bool = False
    time_lag: bool = False
    archive_unknown: bool = False


def annotate_seqno_lags(statuses: t.List[ProviderStatus]) -> None:
    max_last_block_seqno = 0
    for s in statuses:
        if isinstance(s.last_block_seqno_raw, int):
            max_last_block_seqno = max(max_last_block_seqno, s.last_block_seqno_raw)

    max_shards: t.Dict[str, int] = {}
    for s in statuses:
        for shard_id, shard_seqno in s.shards.items():
            if isinstance(shard_seqno, int):
                max_shards[shard_id] = max(max_shards.get(shard_id, 0), shard_seqno)

    for s in statuses:
        if not isinstance(s.last_block_seqno_raw, int):
            continue

        label = str(s.last_block_seqno_raw)

        if s.last_block_seqno_raw < max_last_block_seqno:
            s.mc_lag = True
            label += " (!)"
        else:
            for shard_id, shard_seqno in s.shards.items():
                max_shard_seqno = max_shards.get(shard_id)
                if (
                    isinstance(shard_seqno, int)
                    and isinstance(max_shard_seqno, int)
                    and shard_seqno < max_shard_seqno
                ):
                    s.shard_lag = True
                    label += " (!!)"
                    break

        s.last_block_seqno_label = label


def annotate_time_lags(statuses: t.List[ProviderStatus]) -> None:
    max_time = 0
    for s in statuses:
        if isinstance(s.time_value, int):
            max_time = max(max_time, s.time_value)

    if max_time <= 0:
        return

    for s in statuses:
        if not isinstance(s.time_value, int):
            continue
        if s.time_value < max_time:
            s.time_lag = True
            s.time_label = f"{s.time_value} (*)"
        else:
            s.time_label = str(s.time_value)


def build_legend(
    statuses: t.List[ProviderStatus],
) -> t.List[t.Tuple[str, str, t.Optional[str]]]:
    has_time_lag = any(s.time_lag for s in statuses)
    has_unknown_archive = any(s.archive_unknown for s in statuses)
    has_mc_lag = any(s.mc_lag for s in statuses)
    has_shard_lag = any(s.shard_lag for s in statuses)

    rows: t.List[t.Tuple[str, str, t.Optional[str]]] = []

    if has_time_lag:
        rows.append(
            (
                "(*)",
                "LS time is behind maximum time across LS",
                Fore.YELLOW,
            )
        )

    if has_unknown_archive:
        rows.append(
            (
                "(?)",
                "Failed to determine archive depth for this LS",
                Fore.YELLOW,
            )
        )

    if has_mc_lag:
        rows.append(
            (
                "(!)",
                "Masterchain seqno is behind maximum across LS",
                Fore.RED,
            )
        )

    if has_shard_lag:
        rows.append(
            (
                "(!!)",
                "One or more shardchain seqno is behind maximum for that shard",
                Fore.RED,
            )
        )

    return rows


def print_status(statuses: t.List[ProviderStatus]) -> None:
    annotate_seqno_lags(statuses)
    annotate_time_lags(statuses)

    headers = [
        "LS",
        "IP",
        "PORT",
        "Connect",
        "Request",
        "Ping",
        "Version",
        "Time",
        "Last block seqno",
        "Archive depth",
    ]

    rows: t.List[t.List[str]] = []
    row_styles: t.List[t.Optional[t.Tuple[str, bool]]] = []

    for s in statuses:
        row = [
            str(s.index),
            s.host,
            str(s.port),
            f"{s.connect_ms} ms" if s.connect_ms is not None else "-",
            f"{s.request_ms} ms" if s.request_ms is not None else "-",
            f"{s.ping_ms:.0f} ms" if s.ping_ms is not None else "-",
            s.version or "-",
            s.time_label or (str(s.time_value) if s.time_value is not None else "-"),
            s.last_block_seqno_label
            or (str(s.last_block_seqno_raw) if s.last_block_seqno_raw else "-"),
            s.archive_depth_label or "-",
        ]
        rows.append(row)

        if s.shard_lag or s.mc_lag:
            row_styles.append((Fore.RED, True))
        elif s.time_lag or s.archive_unknown:
            row_styles.append((Fore.YELLOW, False))
        else:
            row_styles.append(None)

    print_table(headers, rows, row_styles=row_styles)

    legend_rows = build_legend(statuses)
    if legend_rows:
        print()
        legend_headers = ["Mark", "Description"]
        legend_data: t.List[t.List[str]] = []

        for mark, desc, fg in legend_rows:
            colored_mark = color(mark, fg=fg, bright=True) if fg else mark
            legend_data.append([colored_mark, desc])

        print_table(
            legend_headers,
            legend_data,
            row_styles=[None] * len(legend_data),
        )
