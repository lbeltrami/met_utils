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

def sond_burf_to_xr(path):
    """
    Read a BUFR radiosounding file and extract its data and metadata.
    Converts each BUFR message into one vertical profile with the following structure:

    - dim:
        - profile : index identifying each radiosounding (one per BUFR message)

    - coords:
        - pressure (Pa) : used as the vertical coordinate for all profile variables

    - data_vars (all defined along pressure):
        - airTemperature (K)
        - dewpointTemperature (K)
        - nonCoordinateGeopotentialHeight (m)
        - windDirection (deg)
        - windSpeed (m/s)

    - attrs (constant per each profile):
        - time (year, month, day, hour, minute)
        - station identifiers (blockNumber, stationNumber)
        - station geolocation (latitude, longitude)
        - station elevation (heightOfStationGroundAboveMeanSeaLevel)

    This function is absed on ECMWF's example: https://confluence.ecmwf.int/display/ECC/bufr_read_temp

    Parameters
    ----------
    path : str
        Path to the BUFR file containing radiosounding observations.

    Returns
    -------
    xr.Dataset
        A concatenated dataset of all radiosounding profiles in the file.
    """

    from eccodes import (codes_bufr_new_from_file, codes_set, codes_get,
        codes_get_array, codes_release,)
    import numpy as np
    import xarray as xr

    datasets = []

    # open BUFR file
    bufr = open(path, 'rb')

    # loop for all the messages in the file
    while 1:

        # get handle for message
        msg = codes_bufr_new_from_file(bufr)
        if msg is None:
            break

        # instruct ecCodes to unpack data
        codes_set(msg, 'unpack', 1)

        # get sounding site metadata
        year   = codes_get(msg, "year")
        month  = codes_get(msg, "month")
        day    = codes_get(msg, "day")
        hour   = codes_get(msg, "hour")
        minute = codes_get(msg, "minute")

        blockNumber   = codes_get(msg, "blockNumber")
        stationNumber = codes_get(msg, "stationNumber")

        latitude  = codes_get(msg, "latitude")
        longitude = codes_get(msg, "longitude")

        heightOfStationGroundAboveMeanSeaLevel = codes_get(
            msg, "heightOfStationGroundAboveMeanSeaLevel"
        )

        # get vertical profile values
        pressure = np.array(codes_get_array(msg, "pressure"))
        nonCoordinateGeopotentialHeight = np.array(
            codes_get_array(msg, "nonCoordinateGeopotentialHeight")
        )
        airTemperature = np.array(codes_get_array(msg, "airTemperature"))
        dewpointTemperature = np.array(codes_get_array(msg, "dewpointTemperature"))
        windDirection = np.array(codes_get_array(msg, "windDirection"))
        windSpeed = np.array(codes_get_array(msg, "windSpeed"))

        # build dataset
        ds = xr.Dataset(
            data_vars={
                "airTemperature": ("pressure", airTemperature),
                "dewpointTemperature": ("pressure", dewpointTemperature),
                "nonCoordinateGeopotentialHeight": ("pressure", nonCoordinateGeopotentialHeight),
                "windDirection": ("pressure", windDirection),
                "windSpeed": ("pressure", windSpeed),
            },
            coords={
                "pressure": ("pressure", pressure),
            },
            attrs={
                "year": year,
                "month": month,
                "day": day,
                "hour": hour,
                "minute": minute,

                "blockNumber": blockNumber,
                "stationNumber": stationNumber,

                "latitude": latitude,
                "longitude": longitude,
                "heightOfStationGroundAboveMeanSeaLevel": heightOfStationGroundAboveMeanSeaLevel,
            }
        )

        datasets.append(ds)

        # release message handle
        codes_release(msg)

    # close file
    bufr.close()

    return xr.concat(datasets, dim="profile")