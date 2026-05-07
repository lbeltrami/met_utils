def virtual_potential_temperature(p, T, Td):
    """
    Compute virtual potential temperature from pressure, air temperature and dew point temperature.

    Parameters
    ----------
    p : array-like
        Pressure (Pa)
    T : array-like
        Air temperature (K)
    Td : array-like
        Dew point temperature (K)

    Returns
    -------
    array-like
        Virtual potential temperature (K)
    """

    import numpy as np

    # calculate potential temperature
    theta = T * (100000.0 / p) ** 0.286

    # calculate mixing ratio
    q = mixing_ratio_from_dewpoint(p, Td)

    return theta * (1 + 0.61 * q)

# ----------------------------------------------------------------------------

def mixing_ratio_from_dewpoint(p, Td):
    """
    Compute water vapor mixing ratio from pressure and dew point temperature.

    Parameters
    ----------
    p : array-like
        Pressure (Pa)
    Td : array-like
        Dew point temperature (K)

    Returns
    -------
    array-like
        Mixing ratio (kg/kg)
    """

    import numpy as np

    # calculate water pressure using Magnus-Tetens formula (hPa)
    e = 6.1094 * np.exp((17.625 * (Td - 273.15)) / ((Td - 273.15) + 243.04))

    # convert from hPa to Pa
    e = e * 100.0

    return 0.622 * e / (p - e)