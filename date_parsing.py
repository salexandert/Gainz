import datetime

from dateutil import parser


GAINZ_TZINFOS = {
    "UTC": 0,
    "GMT": 0,
    "EST": -5 * 3600,
    "EDT": -4 * 3600,
    "CST": -6 * 3600,
    "CDT": -5 * 3600,
    "MST": -7 * 3600,
    "MDT": -6 * 3600,
    "PST": -8 * 3600,
    "PDT": -7 * 3600,
}


def parse_gainz_datetime(value, **kwargs):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value

    tzinfos = dict(GAINZ_TZINFOS)
    tzinfos.update(kwargs.pop("tzinfos", {}) or {})
    return parser.parse(value, tzinfos=tzinfos, **kwargs)
