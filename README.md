This script will analyze fisu killboards to determine the outcome of a Jaeger scrim. Useful for matches where ScrimPlanetmans and the API aren't getting along and everyone is following the rules.

Values are hard-coded following the IO/ISL ruleset.

Accounts for:
- Kills
- Deaths
- Headshots
- Teamkills
- Suicides
- Non-participants
- Likely 0-point kills (default grenades and decimator)

Does **not** account for:
- Anything not on the killboard (i.e. point captures)
- Banned weapons
- Any 0-point weapons other than explosive grenades or decis
- Probably anything else