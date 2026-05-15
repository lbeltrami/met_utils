def sond_download_bufr(output_path, start, end, blo=16, sta=None):
    """
    Download radiosonde BUFR data from  SIMC-Arkimet (http://arkimet.metarpa:8090)
    using arki-query Bash function (https://arpa-simc.github.io/arkimet/)

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
    blo : int or str, optional
        WMO block number (default = 16, which is Italy)
    sta : int or str or None, optional
        WMO station number. If None, all country's stations are taken.
    Returns
    -------
    None
    """

    import subprocess

    # validate station filter
    if sta is not None:
        if isinstance(sta, (int, str)):
            sta = str(sta)
            if not sta.isdigit():
                raise ValueError("sta must contain only digits (e.g. 144)")
        else:
            raise TypeError("sta must be int, str, or None")

    # compose the arki-query
    query = f"reftime:>={start},<={end}; proddef:GRIB:blo={blo}"
    if sta is not None:
        query += f",sta={sta}"

    # Run arki-query to download the BUFR data from Arkimet
    cmd = [
        "arki-query",
        "--data",
        "-o", output_path,
        query,
        "http://arkimet.metarpa:8090/dataset/gts_temp"
    ]

    subprocess.run(cmd, check=True)


def dba_bufr_to_df(path):
    """
    Convert BUFR radiosounding data into a structured pandas DataFrame
    using dballe (https://github.com/ARPA-SIMC/dballe).

    This function reads a BUFR file containing upper-air soundings,
    extracts both station metadata and vertical profile observations,
    and reorganizes them into a flat tabular structure where each row 
    corresponds to a single vertical level of a sounding profile.

    COLUMNS:
        WMO_block            : WMO block number (-)
        WMO_station          : WMO station identifier (-)
        latitude             : station latitude (deg)
        longitude            : station longitude (deg)
        station_height_amsl  : station elevation above mean sea level (m)
        datetime             : launch date-time UTC
        level                : vertical level identifier, based on pressure
        pressure             : pressure (Pa)
        geopotential         : geopotential (m² s⁻²)
        temperature          : temperature (K)
        dewpoint_temperature : dew point temperature (K)
        wind_speed           : wind speed (m s⁻¹)
        wind_direction       : wind direction (degrees)

    Parameters
    ----------
    path : str
        Path to the BUFR file.
    Returns
    -------
    pandas.DataFrame
        A DataFrame containing the converted data.
    """

    import dballe
    import pandas as pd

    BUFR_CODES = {
        # WMO - BUFR Table B codes for station metadata
        "B01001": "WMO_block",
        "B01002": "WMO_station",
        "B05001": "latitude",
        "B06001": "longitude",
        "B07030": "station_height_amsl",

        # WMO - BUFR Table B codes for profile variables
        "B10004": "pressure",
        "B10008": "geopotential",
        "B12101": "temperature",
        "B12103": "dewpoint_temperature",
        "B11001": "wind_direction",
        "B11002": "wind_speed",
    }

    # connect to in-memory database to import the BUFR file
    db = dballe.DB.connect("mem:")
    importer = dballe.Importer("BUFR")

    with open(path, "r") as file:
        with importer.from_file(file) as f:
            for msgs in f:
                with db.transaction() as tr:
                    for message in msgs:
                        tr.import_messages(message,overwrite=True, update_station=True,import_attributes=True)

    # query the in-memory database to get all the data in a DataFrame
    records = []
    with db.transaction() as tr:

        for srow in tr.query_stations():
            ana_id = srow["ana_id"]

            # station metadata
            station_meta = {}
            for row in tr.query_station_data({"ana_id": ana_id}):
                var = row["variable"]
                name = BUFR_CODES.get(var.code, var.code)
                # skip some useless variables e.g. characteristics of the sond
                if name is not None:
                    station_meta[name] = var.enqd()
 
            WMO_block = int(station_meta.get("WMO_block"))
            WMO_station = int(station_meta.get("WMO_station"))

            # observations
            for row in tr.query_data({"ana_id": ana_id}):

                var = row["variable"]
                var_name = BUFR_CODES.get(var.code)
                # skip some useless variables e.g. lat/lon displacement 
                if var_name is None:
                    continue

                level_obj = row["level"]
                level = level_obj.l1 if level_obj else None
                
                records.append({
                    "WMO_block": WMO_block,
                    "WMO_station": WMO_station,
                    "latitude": station_meta.get("latitude"),
                    "longitude": station_meta.get("longitude"),
                    "station_height_amsl": station_meta.get("station_height_amsl"),
                    "datetime": row["datetime"],
                    "level": level,
                    "var_name": var_name,
                    "value": var.enqd()
                })

    # build dataframe
    df = pd.DataFrame(records)
    df = df.pivot_table(
        index=["WMO_block", "WMO_station", "datetime", "latitude", "longitude",
            "station_height_amsl", "level"],
        columns="var_name",
        values="value"
    ).reset_index()

    return df