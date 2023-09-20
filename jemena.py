#!./.venv/bin/python3

import requests
import configparser
import os
import click
import polars as pl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np


def get_config():
    config = configparser.ConfigParser()
    config.read(os.path.expanduser('~/.jemenarc'))
    return config

@click.group()
def jemena():
    """Tool for downloading electricity usage data from Jemena."""
    pass

@jemena.command()
def update():
    """Fetch latest data from Jemena."""
    config = get_config()
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
    config = get_config()
    start_param = [int(s) for s in config.get('DEFAULT', 'start_date').split('-')]
    start_date = pl.date(*start_param)
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
        .filter(pl.col('time') >= start_date)
    )
    return dat


def get_tariff():
    config = get_config()
    rate_ckW = float(config.get('DEFAULT', 'rate_ckw'))
    daily_c = float(config.get('DEFAULT', 'daily_c'))
    return rate_ckW, daily_c


@jemena.command()
def daily():
    """Plot daily usage."""
    rate_ckW, daily_c = get_tariff()
    dat = get_data()
    daily = (
        dat
        .sort('time')
        .group_by_dynamic("time", every="1d")
        .agg(pl.col("usage").sum())
    )
    fig, axes = plt.subplots(1, 2, sharex=True)
    usage, cost = axes
    usage.set_title('Daily usage', fontsize='medium')
    usage.set_ylabel('kWh/day')
    usage.plot(daily['time'], daily['usage'])
    usage.set_ylim(bottom=0)

    cost.set_title('Daily cost', fontsize='medium')
    cost.set_ylabel('$/day')
    bars = {
        'Service': np.repeat(daily_c/100, len(daily['time'])),
        'Usage': np.array(daily['usage']*rate_ckW/100),
    }
    bottom = np.zeros(len(daily['time']))
    for lbl, weight_count in bars.items():
        p = cost.bar(daily['time'], weight_count, label=lbl, bottom=bottom)
        bottom += weight_count
    cost.legend()
    cost.set_ylim(bottom=0)
    
    for ax in axes:
        ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(cost.xaxis.get_major_locator()))

    fig.tight_layout()
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
    data = get_data()
    yesterday = data['time'].dt.date().max()
    day_avg = (
        data
        .filter(pl.col('time').dt.date() != yesterday)
        .with_columns(pl.col('time').dt.time())
        .group_by('time')
        .agg(pl.col('usage').mean())
        .sort('time')
    )
    ye_u = (
        data
        .filter(pl.col('time').dt.date() == yesterday)
        .sort('time')
    )
    fig, ax = plt.subplots()
    ax.step(day_avg['time'].dt.hour() + day_avg['time'].dt.minute()/60 + 0.25,
            day_avg['usage']*2,
            label='Average')
    ax.step(ye_u['time'].dt.hour() + ye_u['time'].dt.minute()/60 + 0.25,
            ye_u['usage']*2,
            linestyle='--',
            label=yesterday.strftime('%a %d %b'))
    ax.set_xlabel('Hour of day')
    ax.set_ylabel('Average power usage kW')
    ax.set_title('Average daily usage profile')
    ax.set_xlim(0, 24)
    ax.set_ylim(0, None)
    ax.legend(frameon=False)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    fig.tight_layout()
    fig.show()
    input('Press enter to quit')


if __name__ == '__main__':
    jemena()
