import datetime
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from astropy.table import Table
from astropy.time import Time


def major_minor_gridlines(ax: plt.Axes):

    ax.grid(which = 'major', color='#CCCCCC', ls='--')
    ax.grid(which = 'minor', color='#CCCCCC', ls=':')


def concisedateformat(ax: plt.Axes, minute_interval: int = None):

    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    if minute_interval is not None:
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=minute_interval))


# def round_seconds(time: datetime.datetime) -> datetime.datetime:
#     """
#     https://stackoverflow.com/a/49309848
#     """

#     if obj.microsecond >= 500_000:
#         obj += datetime.timedelta(seconds=1)

#     return obj.replace(microsecond=0)


def read_log() -> Table:
    
    file = './toggle_log.csv'
    data = Table.read(file, format='csv')
    data.rename_column(data.colnames[0], 'time')
    data.rename_column(data.colnames[1], 'state')
    data['time'] = Time(data['time'])

    return data


def plot_pps() -> plt.Axes:

    fig, ax = plt.subplots(figsize=(12,6), layout='constrained')

    data = read_log()
    inds = data['state'] == 0
    dt = data['time'][inds].datetime
    offset = np.array([d.microsecond for d in dt]) / 1000

    inds = offset > 500
    offset[inds] = offset[inds] - 1000

    ax.plot(dt, offset, c='blue')
    ax.axhline(0, c='gray', ls='--')
    ax.set(
        ylabel='PPS offset from nearest RTC second [millisecond]'
    )

    concisedateformat(ax, minute_interval=1)
    major_minor_gridlines(ax)

    plt.savefig('pps_offset.png', dpi=200)
    plt.show()

    return ax


def main():
    
    plot_pps()


if __name__ == '__main__':
    main()