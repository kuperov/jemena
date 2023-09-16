#!./.venv/bin/python3

import requests
import urllib
import csv
import configparser
import os
import click
import polars as pl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


@click.group()
def jemena():
    """Tool for downloading electricity usage data from Jemena."""
    pass

@jemena.command()
def update():
    """Fetch latest data from Jemena."""
    config = configparser.ConfigParser()
    config.read(os.path.expanduser('~/.jemenarc'))
    email = config.get('DEFAULT', 'email')
    password = config.get('DEFAULT', 'password')
    # The URL of the CSV file to download
    csv_file_url = "https://electricityoutlook.jemena.com.au/electricityView/download"
    # The file name to save the CSV file as
    csv_file_name = "electricity_outlook.csv"
    # The login post target
    login_post_target = "/login_security_check"
    # Log in to the Jemena website
    site_base = "https://electricityoutlook.jemena.com.au/"
    login_data = {
        "login_email": email,
        "login_password": password,
        "submit": "Sign In"}
    print("Logging in to Jemena")
    session = requests.Session()
    login_response = session.post(site_base + login_post_target, data=login_data)
    assert login_response.status_code == 200, "Login failed"
    print("Download usage data file")
    csv_file_response = session.get(csv_file_url)
    with open(csv_file_name, "wb") as csv_file:
        csv_file.write(csv_file_response.content)
    print("CSV file downloaded successfully")


def get_data():
    """Load and process raw data"""
    dat = (
        pl
        .read_csv('electricity_outlook.csv', try_parse_dates=True)
        .drop(['NMI', 'METER SERIAL NUMBER', 'CON/GEN', 'ESTIMATED?'])
        .melt(id_vars=['DATE'], variable_name='period', value_name='usage')
        .sort(by=['DATE', 'period'])
        .with_columns(pl.col('period').str.extract(r"(\d{2}:\d{2}) - .+", group_index=1))
        .with_columns(pl.col('period').str.strptime(pl.Time, format="%H:%M"))
        .with_columns(pl.col('DATE').dt.combine(pl.col('period')).alias('time'))
        .select(['time', 'usage'])
        .filter(pl.col('time') > pl.date(2023, 9, 10))
    )
    return dat


@jemena.command()
def daily():
    """Plot daily usage."""
    dat = get_data()
    daily = (
        dat
        .sort('time')
        .group_by_dynamic("time", every="1d")
        .agg(pl.col("usage").sum())
    )
    fig, ax = plt.subplots()
    ax.set_title('Daily usage', fontsize='medium')
    ax.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.set_ylabel('kWh/day')
    ax.plot(daily['time'], daily['usage'])
    ax.set_ylim(bottom=0)
    fig.show()
    input('Press enter to quit')


@jemena.command()
def plot():
    """Plot high frequency data."""
    fig, ax = plt.subplots()
    dat = get_data()
    ax.plot(dat['time'], dat['usage'])
    ax.set_title('Half hourly usage')
    ax.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.set_ylabel('kWh/half hour')
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.show()
    input('Press enter to quit')


@jemena.command()
def profile():
    """Plot average daily usage profile."""
    day_avg = (
        get_data()
        .with_columns(pl.col('time').dt.time())
        .group_by('time')
        .agg(pl.col('usage').mean())
        .sort('time')
    )
    fig, ax = plt.subplots()
    ax.step(day_avg['time'].dt.hour() + day_avg['time'].dt.minute()/60 + 0.25, day_avg['usage']*2)
    ax.set_xlabel('Hour of day')
    ax.set_ylabel('kW')
    ax.set_title('Average daily usage profile')
    ax.set_xlim(0, 24)
    ax.set_ylim(0, None)
    fig.tight_layout()
    fig.show()
    input('Press enter to quit')


if __name__ == '__main__':
    jemena()
