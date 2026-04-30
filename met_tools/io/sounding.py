def sond_download_bufr(output_path, start, end, sta=None):
    """
    Download radiosonde BUFR data from  SIMC-Arkimet (http://arkimet.metarpa:8090).

    This function queries the Arkimet database and downloads BUFR-format
    radiosonde observations for Italian stations over a specified time period.
    An optional station filter can be applied using the last three digits
    of the WMO station ID.

    Parameters
    ----------
    output_path : str
        Path where the BUFR file will be saved.
    start : str
        Start date in YYYY-MM-DD format.
    end : str
        End date in YYYY-MM-DD format.
    sta : int or str or None, optional
        Last three digits of the WMO station ID (e.g. 144 for 16144).
        If None, all stations are downloaded.
    Returns
    -------
    None
    """

    import subprocess

    # Validate station filter
    if sta is not None:
        if isinstance(sta, (int, str)):
            sta = str(sta)

            if not sta.isdigit():
                raise ValueError("sta must contain only digits (e.g. 144)")

        else:
            raise TypeError("sta must be int, str, or None")

    # Italian stations have WMO IDs as 16nnn
    query = f"reftime:>={start},<={end}; proddef:GRIB:blo=16"

    if sta is not None:
        query += f",sta={sta}"

    # Run arkimet query to download the BUFR data
    cmd = [
        "arki-query",
        "--data",
        "-o", output_path,
        query,
        "http://arkimet.metarpa:8090/dataset/gts_temp"
    ]

    subprocess.run(cmd, check=True)

# --------------------------------------------------------------------------------------

def sond_bufr_to_df(file_path):
    """
    Read radiosonde BUFR data into a pandas DataFrame.

    This function extracts standard meteorological variables from a BUFR file
    using ECMWF's pdbufr library.

    Parameters
    ----------
    file_path : str
        Path to the BUFR file.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing radiosonde profiles with meteorological variables.
    """

    import pdbufr
    import pandas as pd

    columns = (
        "latitude", "longitude", "WMO_station_id", "data_datetime",
        "pressure", "airTemperature", "dewpointTemperature",
        "windDirection", "windSpeed"
    )

    df = pdbufr.read_bufr(file_path, columns=columns)

    return df

