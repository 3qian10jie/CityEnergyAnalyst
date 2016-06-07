
"""
Some helper functions that could be useful


"""

from __future__ import division
import math
import numpy as np
import cea.globalvar as globalvar


def hoy_2_doy(hoy):
    """
    Hour of year to day of year

    Parameters
    ----------
    hoy: hour of year

    Returns
    -------
    doy: day of year

    """

    if check_hoy(hoy):
        return int(math.floor(hoy/24)) + 1
    else:
        return None


def doy_2_hoy(doy):
    """
    Day of year to hour of year

    Parameters
    ----------
    doy: day of year

    Returns
    -------
    hoy: hour of year

    """

    if check_doy(doy):
        return doy*24
    else:
        return None


def hoy_2_woy(hoy):
    """
    Hour of year to week of year

    Parameters
    ----------
    hoy: hour of year

    Returns
    -------
    woy: weak of year

    """

    if check_hoy(hoy):
        return int(math.floor(hoy_2_doy(hoy)/7)) + 1
    else:
        return None


def hoy_2_moy(hoy):
    """
    hour of year to month of year

    Parameters
    ----------
    hoy: hour of year

    Returns
    -------
    moy: month of year

    """

    if check_hoy(hoy):

        # months_of_year = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        days_in_month = np.array([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

        return np.where(np.cumsum(days_in_month) >= hoy_2_doy(hoy))[0][0]
    else:
        return None


def hoy_2_hod(hoy):
    """
    hour of year to hour of day

    Parameters
    ----------
    hoy: hour of year

    Returns
    -------
    hod: hour of day

    """

    if check_hoy(hoy):
        return hoy % 24
    else:
        return None


def hoy_2_dom(hoy):
    """
    hour of year to day of month

    Parameters
    ----------
    hoy: hour of year

    Returns
    -------
    dom: day of month

    """

    if check_hoy(hoy):

        days_in_month = np.array([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
        doy = hoy_2_doy(hoy)
        moy = hoy_2_moy(hoy)
        return doy - np.cumsum(days_in_month)[moy] + days_in_month[moy]
    else:
        return None


def hoy_2_seasonhour(hoy):
    """
    hour of year to hour relative to start of heating season

    Parameters
    ----------
    hoy: hour of year

    Returns
    -------
    seasonhour: hour relative to start of heating season

    """

    hoy_heat_stop, hoy_heat_start = globalvar.GlobalVariables().seasonhours

    if check_hoy(hoy):
        if hoy > hoy_heat_start - 1:
            seasonhour = hoy - hoy_heat_start
        else:
            seasonhour = hoy + 8760 - hoy_heat_start

        return seasonhour

    else:
        return None


def seasonhour_2_hoy(seasonhour):
    """
    hour relative to start of heating season to hour of year

    Parameters
    ----------
    seasonhour: hour relative to start of heating season

    Returns
    -------
    hoy: hour of year

    """

    hoy_heat_stop, hoy_heat_start = globalvar.GlobalVariables().seasonhours

    if check_hoy(seasonhour):
        if seasonhour < 8760 - hoy_heat_start:
            hoy = hoy_heat_start + seasonhour
        else:
            hoy = hoy_heat_start - 8760 + seasonhour
        return hoy

    else:
        return None


def check_hoy(hoy):
    """
    check for hour of year within bounds

    Parameters
    ----------
    hoy: hour of year

    Returns
    -------
    bool

    """

    if 0 <= hoy <= 8759:
        return True
    else:
        print('Error: hour of year out of bounds')
        print(hoy)
        return False


def check_doy(doy):
    """
    check for day of year within bounds

    Parameters
    ----------
    doy: day of year

    Returns
    -------
    bool

    """

    if 0 <= doy <= 359:
        return True
    else:
        print('Error: day of year out of bounds')
        print(doy)
        return False


def test_helpers():
    """
    test helpers

    Returns
    -------

    """

    # translate hours of year to hours relative to start of heating season
    a = np.vectorize(hoy_2_seasonhour)(range(8760))
    # translate back
    b = np.vectorize(seasonhour_2_hoy)(a)
    # compare
    print(np.array_equal(range(8760), b))


if __name__ == '__main__':
    test_helpers()

