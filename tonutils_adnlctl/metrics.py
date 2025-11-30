import asyncio
import time
import typing as t
from contextlib import suppress

from tonutils.clients import AdnlClient
from tonutils.types import WorkchainID

from .status import ProviderStatus


async def measure_connect(
    client: AdnlClient,
    timeout: int = 1,
) -> t.Tuple[bool, t.Optional[int]]:
    start = time.perf_counter()
    try:
        await asyncio.wait_for(client.connect(), timeout=timeout)
    except (Exception,):
        return False, None
    elapsed_ms = int((time.perf_counter() - start) * 1000.0)
    return True, elapsed_ms


async def measure_ping(client: AdnlClient) -> t.Optional[int]:
    try:
        if client.provider.last_ping_ms is None:
            await client.provider.pinger.ping_once()
    except (Exception,):
        return None
    return client.provider.last_ping_ms


async def fetch_version(client: AdnlClient) -> t.Optional[str]:
    try:
        result = await client.provider.get_version()
    except (Exception,):
        return None
    return str(result)


async def fetch_time(client: AdnlClient) -> t.Optional[int]:
    try:
        result = await client.provider.get_time()
    except (Exception,):
        return None
    try:
        return int(result)
    except (TypeError, ValueError):
        return None


async def measure_request_time(client: AdnlClient) -> t.Optional[int]:
    start = time.perf_counter()
    try:
        await client.provider.updater.refresh()
    except (Exception,):
        return None
    elapsed_ms = int((time.perf_counter() - start) * 1000.0)
    return elapsed_ms


async def check_archive_depth(client: AdnlClient, now: int) -> str:
    day = 86400
    first_block_utime = 1573822385
    seconds_diff = now - first_block_utime
    max_days = seconds_diff // day

    async def _probe(_days: int) -> bool:
        utime = now - _days * day
        try:
            await client.provider.lookup_block(
                workchain=WorkchainID.MASTERCHAIN,
                shard=-(2**63),
                utime=utime,
            )
            return True
        except (Exception,):
            return False

    left = 0
    right = max_days
    best_days = 0

    while left <= right:
        mid = (left + right) // 2
        if await _probe(mid):
            best_days = mid
            left = mid + 1
        else:
            right = mid - 1

    years = best_days // 365
    rem = best_days % 365
    months = rem // 30
    days = rem % 30

    parts: t.List[str] = []
    if years > 0:
        parts.append(f"{years}y")
    if months > 0:
        parts.append(f"{months}m")
    if days > 0:
        parts.append(f"{days}d")
    if not parts:
        parts.append("(?)")

    return " ".join(parts)


async def check_archive_depth_quick(client: AdnlClient, now: int) -> str:
    day = 86400
    time_offsets = [
        ("≈ 1d", 1 * day),
        ("≈ 3d", 3 * day),
        ("≈ 7d", 7 * day),
        ("≈ 14d", 14 * day),
        ("≈ 1m", 30 * day),
        ("≈ 3m", 3 * 30 * day),
        ("≈ 6m", 6 * 30 * day),
        ("≈ 9m", 9 * 30 * day),
        ("≈ 1y", 365 * day),
    ]

    async def _probe(utime: int) -> bool:
        try:
            await client.provider.lookup_block(
                workchain=WorkchainID.MASTERCHAIN,
                shard=-(2**63),
                utime=utime,
            )
            return True
        except (Exception,):
            return False

    tasks = [asyncio.create_task(_probe(now - delta)) for _, delta in time_offsets]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    depth_label = "(?)"
    for (label, _), ok in zip(time_offsets, results):
        if ok:
            depth_label = label
    return depth_label


async def probe_client(
    index: int,
    client: AdnlClient,
    use_exact: bool,
) -> ProviderStatus:
    status = ProviderStatus(
        index=index,
        host=client.provider.node.host,
        port=client.provider.node.port,
    )

    connected = False
    try:
        connected, connect_ms = await measure_connect(client, timeout=1)
        if connect_ms is not None:
            status.connect_ms = connect_ms

        if not connected:
            return status

        status.ping_ms = await measure_ping(client)
        status.time_value = await fetch_time(client)
        status.version = await fetch_version(client)
        status.request_ms = await measure_request_time(client)

        with suppress(Exception):
            last_mc_block = client.provider.last_mc_block
            if last_mc_block is not None:
                status.last_block_seqno_raw = int(last_mc_block.seqno)

                shards = await client.provider.get_all_shards_info(last_mc_block)
                shard_map: t.Dict[str, int] = {}
                for shard in shards:
                    shard_id = shard.shard.to_bytes(8, "big", signed=True).hex()
                    shard_map[shard_id] = int(shard.seqno)
                status.shards = shard_map

        with suppress(Exception):
            now = int(time.time())
            if use_exact:
                status.archive_depth_label = await check_archive_depth(
                    client=client,
                    now=now,
                )
            else:
                status.archive_depth_label = await check_archive_depth_quick(
                    client=client,
                    now=now,
                )
            if status.archive_depth_label == "(?)":
                status.archive_unknown = True

        return status
    finally:
        if connected:
            with suppress(Exception):
                await client.close()


async def probe_all_clients(
    clients: t.Sequence[AdnlClient],
    use_exact: bool,
) -> t.List[ProviderStatus]:
    tasks = [
        probe_client(index=i, client=c, use_exact=use_exact)
        for i, c in enumerate(clients)
    ]
    return await asyncio.gather(*tasks, return_exceptions=False)
