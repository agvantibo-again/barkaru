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

cardinal_stats = [
    "exogrit",
    "shadelust",
    "neocognition",
    "wardbloom",
    "paralleloquence",
    "chronacumen",
    "aethertune",
]
explosion_bites = [
    "Fate emboldens",
    "Harmony befalls the Stars",
    "Polari gleams",
    "Lundara approves",
    "A Chord resounds",
    "The Veil beckons",
    "Destiny interferes",
    "Fortune glistens",
    "The Shroud observes",
]
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
    stats = dict([(stat, -1) for stat in cardinal_stats])
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
        for stat, value in self.stats.items():
            stat_spread += f"\n\t{stat}: {value}"
        return f'Prophet "{self.name}" registered as "{self.cname}"{stat_spread}'

    def roll(self, prophet: typing.Self, stat_kind: str, stat: int) -> tuple:
        """Calculate actual random die roll results"""
        n_rolls = 0
        rolls = list()
        explosions = 0
        exploded = False
        while n_rolls < roll_limit and stat > 0:
            rolls.append(random.randint(0, prophet.die_sides - 1))
            stat -= 1
            if rolls[-1] in prophet.stats.get(stat_kind):
                exploded = True
                stat += 1
            else:
                exploded = False
            n_rolls += 1
        return tuple(rolls)

    def do_roll(
        self,
        by_prophet: typing.Self,
        stat_kind: str,
        by_stat: int,
        against_prophet: typing.Self,
        against_stat: int,
    ) -> str:
        """Batch and format a full dice roll"""
        output = list()
        by_rolls = self.roll(by_prophet, stat_kind, by_stat)
        if len(by_rolls) == 0:
            output.append(f"You rolled nothing. You suck at {stat_kind}.")
        else:
            aggregate_line_0 = "You rolled"
            aggregate_line = aggregate_line_0
            for roll in by_rolls:
                aggregate_line += f" {roll}"
                log.debug(f"Comparing roll {roll} with {by_prophet.stats}")
                if roll in by_prophet.stats.get(stat_kind):
                    aggregate_line += f"... {random.choice(explosion_bites)}!"
            output.append(aggregate_line)
            output.append(f"In total: {sum(by_rolls)}. Well done.")

        if against_prophet.cname == "nihil":
            against_rolls = [against_stat]
            output.append(f"You're going up against at least a {against_stat}!")
        else:
            against_rolls = self.roll(against_prophet, stat_kind, against_stat)
            if len(by_rolls) == 0:
                output.append(f"They rolled nothing. They suck.")
            else:
                aggregate_line_0 = "They rolled"
                aggregate_line = aggregate_line_0
                for roll in against_rolls:
                    aggregate_line += f" {roll}"
                    if roll in by_prophet.stats.get(stat_kind):
                        aggregate_line += f"... {random.choice(explosion_bites)}!"
                output.append(aggregate_line)
                output.append(f"In total: {sum(against_rolls)}")
        if sum(by_rolls) > sum(against_rolls):
            output.append(f"Victory! ({sum(by_rolls)} > {sum(against_rolls)})")
        elif sum(by_rolls) < sum(against_rolls):
            output.append(f"Defeat. ({sum(by_rolls)} < {sum(against_rolls)})")
        else:
            output.append(f"Evenly matched.")

        return "\n".join(output)


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


# Argument template: stat_kind by_prophet stat against_prophet stat
def parse_argv1(raw_args: list, prophets: dict) -> dict:
    "Parse the basic argument array and complain if something's off"
    arguments = dict()
    if len(raw_args) != 5:
        raise ValueError(f"Unexpected number of arguments: {len(raw_args)}")
    stat_kind, by_prophet, by_stat, against_prophet, against_stat = raw_args[:5]
    if stat_kind in cardinal_stats:
        arguments["stat_kind"] = stat_kind
    else:
        raise ValueError(f'"{stat_kind}" isn\'t a stat I know :<')
    if by_prophet in prophets and against_prophet in prophets:
        arguments["by_prophet"] = prophets[by_prophet]
        arguments["against_prophet"] = prophets[against_prophet]
    else:
        raise ValueError(
            f'Prophets "{by_prophet}" or "{against_prophet}" aren\'t the ones I know :<'
        )
    arguments["by_stat"] = int(by_stat)
    arguments["against_stat"] = int(against_stat)

    return arguments


@bot.command()
async def roll(
    ctx,
    stat_kind: str,
    by_prophet: str,
    by_stat: str,
    against_prophet: str,
    against_stat: str,
):
    """Roll the Aethertuned dice. See what fortune brings."""
    try:
        argv = parse_argv1(
            (stat_kind, by_prophet, by_stat, against_prophet, against_stat), prophets
        )
        result = prophets[argv["by_prophet"].cname].do_roll(**argv)
        await ctx.send(result)
    except Exception as exception:
        err_string = f"Error!\n{str(exception)}\nInvoked with:\n{argv}"
        traceback.print_exception(exception)
        log.warning(err_string)
        await ctx.send(err_string)


async def main():
    global prophets

    log.info("Hello from barkaru!")
    prophets = load_quin_prophet_stats("prophets.txt")
    prophets["nihil"] = Prophet.__new__(Prophet)
    log.info(f"Loaded {len(prophets)} prophets!")
    for prophet in prophets.values():
        log.debug(prophet)

    async with bot:
        await bot.start(bot_token)


if __name__ == "__main__":
    asyncio.run(main())
