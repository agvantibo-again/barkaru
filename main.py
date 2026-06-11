#!/usr/bin/env python3

import random
import logging
import typing
import os
import asyncio
import discord
import traceback
from discord.ext import commands
from dotenv import load_dotenv

cardinal_stats = (
    "exogrit",
    "shadelust",
    "neocognition",
    "wardbloom",
    "paralleloquence",
    "chronacumen",
    "aethertune",
)
explosion_barks = list()
roll_limit = 22

load_dotenv()
log_level = os.environ.get("LOGLEVEL", "INFO").upper()
bot_token = os.environ.get("QUIN_TOKEN", "")
logging.basicConfig(filename="barkaru.log.txt")
log = logging.getLogger(__name__)
log.setLevel(log_level)
intents = discord.Intents(messages=True, guilds=True, message_content=True)
bot = commands.Bot(command_prefix="!", intents=intents)


class Prophet:
    # Defaults are for nihil
    name = "Nihil unfathomable"
    cname = "nihil"
    stats = dict([(stat, (-1,)) for stat in cardinal_stats])
    die_sides = 6

    def __init__(self, new_name: str, new_cname: str, new_stats: dict):
        self.name = new_name
        self.cname = new_cname
        self.stats = self.stats.copy()
        self.stats.update(new_stats)

    def canonicalize_name(name: str):
        """Make a human-readable name into a code-suitable one"""
        return name.lower()

    def __repr__(self):
        stat_spread = str()
        for _, value in self.stats.items():
            stat_spread += f"{value}"

        stat_spread = stat_spread.replace(",)(", "|")
        return f'Prophet "{self.name}" registered as "{self.cname}", attuned to {stat_spread}'

    def roll(self, prophet: typing.Self, stat_kind: str, stat: int) -> tuple:
        """Calculate actual random die roll results"""
        n_rolls = 0
        rolls = list()
        pending_rolls = stat
        while n_rolls <= roll_limit and pending_rolls:
            if n_rolls + pending_rolls >= roll_limit:
                pending_rolls += roll_limit - (pending_rolls + n_rolls)
            n_rolls += pending_rolls
            rolls.append(
                tuple(
                    [
                        random.randint(0, prophet.die_sides - 1)
                        for roll in range(pending_rolls)
                    ]
                )
            )
            log.debug(f"Rolled {rolls[-1]}")
            for stat in prophet.stats[stat_kind]:
                pending_rolls = rolls[-1].count(stat)
            log.debug(f"Want to roll {pending_rolls} more")

        return tuple(rolls)

    def do_roll(
        self,
        by_prophet: typing.Self,
        stat_kind: str,
        by_stat: int,
    ) -> list:
        """Batch and format a full dice roll"""
        output = list()
        output.append(f"### {stat_kind.upper()} [*{by_prophet.name}*]")
        by_rolls = self.roll(by_prophet, stat_kind, by_stat)
        if len(by_rolls) == 0:
            output.append(f"You rolled nothing. You suck at {stat_kind}.")
        else:
            total = 0
            aggregate_line_0 = "You rolled "
            aggregate_line = aggregate_line_0
            aggregate_line += " ".join(
                [
                    (
                        f"{{{stat_kind[0]}{roll}}}"
                        if roll not in by_prophet.stats[stat_kind]
                        else f"{{x{roll}}}"
                    )
                    for roll in by_rolls[0]
                ]
            )
            total += sum(by_rolls[0])
            if len(by_rolls) > 1:
                for i_rolls in range(1, len(by_rolls)):
                    aggregate_line += f"... {random.choice(explosion_barks)}!"
                    output.append(aggregate_line)
                    aggregate_line = aggregate_line_0
                    aggregate_line += " ".join(
                        [
                            (
                                f"{{{stat_kind[0]}{roll}}}"
                                if roll not in by_prophet.stats[stat_kind]
                                else f"{{x{roll}}}"
                            )
                            for roll in by_rolls[i_rolls]
                        ]
                    )
                    total += sum(by_rolls[i_rolls])
            output.append(aggregate_line)
            if sum(map(len, by_rolls)) >= roll_limit:
                output.append("[TRANSMISSION INTERRUPTED]")
            output.append(f"In total: {total}.")

        return output


@bot.event
async def on_ready():
    """Acknowledge Discord authorization in logs"""
    log.info(f"Logged in as {bot.user}")


@bot.command()
async def ping(ctx):
    """Send a small ping message. To know I'm here."""
    await ctx.send("Ping from Barkaru OwO")


def load_quin_prophet_stats(path: str) -> dict:
    """Parse Quin\'s not-CSV file format and ingest prophets and their stats from it"""
    prophets_stats = dict()
    with open(path) as file:
        for line in file.readlines():
            prophet_name, stats_string = line.split()
            prophets_stats[prophet_name] = stats_string

    prophets = dict()
    for prophet_name, stats_string in prophets_stats.items():
        statblock = dict()
        for i_stat in range(len(stats_string)):
            statblock[cardinal_stats[i_stat]] = (int(stats_string[i_stat]),)
        prophet_cname = Prophet.canonicalize_name(prophet_name)
        prophets[prophet_cname] = Prophet(prophet_name, prophet_cname, statblock)

    return prophets


def load_explosion_barks(path: str, array: list):
    """Parse a text file line by line and ingest explosion barks"""
    with open(path) as file:
        for line in file.readlines():
            if "#" not in line:
                array.append(line.removesuffix("\n"))


def fuzzy_match(ingress: str, against: tuple) -> tuple:
    """Make an effort to match a string against some states it should represent"""
    """Returns a tuple of either String or None and an optional error message if None"""
    matches = list(against)
    for i_char in range(len(ingress)):
        droplist = list()
        for word in matches:
            if len(word) <= i_char or word[i_char] != ingress[i_char]:
                droplist.append(word)
        matches = [m for m in matches if m not in droplist]
        if len(matches) == 0:
            return (None, f"No matches found for {ingress}")
        if len(matches) == 1:
            return (matches[0], None)
    return (None, f"Multiple matches found for \"{ingress}\": {'|'.join(matches)}")


# Argument template: stat_kind by_prophet stat
def parse_argv1(raw_args: list, prophets: dict) -> dict:
    "Parse the basic argument array and complain if something's off"
    arguments = dict()
    if len(raw_args) != 3:
        raise ValueError(f"Unexpected number of arguments: {len(raw_args)}")
    stat_kind, by_prophet, by_stat = raw_args[:3]
    stat_kind = fuzzy_match(stat_kind, cardinal_stats)
    by_prophet = fuzzy_match(by_prophet, list(prophets.keys()))

    if not stat_kind[0]:
        raise ValueError(f"Trouble looking up Stat: {stat_kind[1]} :<")
    if not by_prophet[0]:
        raise ValueError(f"Trouble looking up Prophet: {by_prophet[1]} :<")

    arguments["stat_kind"] = stat_kind[0]
    arguments["by_prophet"] = prophets.get(by_prophet[0])
    arguments["by_stat"] = int(by_stat)

    return arguments


@bot.command()
async def roll(
    ctx,
    stat_kind: str,
    by_prophet: str,
    by_stat: str,
):
    """Roll the Aethertuned dice. See what fortune brings."""
    try:
        emotes_task = asyncio.create_task(ctx.guild.fetch_emojis())
        argv = parse_argv1((stat_kind, by_prophet, by_stat), prophets)
        result = prophets[argv["by_prophet"].cname].do_roll(**argv)

        emotes = await emotes_task
        emotes = {emote.name: str(emote) for emote in emotes}

        for line in result:
            await ctx.send(line.format(**emotes))
    except Exception as exception:
        err_string = "".join(traceback.format_exception(exception))
        log.warning(err_string)
        await ctx.send(err_string)


@bot.command()
async def prophets(ctx):
    """Observe the Prophets 22 and their alignment"""
    prophets_string = "\n".join(
        [
            "```",
            f'The values are in canonical order: {" ".join(cardinal_stats)}',
            f'{"\n".join(map(str, prophets.values()))}',
            "```",
        ]
    )
    log.debug(prophets_string)
    log.debug(f"Length: {len(prophets_string)}")
    await ctx.send(prophets_string)


async def main():
    global prophets

    log.info("Hello from barkaru!")
    prophets = load_quin_prophet_stats("prophets.txt")
    prophets["nihil"] = Prophet.__new__(Prophet)
    log.info(f"Loaded {len(prophets)} prophets!")
    load_explosion_barks("explosions.txt", explosion_barks)
    log.info(f"Loaded {len(explosion_barks)} explosion barks!")
    for prophet in prophets.values():
        log.debug(prophet)

    async with bot:
        await bot.start(bot_token)


if __name__ == "__main__":
    asyncio.run(main())
