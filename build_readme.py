import pathlib
import re
import os
import textwrap

import httpx


root = pathlib.Path(__file__).parent.resolve()

STRAVA_TOKEN = os.environ.get("STRAVA_TOKEN")


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
        distance: {(totals["distance"] / 1000):,.0f} km
        elevation_gain: {totals["elevation_gain"]:,.0f} m
        count: {totals["count"]}
        """


def fetch_stats():
    athlete_id = 15733086

    try:
        stats = httpx.get(
            f"https://www.strava.com/api/v3/athletes/{athlete_id}/stats",
            headers={"Authorization": f"Bearer {STRAVA_TOKEN}"},
        ).json()
        print(stats)
        return textwrap.dedent(
            f"""\
        #### Recent rides

{get_stat_values(stats["recent_ride_totals"])}

        #### YTD ride totals

{get_stat_values(stats["ytd_ride_totals"])}

        #### All ride totals

{get_stat_values(stats["all_ride_totals"])}
        """
        )
    except Exception as e:
        print(f"Exception when calling AthletesApi->getStats: {e}\n")


if __name__ == "__main__":
    readme = root / "README.md"
    readme_contents = readme.open().read()

    stats = fetch_stats()
    rewritten = replace_chunk(readme_contents, "strava_stats", stats)

    readme.open("w").write(rewritten)
