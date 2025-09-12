import aiosqlite
import json
import time
import os
import aiofiles
import asyncio
import sys

DB_FILE = "codygen.db"
config_ver = 1002


async def create_table():
    async with aiosqlite.connect(DB_FILE) as con:
        await con.execute(
            """CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '>',
                prefix_enabled BOOLEAN DEFAULT 1,
                level_per_message INTEGER DEFAULT 0,
                levelup_channel INTEGER,
                config_ver INTEGER DEFAULT 1002,
                timestamp REAL
            )"""
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
                percentage INTEGER,
                expires REAL
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS role_boosts (
                role_id INTEGER PRIMARY KEY,
                percentage INTEGER,
                expires REAL
            )"""
        )
        await con.execute(
            """CREATE TABLE IF NOT EXISTS user_boosts (
                    user_id INTEGER,
                    guild_id INTEGER,
                    percentage INTEGER,
                    expires REAL,
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
                admin BOOLEAN DEFAULT 1,
                applications BOOLEAN DEFAULT 1,
                codygen BOOLEAN DEFAULT 1,
                dashboard BOOLEAN DEFAULT 1,
                fm BOOLEAN DEFAULT 1,
                fun BOOLEAN DEFAULT 1,
                info BOOLEAN DEFAULT 1,
                level BOOLEAN DEFAULT 1,
                moderation BOOLEAN DEFAULT 1,
                settings BOOLEAN DEFAULT 1,
                utility BOOLEAN DEFAULT 1
            )"""
        )
        print("created (missing?) tables")
        await con.commit()


async def convert_from_json():
    if os.path.exists(DB_FILE):
        print(
            "looks like the database already exists.\nthe program cannot proceed with an already existing database"
        )
        print("to just create the tables, run this script with the -t argument")
        return
    await create_table()
    async with aiosqlite.connect(DB_FILE) as con:
        for f in os.listdir("data/guilds"):
            async with aiofiles.open(f"data/guilds/{f}", mode="r") as ff:
                print(f"now processing: {f}")
                guild_id = int(f[:-5])
                content = await ff.read()
                data = json.loads(content)
                for level, role in data["modules"]["level"].get("rewards", {}).items():
                    await con.execute(
                        """INSERT INTO level_rewards (guild_id, level, reward_id) VALUES (?, ?, ?)""",
                        (guild_id, level, role),
                    )
                print("inserted level rewards")
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
                print("inserted guild config")
                for user, xp_data in data["stats"]["level"].get("users", {}).items():
                    await con.execute(
                        """INSERT INTO users (guild_id, user_id, xp) VALUES (?, ?, ?)""",
                        (guild_id, user, xp_data.get("xp", 0)),
                    )

                print("inserted leveling data")
                await con.execute(
                    """INSERT INTO guild_commands (guild_id, wokemeter_min, wokemeter_max) VALUES (?, ?, ?)""",
                    (
                        guild_id,
                        data["commands"]["wokemeter"]["woke_min"],
                        data["commands"]["wokemeter"]["woke_max"],
                    ),
                )
                print("inserted command-specific data")
                boosts = data["modules"]["level"].get("boost", {})
                await con.execute(
                    """INSERT INTO global_boosts (guild_id, percentage, expires) VALUES (?, ?, ?)""",
                    (
                        guild_id,
                        boosts.get("global", {}).get("percentage", 0),
                        boosts.get("global", {}).get("expires", 0),
                    ),
                )
                print("inserted global boosts")
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
                print("inserted user boosts")
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
                print("inserted role boosts")
        await con.commit()
        await con.close()
        print("all done! converted your existing json data into a database")


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
    print(await rewards_res.fetchall())
    users_res = await cur.execute(
        "SELECT user_id, xp FROM users WHERE guild_id=?", (1333785291584180244,)
    )
    users = await users_res.fetchall()
    print(users)


if __name__ == "__main__":
    if "-t" in sys.argv:
        asyncio.run(create_table())
    elif "-s" in sys.argv:
        asyncio.run(user_tests())
    else:
        asyncio.run(convert_from_json())
