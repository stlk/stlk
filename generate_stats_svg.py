import pytz
import os
from stravalib.client import Client
import pathlib
import math
import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import typer

root = pathlib.Path(__file__).parent.resolve()

env = Environment(loader=FileSystemLoader(root), autoescape=select_autoescape())

app = typer.Typer()


def get_rides():
    client = Client()

    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
    refresh_token = os.environ.get("STRAVA_REFRESH_TOKEN")

    refresh_response = client.refresh_access_token(
        client_id=client_id, client_secret=client_secret, refresh_token=refresh_token
    )
    client.access_token = refresh_response["access_token"]

    activities = client.get_activities()

    return [
        {
            "date": activity.start_date.isoformat(),
            "distance": activity.distance.get_num(),
        }
        for activity in activities
    ]


def generate(activities_data):
    dataframe = pd.DataFrame.from_records(activities_data)
    dataframe["date"] = pd.to_datetime(dataframe.date)

    # #Setting the date_time column as the index
    dataframe = dataframe.set_index("date")

    print(dataframe.head())

    by_day = dataframe["distance"].resample("D").agg("sum")

    vmax = by_day.max()

    years = reversed(np.unique(dataframe.index.year))

    data = [
        generate_year(by_day, year, idx, max=vmax) for idx, year in enumerate(years)
    ]

    template = env.get_template("strava_stats_template.svg")
    result = template.render(data=data)
    (root / "strava_stats.svg").write_text(result)


def generate_year(by_day, year, idx, max):

    # Filter on year.
    by_day = by_day[str(year)]

    # Add missing days.
    by_day = by_day.reindex(
        pd.date_range(start=str(year), end=str(year + 1), tz=pytz.UTC, freq="D")[:-1]
    )

    # Create data frame we can pivot later.
    by_day = pd.DataFrame(
        {
            "data": by_day,
            "fill": 1,
            "day": by_day.index.dayofweek,
            "week": by_day.index.isocalendar().week,
        }
    )

    # There may be some days assigned to previous year's last week or
    # next year's first week. We create new week numbers for them so
    # the ordering stays intact and week/day pairs unique.
    by_day.loc[(by_day.index.month == 1) & (by_day.week > 50), "week"] = 0
    by_day.loc[(by_day.index.month == 12) & (by_day.week < 10), "week"] = (
        by_day.week.max() + 1
    )

    plot_data = by_day.pivot("day", "week", "data")

    return {
        "year": year,
        "position": 14 + 130 * idx,
        "weeks": [generate_week(week, idx, max) for idx, week in plot_data.items()],
    }


def value_to_level(value, max):
    return math.ceil(value / max * 4)


def generate_week(days, week_offset, max):
    result = [
        {"position": 4 + 15 * day, "level": value_to_level(value, max)}
        for day, value in days.items()
        if not np.isnan(value)
    ]
    return {"position": 15 * week_offset, "days": result}


@app.command()
def save_rides_to_file():
    activities_data = get_rides()

    with open(root / "rides.json", "w") as file:
        json.dump(activities_data, file, indent=2)
    typer.echo(f"Saved {len(activities_data)} activities")


@app.command()
def generate_from_file():
    with open(root / "rides.json", "r") as file:
        activities_data = json.load(file)
    generate(activities_data)


@app.command()
def generate_live():
    activities_data = get_rides()
    generate(activities_data)


if __name__ == "__main__":
    app()
