import aiosqlite
import os
import datetime
from pathlib import Path


async def snapshot_db() -> Path | str:
    snapshot_dir = Path("snapshots")
    os.makedirs(snapshot_dir, exist_ok=True)

    snapshot_file = snapshot_dir / (
        datetime.datetime.now().strftime("%d-%m-%Y_%H.%M.%S") + ".db"
    )

    async with (
        aiosqlite.connect("codygen.db") as src,
        aiosqlite.connect(snapshot_file) as dest,
    ):
        await src.execute("PRAGMA wal_checkpoint(FULL);")
        await src.commit()
        await src.backup(dest)
    return snapshot_file
