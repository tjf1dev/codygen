import aiosqlite
import json
import time
import os
import aiofiles
import asyncio
import sys
import logger
import readchar
from warnings import deprecated

DB_FILE = "codygen.db"
config_ver = 1003


async def create_table():
    async with aiosqlite.connect(DB_FILE) as con:
        await con.execute(
            f"""--sql
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '>',
                prefix_enabled BOOLEAN DEFAULT 1,
                level_per_message INTEGER DEFAULT 0,
                levelup_channel INTEGER,
                logging_settings TEXT DEFAULT '{{}}',
                module_settings TEXT DEFAULT '{{}}',
                config_ver INTEGER DEFAULT {config_ver},
                timestamp INTEGER DEFAULT (strftime('%s', 'now'))
            )
            """
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS guild_commands (
                guild_id INTEGER PRIMARY KEY,
                wokemeter_min INTEGER DEFAULT 0,
                wokemeter_max INTEGER DEFAULT 100
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS global_boosts (
                guild_id INTEGER PRIMARY KEY,
                percentage INTEGER NOT NULL,
                expires INTEGER DEFAULT 0
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS role_boosts (
                role_id INTEGER PRIMARY KEY,
                percentage INTEGER NOT NULL,
                expires INTEGER DEFAULT 0
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS user_boosts (
                    user_id INTEGER,
                    guild_id INTEGER,
                    percentage INTEGER NOT NULL,
                    expires INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS level_rewards (
                guild_id INTEGER,
                level INTEGER,
                reward_id INTEGER,
                PRIMARY KEY (guild_id, level, reward_id)
            );
            """
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER,
                user_id INTEGER,
                xp INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS modules (
                guild_id INTEGER PRIMARY KEY,
                admin BOOLEAN NOT NULL,
                applications BOOLEAN NOT NULL,
                codygen BOOLEAN NOT NULL,
                ipcx_api BOOLEAN NOT NULL,
                fm BOOLEAN NOT NULL,
                fun BOOLEAN NOT NULL,
                info BOOLEAN NOT NULL,
                level BOOLEAN NOT NULL,
                moderation BOOLEAN NOT NULL,
                settings BOOLEAN NOT NULL,
                utility BOOLEAN NOT NULL,
                logging BOOLEAN NOT NULL,
                ticket BOOLEAN NOT NULL,
                testing BOOLEAN NOT NULL,
                forms BOOLEAN NOT NULL
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS webhooks (
                channel_id INTEGER,
                webhook_id INTEGER,
                webhook_token TEXT,
                PRIMARY KEY (channel_id, webhook_id)

            )
            """
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS xp_wheel_event (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                min_range INTEGER DEFAULT 0,
                max_range INTEGER DEFAULT 10
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS xp_wheel_bets (
                event_id INTEGER,
                user_id INTEGER,
                number INTEGER,
                timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (event_id) REFERENCES xp_wheel_event(event_id),
                PRIMARY KEY (event_id, user_id)
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS primary_guild_roles (
                guild_id INTEGER PRIMARY KEY,
                role_id INTEGER
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS uotm_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                active INTEGER,
                name TEXT NOT NULL,
                timestamp INTEGER DEFAULT (strftime('%s', 'now'))
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS uotm_candidates (
                event_id INTEGER,
                user_id TEXT NOT NULL,
                timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                PRIMARY KEY (event_id, user_id),
                FOREIGN KEY (event_id) REFERENCES uotm_events(event_id)
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS uotm_votes (
                event_id INTEGER,
                user_id INTEGER,
                vote_id INTEGER,
                timestamp INTEGER DEFAULT (strftime('%s', 'now')),
                PRIMARY KEY (event_id, user_id),
                FOREIGN KEY (event_id) REFERENCES uotm_events(event_id)
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                author_id INTEGER, --? ID of the user who created the ticket
                users TEXT DEFAULT '[]', --? list of IDs 
                timestamp INTEGER DEFAULT (strftime('%s', 'now'))
            )"""
        )
        logger.info("created (missing?) tables")
        await con.commit()


async def add_column():
    async with aiosqlite.connect(DB_FILE) as con:
        table = input("table (e.g 'modules') >")
        column = input("column name (e.g 'logging') >")
        data = input("extra data (e.g 'BOOLEAN DEFAULT 1') >")
        await con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {data}")


async def backup_and_recreate():
    if not os.path.exists(DB_FILE):
        logger.error("database does not exist.")
        return
    logger.warning("are you sure you want to proceed?")
    logger.warning("any interruptions will result in a corrupted database.")
    logger.warning("make sure a snapshot has been created recently.")
    logger.info("press 'y' to start recreation.")
    k = readchar.readkey()
    if k.lower() != "y":
        logger.warning("invalid input, closing.")
        return
    async with aiosqlite.connect(DB_FILE) as con:
        con.row_factory = aiosqlite.Row

        # get all table names
        tables_res = await con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = [row["name"] for row in await tables_res.fetchall()]

        # backup data
        backup_data = {}
        for table in tables:
            cur = await con.execute(f"SELECT * FROM {table}")
            rows = await cur.fetchall()
            backup_data[table] = [dict(row) for row in rows]

        # drop all tables
        for table in tables:
            await con.execute(f"DROP TABLE IF EXISTS {table}")
        await con.commit()
        logger.debug("dropped all tables.")

        # recreate tables
        await create_table()
        logger.debug("recreated all tables.")

        # restore data
        for table, rows in backup_data.items():
            if not rows:
                continue
            columns = rows[0].keys()
            placeholders = ", ".join("?" for _ in columns)
            columns_str = ", ".join(columns)
            for row in rows:
                values = tuple(row[col] for col in columns)
                await con.execute(
                    f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})",
                    values,
                )
        await con.commit()
        logger.debug("restored all data.")
        logger.ok("finished!")


@deprecated(
    "removing in 0.40-beta / 0.42-alpha; json data management should not be used anymore."
)
async def convert_from_json():
    if os.path.exists(DB_FILE):
        logger.warning(
            "looks like the database already exists.\nthe program cannot proceed with an already existing database"
        )
        logger.info("to just create the tables, run this script with the -t argument")
        return
    await create_table()
    async with aiosqlite.connect(DB_FILE) as con:
        for f in os.listdir("data/guilds"):
            async with aiofiles.open(f"data/guilds/{f}", mode="r") as ff:
                logger.debug(f"now processing: {f}")
                guild_id = int(f[:-5])
                content = await ff.read()
                data = json.loads(content)
                for level, role in data["modules"]["level"].get("rewards", {}).items():
                    await con.execute(
                        """INSERT INTO level_rewards (guild_id, level, reward_id) VALUES (?, ?, ?)""",
                        (guild_id, level, role),
                    )
                logger.debug("inserted level rewards")
                # await con.commit()
                # continue
                await con.execute(
                    """INSERT INTO guilds (guild_id, prefix, prefix_enabled, level_per_message, levelup_channel, config_ver, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        guild_id,
                        data["prefix"]["prefix"],
                        data["prefix"]["prefix_enabled"],
                        data["modules"]["level"]["per_message"],
                        data["modules"]["level"]["levelup"]["channel"],
                        data.get("config_ver", 1001),
                        data.get("timestamp", time.time()),
                    ),
                )
                logger.debug("inserted guild config")
                for user, xp_data in data["stats"]["level"].get("users", {}).items():
                    await con.execute(
                        """INSERT INTO users (guild_id, user_id, xp) VALUES (?, ?, ?)""",
                        (guild_id, user, xp_data.get("xp", 0)),
                    )

                logger.debug("inserted leveling data")
                await con.execute(
                    """INSERT INTO guild_commands (guild_id, wokemeter_min, wokemeter_max) VALUES (?, ?, ?)""",
                    (
                        guild_id,
                        data["commands"]["wokemeter"]["woke_min"],
                        data["commands"]["wokemeter"]["woke_max"],
                    ),
                )
                logger.debug("inserted command-specific data")
                boosts = data["modules"]["level"].get("boost", {})
                await con.execute(
                    """INSERT INTO global_boosts (guild_id, percentage, expires) VALUES (?, ?, ?)""",
                    (
                        guild_id,
                        boosts.get("global", {}).get("percentage", 0),
                        boosts.get("global", {}).get("expires", 0),
                    ),
                )
                logger.debug("inserted global boosts")
                user_boosts = boosts.get("user", {})
                for user, boost in user_boosts.items():
                    await con.execute(
                        """INSERT INTO user_boosts (guild_id, user_id, percentage, expires) VALUES (?, ?, ?, ?)""",
                        (
                            guild_id,
                            user,
                            boost.get("percentage", 0),
                            boost.get("expires", 0),
                        ),
                    )
                logger.debug("inserted user boosts")
                role_boosts = boosts.get("role", {})
                for role, boost in role_boosts.items():
                    await con.execute(
                        """INSERT INTO role_boosts (role_id, percentage, expires) VALUES (?, ?, ?)""",
                        (
                            role,
                            boost.get("percentage", 0),
                            boost.get("expires", 0),
                        ),
                    )
                logger.debug("inserted role boosts")
        await con.commit()
        await con.close()
        logger.ok("all done! converted your existing json data into a database")


async def get_database_latency(db):
    start = time.perf_counter()
    async with db.execute("SELECT 1") as cursor:
        await cursor.fetchone()
    end = time.perf_counter()
    latency_ms = (end - start) * 1000
    return latency_ms


async def connect() -> aiosqlite.Connection:
    return await aiosqlite.connect(DB_FILE)


async def user_tests():
    con = await aiosqlite.connect(DB_FILE)
    cur: aiosqlite.Cursor = await con.cursor()
    rewards_res = await cur.execute(
        "SELECT level, reward_id FROM level_rewards WHERE guild_id=?",
        (1333785291584180244,),
    )
    logger.debug(await rewards_res.fetchall())
    users_res = await cur.execute(
        "SELECT user_id, xp FROM users WHERE guild_id=?", (1333785291584180244,)
    )
    users = await users_res.fetchall()
    logger.debug(users)


if __name__ == "__main__":
    if "-t" in sys.argv:
        asyncio.run(create_table())
    elif "-c" in sys.argv:
        asyncio.run(add_column())
    elif "-s" in sys.argv:
        asyncio.run(user_tests())
    elif "-j":
        asyncio.run(convert_from_json())
