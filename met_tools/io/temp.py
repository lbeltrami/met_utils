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

# --------------------------------------------------------------------------------------

def sond_bufr_to_xr(path, verbose=False):
    """
    Read a BUFR radiosounding file and extract its data and metadata.
    Converts each BUFR message into one vertical profile with the following structure:

    - data_vars:
        - pressure (Pa)
        - nonCoordinateGeopotentialHeight (m^2 / s^2)     !!! units to be verified !!!
        - airTemperature (K)
        - dewpointTemperature (K)
        - windDirection (deg)
        - windSpeed (m/s)
    
    - coords:
        - level : index of the profile's vertical level

    - attrs:
        - date and time (year, month, day, hour, minute)
        - station identifiers (WMO_station_id, blockNumber, stationNumber)
        - station geolocation (latitude, longitude)
        - station elevation (heightOfStationGroundAboveMeanSeaLevel)

    This function is based on ECMWF's example: https://confluence.ecmwf.int/display/ECC/bufr_read_temp
    and is designed for compliancy with xarray workflows.

    Parameters
    ----------
    path : str
        Path to the BUFR file containing radiosounding observations.
    verbose : bool
        If True, prints station ID and datetime for each profile (default = False).

    Returns
    -------
    list of xr.Dataset
        A list where each element is an xarray Dataset representing a single radiosounding profile.
    """

    from eccodes import (codes_bufr_new_from_file, codes_set, codes_get,
        codes_get_array, codes_release)
    from datetime import datetime
    import numpy as np
    import xarray as xr

    profiles = []

    # open BUFR file
    bufr = open(path, 'rb')

    if verbose is True:
        print("File opened ...")

    # loop for all the messages in the file
    while True:

        # get handle for message
        msg = codes_bufr_new_from_file(bufr)
        if msg is None:
            break

        # instruct ecCodes to unpack data
        codes_set(msg, 'unpack', 1)

        # get sounding site metadata
        year = int(codes_get(msg, "year"))
        month = int(codes_get(msg, "month"))
        day = int(codes_get(msg, "day"))
        hour = int(codes_get(msg, "hour"))
        minute = int(codes_get(msg, "minute"))

        date_time = datetime(year, month, day, hour, minute) # costum var for dt

        blockNumber   = codes_get(msg, "blockNumber")
        stationNumber = codes_get(msg, "stationNumber")

        WMO_station_id = f"{blockNumber:02d}{stationNumber:03d}" # costum var for WMO code

        latitude  = codes_get(msg, "latitude")
        longitude = codes_get(msg, "longitude")

        heightOfStationGroundAboveMeanSeaLevel = codes_get(
            msg, "heightOfStationGroundAboveMeanSeaLevel"
        )

        # get vertical profile values by reading every single level
        pressure = []
        vars_ = {
            "nonCoordinateGeopotentialHeight": [],
            "airTemperature": [],
            "dewpointTemperature": [],
            "windDirection": [],
            "windSpeed": [],
        }
        
        i = 1

        while True:
            try:
                pressure.append(codes_get(msg, f"#{i}#pressure"))
            except:
                break  # no more levels

            for varname in vars_:
                try:
                    vars_[varname].append(codes_get(msg, f"#{i}#{varname}"))
                except:
                    vars_[varname].append(np.nan)

            i += 1

        pressure = np.array(pressure)
        nonCoordinateGeopotentialHeight = np.array(vars_["nonCoordinateGeopotentialHeight"])
        airTemperature = np.array(vars_["airTemperature"])
        dewpointTemperature = np.array(vars_["dewpointTemperature"])
        windDirection = np.array(vars_["windDirection"])
        windSpeed = np.array(vars_["windSpeed"])

        # build the dataset
        ds = xr.Dataset(
            data_vars={
                "pressure": ("level", pressure),
                "nonCoordinateGeopotentialHeight": ("level", nonCoordinateGeopotentialHeight),
                "airTemperature": ("level", airTemperature),
                "dewpointTemperature": ("level", dewpointTemperature),
                "windDirection": ("level", windDirection),
                "windSpeed": ("level", windSpeed),
            },
            coords={
                "level": np.arange(len(pressure)),
            },
            attrs={
                "datetime": date_time,
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": minute,

                "WMO_station_id": WMO_station_id,
                "blockNumber": blockNumber,
                "stationNumber": stationNumber,

                "latitude": latitude,
                "longitude": longitude,
                "heightOfStationGroundAboveMeanSeaLevel": heightOfStationGroundAboveMeanSeaLevel,
            }
        )

        profiles.append(ds)
        codes_release(msg)

        if verbose:
            print("WMO_station_id: ", WMO_station_id, " --- date_time: ", date_time)
        
    bufr.close()

    return profiles

def dba_bufr_to_df(path):
    """
    Read a BUFR radiosounding file and extract its data and metadata using
    the dballe library (https://github.com/ARPA-SIMC/dballe).
    """

    import dballe
    import pandas as pd

    # connect to in-memory database to import the BUFR file
    db = dballe.DB.connect("mem:")
    importer = dballe.Importer("BUFR")

    with open(path, "r") as file:
        with importer.from_file(file) as f:
            for msgs in f:
                with db.transaction() as tr:
                    for message in msgs:
                        tr.import_messages(message,overwrite=True, update_station=True,import_attributes=True)

    # query the database to extract all profiles and their metadata into a DataFrame
    records = []

    with db.transaction() as tr:

        for srow in tr.query_stations():
            ana_id = srow["ana_id"]

            # station metadata
            station_meta = {}
            for mrow in tr.query_station_data({"ana_id": ana_id}):
                v = mrow["variable"]
                station_meta[v.code] = v.enqd()

            # observations
            for row in tr.query_data({"ana_id": ana_id}):

                var = row["variable"]
                level = row["level"]
                trange = row["trange"]

                records.append({
                    "ana_id": ana_id,
                    "station": srow["station"],
                    "datetime": row["datetime"],
                    "level": level.l1 if level else None,
                    "var_code": var.code,
                    "var_desc": var.info.desc,
                    "value": var.enqd(),
                    **station_meta,
                })

    return pd.DataFrame(records)