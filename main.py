#!/usr/bin/env python3
"""
Script to analyze fisu killboards of scrim participants to determine rough
match scoring in case the usual ScrimPlanetmans script does not work. Not
very efficient and has some faults (incomplete coverage of zero-point weapons,
no coverage of banned weapons or captures, hard-coded point values for IO/ISL)
"""

import bs4
from colorama import Fore, Style, Back
from datetime import datetime, timezone, timedelta
import re
import os


FACTIONS = {}
KB_DIR = os.path.abspath(os.path.join('.', 'Killboards'))
SCORES = {}
START_TIME = 0
TEAM_KILLED = []


def calculate_net(player: str, stats: dict[str, int]) -> int:
    net_score = calculate_points(stats)
    net_score -= stats['deaths']

    for tk in TEAM_KILLED:
        if tk == player:
            net_score += 1

    return net_score


def calculate_points(stats: dict[str, int]) -> int:
    points = 0
    points += stats['kills']
    points -= stats['tks'] * 2
    points -= stats['suicides'] * 2
    points -= stats['nulls']

    return points


def determine_player_score(team: str, player: str, stats: dict[str, int]) -> None:
    SCORES[team][player]['kills'] = stats['kills']
    SCORES[team][player]['deaths'] = stats['deaths']
    SCORES[team][player]['tks'] = stats['tks']
    SCORES[team][player]['suicides'] = stats['suicides']
    SCORES[team][player]['points'] = calculate_points(stats)
    SCORES[team][player]['net'] = calculate_net(player, stats)

    if stats['kills'] > 0:
        SCORES[team][player]['hsr'] = stats['headshots'] / stats['kills']
    else:
        SCORES[team][player]['hsr'] = 0


def get_team_faction(team: str) -> int:
    return FACTIONS[team]


def get_teams() -> list[str]:
    teams = []

    for item in os.listdir(KB_DIR):
        item_path = os.path.join(KB_DIR, item)
        if os.path.isdir(item_path):
            teams.append(item)
    
    if len(teams) != 2:
        print('There should be exactly two teams\' killboard directories.')
    
    return teams


def get_teams_and_players() -> dict[str, dict[str, dict[str, dict]]]:
    players = {}

    for team in get_teams():
        players[team] = {}

        team_dir = os.path.join(os.path.join(KB_DIR, team))
        for item in os.listdir(team_dir):
            item_path = os.path.join(team_dir, item)
            if os.path.isfile(item_path):
                player_name = re.match(r'^\w+', item).group(0)
                players[team][player_name] = {}

    return players


def get_killboard_path(team: str, player_name: str) -> str:
    filename = f'{player_name} - Killboard - PlanetSide 2.htm'
    return os.path.abspath(os.path.join('.', 'Killboards', team, filename))


def get_first_round_event(killboard: bs4.Tag) -> int:
    first_event = 0

    for row in killboard.find_all('tr'):
        if not row.get('class'): continue

        columns = row.find_all('td')
        date_string = columns[1].string
        date = datetime.strptime(date_string, r'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

        if date.timestamp() < START_TIME:
            return first_event
        else:
            first_event = int(columns[0].string)

    start_date = datetime.fromtimestamp(START_TIME, tz=timezone.utc)
    if (date >= start_date and date < start_date + timedelta(minutes=15)):
        return first_event

    raise Exception('Killboard is too old, could not find first event.')


def get_last_round_event(killboard: bs4.Tag) -> int:
    end_time = START_TIME + (15 * 60)

    for row in killboard.find_all('tr'):
        if not row.get('class'): continue
        
        columns = row.find_all('td')
        date_string = columns[1].string
        date = datetime.strptime(date_string, r'%Y-%m-%d %H:%M:%S')

        if date.replace(tzinfo=timezone.utc).timestamp() < end_time:
            return int(columns[0].string)

    raise Exception('Killboard is too old, could not find latest event.')


def read_player_killboard(team: str, player_name: str) -> dict[str, int]:
    killboard_path = get_killboard_path(team, player_name)

    with open(killboard_path, 'r', encoding='utf-8') as kb:
        soup = bs4.BeautifulSoup(kb.read(), 'html.parser')
        board = soup.find(id='killboard').tbody

        first_event_num = get_first_round_event(board)
        last_event_num = get_last_round_event(board)

        stats = process_round(board, team, player_name, first_event_num, last_event_num)

        return stats


def parse_event(cols: list[bs4.Tag]) -> dict[str, any]:
    def get_team_from_span(span: bs4.Tag) -> str:
        team = span.get('class')
        return team[0][-1:] if isinstance(team, list) else team[-1:]


    return {
        'attacker': re.match(r'^(?:\[\w{1,4}\]\s)?(\w+)(?:\s\([0-9~]+\))$', cols[4].a.span.string).group(1),
        'attacker_team': int(get_team_from_span(cols[4].a.span)),
        'target': re.match(r'^(?:\[\w{1,4}\]\s)?(\w+)(?:\s\([0-9~]+\))$', cols[5].a.span.string).group(1),
        'target_team': int(get_team_from_span(cols[5].a.span)),
        'headshot': True if len(cols[6].contents) > 0 and cols[6].contents[0].get('title') == 'Headshot' else False,
        'vehicle': True if len(cols[6].contents) > 0 and cols[6].contents[0].get('title') == 'Vehicle destroyed' else False,
        'method': cols[8].span.string
    }


def player_is_participant(player_name: str) -> bool:
    for team in SCORES.keys():
        for player in SCORES[team].keys():
            if (player_name == player):
                return True


def print_all_scores() -> None:
    print()
    for team in SCORES.keys():
        print_team_scores(team)
        print()


def print_team_scores(team: str) -> None:
    team_colors = {
        1: Fore.MAGENTA,
        2: Fore.BLUE,
        3: Fore.RED
    }

    team_heading_colors = {
        1: Back.MAGENTA,
        2: Back.BLUE,
        3: Back.RED
    }

    team_faction = get_team_faction(team)
    team_color = team_colors[team_faction]
    team_heading_color = team_heading_colors[team_faction]
    clr = Style.RESET_ALL

    print(f"{team_heading_color}{Style.BRIGHT}{f'Team: {team}':^69}{clr}")
    print(f"{Style.BRIGHT}{'Player Name':^28}|{'Points':^6}|{'Net':^3}|{'Kills':^5}|{'Deaths':^6}|{'HSR':^3}|{'TKs':^3}|{'Suicides':^8}{clr}")

    total_points = 0
    
    for player, s in SCORES[team].items():
        total_points += s['points']

        net_color = Fore.YELLOW if s['net'] < 0 else Fore.GREEN if s['net'] > 0 else ''
        print(f"{team_color}{player:<28}{clr}"
            f"|{s['points']:>6}"
            f"|{net_color}{s['net']:>3}{clr}"
            f"|{s['kills']:>5}"
            f"|{s['deaths']:>6}"
            f"|{s['hsr']:>3.0%}"
            f"|{s['tks']:>3}"
            f"|{s['suicides']:>8}")

    print(f"{'':28} {Style.BRIGHT}{total_points:>6}{clr}")


def process_round(board: bs4.Tag, team: str, player: str, earliest: int, latest: int) -> dict[str, int]:
    rnd_kills = 0
    rnd_deaths = 0
    rnd_headshots = 0
    rnd_suicides = 0
    rnd_tks = 0
    rnd_nulls = 0

    for row in board.find_all('tr'):
        if not row.get('class'): continue # ignore first row

        columns = row.find_all('td')
        event_num = int(columns[0].string)

        if event_num < latest: continue # skip rows after 15 min
        if event_num > earliest: break # stop after reaching first event

        event = parse_event(columns)

        if event['vehicle']: continue # ignore vehicle events

        if not player_is_participant(event['attacker']): continue # ignore interference
        if not player_is_participant(event['target']): continue

        if not FACTIONS.get('team'):
            if event['target'] == player:
                FACTIONS[team] = event['target_team']
            else:
                FACTIONS[team] = event['attacker_team']

        if event['target'] == player:
            if event['attacker'] == player: # player died to themselves
                rnd_suicides += 1
            else: # player died to someone else
                rnd_deaths += 1
        else:
            if event['attacker_team'] == event['target_team']: # someone else died on same team
                TEAM_KILLED.append(event['target'])
                rnd_tks += 1
            else: # someone else died on different team
                rnd_kills += 1

                if event['headshot']:
                    rnd_headshots += 1

        if event['attacker'] == player:
            for weapon in ['decimator', 'grenade']:
                if weapon in event['method'].lower(): # method string mentions 0 point weapon
                    rnd_nulls += 1

    return {
        'kills': rnd_kills,
        'deaths': rnd_deaths,
        'headshots': rnd_headshots,
        'suicides': rnd_suicides,
        'nulls': rnd_nulls,
        'tks': rnd_tks
    }

if __name__ == '__main__':
    START_TIME = int(input('Enter the start time of the round (epoch timestamp UTC): '))
    SCORES = get_teams_and_players()

    player_stats = {}

    for team, players in SCORES.items():
        for player in players.keys():
            player_stats[player] = read_player_killboard(team, player)
        
        for player in players.keys():
            determine_player_score(team, player, player_stats[player])

    print_all_scores()