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

# ----------------------------------------------------------------------------

def virtual_potential_temperature(p, T, Td):
    """
    Compute virtual potential temperature from 
    pressure, air temperature and dew point temperature.

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

def hydrostatic_height(p, T, Td):
    """
    Compute geometric height from a vertical atmospheric profile
    using the hydrostatic (hypsometric) equation.
    The integration is performed layer-by-layer starting from
    the surface upward.

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
        Geometric height profile (m)
    """

    import numpy as np

    Rd = 287.05
    g = 9.80665

    # mixing ratio
    q = mixing_ratio_from_dewpoint(p, Td)

    # virtual temperature
    Tv = T * (1.0 + 0.61 * q)

    # initialize height array
    z = np.zeros(len(p))

    # integrate hydrostatic equation
    for k in range(1, len(p)):

        # layer-mean virtual temperature
        Tv_mean = 0.5 * (Tv[k] + Tv[k - 1])

        # hypsometric equation
        z[k] = z[k - 1] + (Rd / g) * Tv_mean * np.log(p[k - 1] / p[k])

    return z