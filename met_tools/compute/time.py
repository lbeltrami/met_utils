def adjust_time(dt):
    """
    Normalize radiosonde launch times to standard synoptic hours (00 and 12 UTC).

    Radiosonde observations are not always performed exactly at 00:00 or 12:00 UTC.
    Instead, launches typically occur within time windows around these reference hours.
    This function maps the actual launch time to the corresponding synoptic time:
    - Launches between 09:00 and 15:00 UTC → mapped to 12:00 UTC (same day)
    - Launches between 21:00 and 23:59 UTC → mapped to 00:00 UTC (next day)
    Any timestamps outside these windows are considered invalid and set to NaT.

    Args:
        dt (pandas.Timestamp): Original datetime of the radiosonde launch.

    Returns:
    pandas.Timestamp or pandas.NaT
        Adjusted datetime aligned to 00 or 12 UTC, or NaT if outside valid windows.
    """

    import pandas as pd

    hour = dt.hour

    # morning launches → 12 UTC same day
    if 9 <= hour <= 15:
        return dt.normalize() + pd.Timedelta(hours=12)
    # evening launches → 00 UTC next day
    elif 21 <= hour <= 23:
        return dt.normalize() + pd.Timedelta(days=1)
    # discard non-standard launch times
    else:
        return pd.NaT