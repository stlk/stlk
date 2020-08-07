import pathlib
import re
import os
import textwrap

from stravalib.client import Client
from stravalib import unithelper

root = pathlib.Path(__file__).parent.resolve()

client_id = os.environ.get("STRAVA_CLIENT_ID")
client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")

# https://github.com/hozn/stravalib

def replace_chunk(content, marker, chunk, inline=False):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)


def get_stat_values(totals):
    return f"""\
    distance: {unithelper.kilometers(totals.distance)}  
    elevation_gain: {totals.elevation_gain}  
    count: {totals.count}
    """


def fetch_stats():
    client = Client()

    refresh_response = client.refresh_access_token(client_id=client_id, client_secret=client_secret,refresh_token=refresh_token)
    client.access_token = refresh_response['access_token']
    stats = client.get_athlete_stats()

    return textwrap.dedent(
        f"""\
    #### Recent rides

{get_stat_values(stats.recent_ride_totals)}

    #### YTD ride totals

{get_stat_values(stats.ytd_ride_totals)}

    #### All ride totals

{get_stat_values(stats.all_ride_totals)}
    """
    )


readme = root / "README.md"
readme_contents = readme.open().read()

stats = fetch_stats()
rewritten = replace_chunk(readme_contents, "strava_stats", stats)

readme.open("w").write(rewritten)
