def extract_points_1D(da, var, time_var, locations, source = None):
    """
    Extract data values at specific coordinates from an xarray.DataArray
    e.g. a GRIB or NetCDF file that has been already opened with xarray.open_dataset.

    The label "1D" means that lat/lon coordinates are 1-dimensional arrays, instead of
    being 2-dimensional arrays (e.g. NetCDF usually report latitude as 
    a 2D field with dims (west_east, sout_north)).

    Args:
        da (xarray.DataArray): a DataArray object with 
                                dimensions 'latitude', 'longitude' and attribute 'time'.
        var (str): Name of the variable to extract. BE AWARE: it does not necessarly coincide with
                    the shortName. Thus use 'da.variables' to check the name of the variables in the file.  
        time_var (str): Name of the date_time variable in the DataArray.
        locations (dict): Dictionary with names and coordinates of locations of interest stored as: 
                            {'Name1': {'lat'0 xx, 'lon': yy}, 'Name2': {'lat': xx, 'lon': yy}, ...}.
        source (str): String reporting what is the source of the data e.g. 
                        'Model ...', 'Instrument ...'.

    Returns:
        pandas.DataFrame: a DataFrame long-structured with columns: 
                            ['time', 'location', 'source', 'variable', 'value'].
    """

    import numpy as np
    import pandas as pd

    records = []

    da = da[var]

    if isinstance(time_var, str) and time_var in da.coords:
        time_val = da[time_var].values.item()
    else:
        time_val = time_var.item() if hasattr(time_var, "item") else time_var

    for name, coords in locations.items():

        value = da.sel( 
            latitude=coords['lat'], 
            longitude=coords['lon'], 
            method='nearest'
        ).values.item()

        records.append({
            'time': time_val,
            'location': name,
            'source': source,
            'variable': var,
            'value': value
        })

    return pd.DataFrame(records)

# ---------------------------------------------------------------------------------------------------

def extract_points_2D(ds, var, time_var, locations, source = None):
    """
    Extract data values at specific coordinates from an xarray.Dataset
    e.g. a NetCDF file that has been already opened with xarray.open_dataset.

    The label "2D" means that lat/lon coordinates are 2-dimensional arrays, e.g. 
    NetCDF usually report latitude as a 2D field with dims (west_east, sout_north).

    Args:
        ds (xarray.Dataset): Dataset with dims ['Time', 'south_north', 'west_east']. 
        locations (dict): Dictionary with names and coordinates of locations of interest stored as: 
                            {'Name1': {'lat'0 xx, 'lon': yy}, 'Name2': {'lat': xx, 'lon': yy}, ...}.
        var (str): Name of the variable to extract.
        time_var (str): Name of the date_time variable in the DataArray.
        source (str): String reporting what is the source of the data e.g. 
                        'Model ...', 'Instrument ...'.
    Returns:
        pandas.DataFrame: a DataFrame long-structured with columns: 
                            ['time', 'location', 'source', 'variable', 'value'].
    """
    
    import numpy as np
    import pandas as pd

    ds_lat = ds["lat"].values
    ds_lon = ds["lon"].values
    ds_times = ds[time_var].values
    
    data = ds[var]

    records = []

    for t_idx, tval in enumerate(ds_times):
        for name, coords in locations.items():

            target_lat = coords['lat']
            target_lon = coords['lon']

            dist_sq = (ds_lat - target_lat)**2 + (ds_lon - target_lon)**2
            i, j = np.unravel_index(np.argmin(dist_sq), dist_sq.shape)

            value = data.isel(**{"Time": t_idx, "south_north": i, "west_east": j}).values.item()

            records.append({
                'time': tval,
                'location': name,
                'source': source,
                'variable': var,
                'value': value
            })

    return pd.DataFrame(records)