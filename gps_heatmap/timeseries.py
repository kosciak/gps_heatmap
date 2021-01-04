import bisect
import collections


"""Simple timeseries for grouping values by year, quarter, month, week, day."""


def all_group(date):
    return None

def year_group(date):
    return (date.year, )

def quarter_group(date):
    return (date.year, (date.month-1)/3+1)

def month_group(date):
    return (date.year, date.month)

def week_group(date):
    year, week, weekday = date.isocalendar()
    return (year, week)

def day_group(date):
    return (date.year, date.month, date.day)


class Timeseries(object):

    """Keeps values sorted by date."""

    def __init__(self):
        self._dates = []
        self._values = collections.defaultdict(list)

    def add(self, date, value):
        index = bisect.bisect_left(self._dates, date)
        if not (len(self._dates) > index and self._dates[index] == date):
            self._dates.insert(index, date)
        self._values[date].append(value)

    def __len__(self):
        return sum(len(values) for values in self._values.values())

    def __iter__(self):
        for date in self._dates:
            for value in self._values[date]:
                yield value

    def _grouped_values(self, group_func=None):
        if not group_func:
            yield None, self
        values = []
        prev_group = None
        for date in self._dates:
            group = group_func(date)
            if prev_group and not group == prev_group:
                yield prev_group, values
                values = []
            for value in self._values[date]:
                values.append(value)
            prev_group = group
        if values:
            yield prev_group, values

    @property
    def all(self):
        return self._grouped_values(all_group)

    @property
    def yearly(self):
        return self._grouped_values(year_group)

    @property
    def quarterly(self):
        return self._grouped_values(quarter_group)

    @property
    def monthly(self):
        return self._grouped_values(month_group)

    @property
    def weekly(self):
        return self._grouped_values(week_group)

    @property
    def daily(self):
        return self._grouped_values(day_group)

