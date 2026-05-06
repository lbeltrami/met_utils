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

    # calculate water pressure using Magnus-Tetens formula
    e = 6.1094 * np.exp((17.625 * (Td - 273.15)) / ((Td - 273.15) + 243.04))
    
    # convert from Pa to hPa
    e = e * 100.0

    # calculate mixing ratio
    q = 0.622 * e / (p - e)

    # calculate virtual potential temperature
    return theta * (1 + 0.61 * q)