# -*- coding: utf-8 -*-
"""
============================================
Ventilation according to DIN EN 16798-7:2015
============================================ 
Created on Tue Apr 12 18:04:04 2016
@author: happle@arch.ethz.ch
Reference:
[1] Energieeffizienz von Gebäuden - Teil 7: Modul M5-1, M 5-5, M 5-6, M 5-8 –
    Berechnungsmethoden zur Bestimmung der Luftvolumenströme in Gebäuden inklusive Infiltration;
    Deutsche Fassung prEN 16798-7:2014
[2] Wärmetechnisches Verhalten von Gebäuden –
    Bestimmung der Luftdurchlässigkeit von Gebäuden –
    Differenzdruckverfahren (ISO 9972:2015);
    Deutsche Fassung EN ISO 9972:2015
"""

from __future__ import division
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from cea import inputlocator
import geopandas as gpd
import cea.globalvar
import time

gv = cea.globalvar.GlobalVariables()


# ++++ GEOMETRY ++++

# for now get geometric properties of exposed facades from the radiation file
def create_windows(df_prop_surfaces, gdf_building_architecture):
    """

    Parameters
    ----------
    df_prop_surfaces
    gdf_building_architecture

    Returns
    -------

    """
    # TODO: documentation

    # sort dataframe for name of building for default orientation generation
    # FIXME remove this in the future
    df_prop_surfaces.sort(['Name'])

    # default values
    # FIXME use real window angle in the future
    angle_window_default = 90  # (deg), 90° = vertical, 0° = horizontal

    # read relevant columns from dataframe
    free_height = df_prop_surfaces['Freeheight']
    height_ag = df_prop_surfaces['height_ag']
    length_shape = df_prop_surfaces['Shape_Leng']
    name = df_prop_surfaces['Name']

    # calculate number of exposed floors per facade
    num_floors_free_height = (free_height / 3).astype('int')  # floor heigth is 3 m
    num_windows = num_floors_free_height.sum()  # total number of windows in model, not used

    # *** experiment with structured array
    # initialize numpy structured array for results
    # array_windows = np.zeros(num_windows,
    #                          dtype={'names':['name_building','area_window','height_window_above_ground',
    #                                          'orientation_window','angle_window','height_window_in_zone'],
    #                                 'formats':['S10','f2','f2','f2','f2','f2']})

    # initialize lists for results
    col_name_building = []
    col_area_window = []
    col_height_window_above_ground = []
    col_orientation_window = []
    col_angle_window = []
    col_height_window_in_zone = []

    # for all vertical exposed facades
    for i in range(name.size):

        # generate orientation
        # TODO in the future get real orientation
        # FIXME
        if i % 4 == 0:
            orientation_default = 0
        elif i % 4 == 1:
            orientation_default = 180
        elif i % 4 == 2:
            orientation_default = 90
        elif i % 4 == 3:
            orientation_default = 270
        else:
            orientation_default = 0

        # get window-wall ratio of building from architecture geodataframe
        #win_wall_ratio = gdf_building_architecture.loc[gdf_building_architecture['Name'] == name[i]].iloc[0]['win_wall']
        win_wall_ratio = gdf_building_architecture.ix[name[i]]['win_wall']
        win_op_ratio = gdf_building_architecture.ix[name[i]]['win_op']

        # for all levels in a facade
        for j in range(num_floors_free_height[i]):
            window_area = length_shape[
                              i] * 3 * win_wall_ratio * win_op_ratio  # 3m = average floor height
            window_height_above_ground = height_ag[i] - free_height[
                i] + j * 3 + 1.5  # 1.5m = window is placed in the middle of the floor height # TODO: make heights dynamic
            window_height_in_zone = window_height_above_ground  # for now the building is one ventilation zone

            col_name_building.append(name[i])
            col_area_window.append(window_area)
            col_height_window_above_ground.append(window_height_above_ground)
            col_orientation_window.append(orientation_default)
            col_angle_window.append(angle_window_default)
            col_height_window_in_zone.append(window_height_in_zone)

    # create pandas dataframe with table of all windows
    df_windows = pd.DataFrame({'name_building': col_name_building,
                    'area_window': col_area_window,
                    'height_window_above_ground': col_height_window_above_ground,
                    'orientation_window': col_orientation_window,
                    'angle_window': col_angle_window,
                    'height_window_in_zone': col_height_window_in_zone})


    return df_windows


# ++++ GENERAL ++++


def calc_rho_air(temp_air):
    """
    Calculation of density of air according to 6.4.2.1 in [1]

    Parameters
    ----------
    temp_air : air temperature in (°C)

    Returns
    -------
    air density in (kg/m3)

    """
    # constants from Table 12 in [1]
    # TODO import from global variables
    # TODO implement dynamic air density in other functions
    rho_air_ref = 1.23  # (kg/m3)
    temp_air_ref = 283  # (K)
    temp_air += 273  # conversion to (K)

    # Equation (1) in [1]
    rho_air = temp_air_ref / temp_air * rho_air_ref
    return rho_air


def lookup_coeff_wind_pressure(height_path, class_shielding, orientation_path, slope_roof, factor_cros):
    """
    Lookup default wind pressure coefficients for air leakage paths according to B.1.3.3 in [1]

    Parameters
    ----------
    height_path
    class_shielding
    orientation_path
    slope_roof
    factor_cros

    Returns
    -------
    wind pressure coefficients (-)

    conventions
    -----------

    class_shielding = 0 : open terrain
    class_shielding = 1 : normal
    class_shielding = 2 : shielded

    orientation_path = 0 : facade facing wind
                       1 : facade not facing wind
                       2 : roof

    factor_cros = 0 : cross ventilation not possible
                = 1 : cross ventilation possible

    """

    # Table B.5 in [1]
    table_coeff_wind_pressure_cross_ventilation = np.array([[0.5, -0.7, -0.7, -0.6, -0.2],
                                                            [0.25, -0.5, -0.6, -0.5, -0.2],
                                                            [0.05, -0.3, -0.5, -0.4, -0.2],
                                                            [0.65, -0.7, -0.7, -0.6, -0.2],
                                                            [0.45, -0.5, -0.6, -0.5, -0.2],
                                                            [0.25, -0.3, -0.5, -0.4, -0.2],
                                                            [0.8, -0.7, -0.7, -0.6, -0.2]])

    # Table B.6 in [1]
    table_coeff_wind_pressure_non_cross_ventilation = np.array([0.05, -0.05, 0])

    num_paths = height_path.shape[0]
    coeff_wind_pressure = np.zeros(num_paths)

    for i in range(0, num_paths):

        if factor_cros == 1:

            if height_path[i] < 15:
                index_row = 0
            elif 15 <= height_path[i] < 50:
                index_row = 3
            elif height_path[i] >= 50:
                index_row = 6

            index_row = min(index_row + class_shielding, 6)

            if orientation_path[i] == 2:
                if slope_roof < 10:
                    index_col = 0
                elif 10 <= slope_roof <= 30:
                    index_col = 1
                elif slope_roof > 30:
                    index_col = 2
                index_col = index_col + orientation_path[i]
            elif orientation_path[i] == 0 or orientation_path[i] == 1:
                index_col = orientation_path[i]

            coeff_wind_pressure[i] = table_coeff_wind_pressure_cross_ventilation[index_row, index_col]

        elif factor_cros == 0:
            index_col = orientation_path[i]

            coeff_wind_pressure[i] = table_coeff_wind_pressure_non_cross_ventilation[index_col]

    return coeff_wind_pressure


def calc_delta_p_path(p_zone_ref, height_path, temp_zone, coeff_wind_pressure_path, u_wind_site, temp_ext):
    """
    Calculation of indoor-outdoor pressure difference at air path according to 6.4.2.4 in [1]

    Parameters
    ----------
    p_zone_ref
    height_path
    temp_zone : air temperature of ventilation zone in (°C)
    coeff_wind_pressure_path
    u_wind_site
    temp_ext

    Returns
    -------

    """

    # constants from Table 12 in [1]
    # TODO import from global variables
    g = 9.81  # (m/s2)
    rho_air_ref = 1.23  # (kg/m3)
    temp_ext_ref = 283  # (K)

    temp_zone += 273  # conversion to (K)
    temp_ext += 273  # conversion to (K)

    # Equation (5) in [1]
    p_zone_path = p_zone_ref - rho_air_ref * height_path * g * temp_ext_ref / temp_zone

    # Equation (4) in [1]
    p_ext_path = rho_air_ref * (
        0.5 * coeff_wind_pressure_path * u_wind_site ** 2 - height_path * g * temp_ext_ref / temp_ext)

    # Equation (3) in [1]
    delta_p_path = p_ext_path - p_zone_path

    return delta_p_path


# ++++ LEAKAGES ++++


def calc_qv_delta_p_ref(n_delta_p_ref, vol_building):
    """
    Calculate airflow at reference pressure according to 6.3.2 in [2]

    Parameters
    ----------
    n_delta_p_ref = air changes at reference pressure [1/h]
    vol_building = building_volume [m3]

    Returns
    -------

    """

    # Eq. (9) in [2]
    return n_delta_p_ref * vol_building


def calc_qv_lea_path(coeff_lea_path, delta_p_lea_path):
    """
    Calculate volume air flow of single leakage path according to 6.4.3.6.5 in [1]

    Parameters
    ----------
    coeff_lea_path
    delta_p_lea_path

    Returns
    -------

    """
    # default values in [1]
    # TODO reference global variables
    n_lea = 0.667  # (-), B.1.3.15 in [1]

    # Equation (64) in [1]
    qv_lea_path = coeff_lea_path * np.sign(delta_p_lea_path) * np.abs(delta_p_lea_path) ** n_lea
    return qv_lea_path


def calc_coeff_lea_zone(qv_delta_p_lea_ref):
    """
    Calculate default leakage coefficient of zone according to B.1.3.16 in [1]

    Parameters
    ----------
    qv_delta_p_lea_ref

    Returns
    -------

    """
    # default values in [1]
    # TODO reference global variables
    delta_p_lea_ref = 50  # (Pa), B.1.3.14 in [1]
    n_lea = 0.667  # (-), B.1.3.15 in [1]

    # Eq. (B.5) in [1] # TODO: Formula assumed to be wrong in [1], corrected to match Eq. (8) in [2]
    coeff_lea_zone = qv_delta_p_lea_ref / (delta_p_lea_ref ** n_lea)

    return coeff_lea_zone


def allocate_default_leakage_paths(coeff_lea_zone, area_facade_zone, area_roof_zone, height_zone):
    """
    Allocate default leakage paths according to B.1.3.17 in [1]

    Parameters
    ----------
    coeff_lea_zone
    area_facade_zone
    area_roof_zone
    height_zone

    Returns
    -------

    """

    # Equation (B.6) in [1]
    coeff_lea_facade = coeff_lea_zone * area_facade_zone / (area_facade_zone + area_roof_zone)
    # Equation (B.7) in [1]
    coeff_lea_roof = coeff_lea_zone * area_roof_zone / (area_facade_zone + area_roof_zone)

    coeff_lea_path = np.zeros(5)
    height_lea_path = np.zeros(5)
    orientation_lea_path = np.zeros(5)

    # Table B.10 in [1]
    # default leakage path 1
    coeff_lea_path[0] = 0.25 * coeff_lea_facade
    height_lea_path[0] = 0.25 * height_zone
    orientation_lea_path[0] = 0  # facade facing the wind

    # default leakage path 2
    coeff_lea_path[1] = 0.25 * coeff_lea_facade
    height_lea_path[1] = 0.25 * height_zone
    orientation_lea_path[1] = 1  # facade not facing the wind

    # default leakage path 3
    coeff_lea_path[2] = 0.25 * coeff_lea_facade
    height_lea_path[2] = 0.75 * height_zone
    orientation_lea_path[2] = 0  # facade facing the wind

    # default leakage path 4
    coeff_lea_path[3] = 0.25 * coeff_lea_facade
    height_lea_path[3] = 0.75 * height_zone
    orientation_lea_path[3] = 1  # facade not facing the wind

    # default leakage path 5
    coeff_lea_path[4] = coeff_lea_roof
    height_lea_path[4] = height_zone
    orientation_lea_path[4] = 2  # roof

    return coeff_lea_path, height_lea_path, orientation_lea_path


def calc_qm_lea(p_zone_ref, temp_zone, temp_ext, u_wind_site, dict_locals):
    """
    Calculation of leakage infiltration and exfiltration air mass flow as a function of zone indoor reference pressure

    Parameters
    ----------
    p_zone_ref
    temp_zone : air temperature in ventilation zone (°C)
    temp_ext : exterior air temperature (°C)
    u_wind_site
    dict_locals

    Returns
    -------

    """

    # get default leakage paths from locals
    coeff_lea_path = dict_locals['dict_props_nat_vent']['coeff_lea_path']
    height_lea_path = dict_locals['dict_props_nat_vent']['height_lea_path']

    # lookup wind pressure coefficients for leakage paths from locals
    coeff_wind_pressure_path = dict_locals['dict_props_nat_vent']['coeff_wind_pressure_path_lea']

    # calculation of pressure difference at leakage path
    delta_p_path = calc_delta_p_path(p_zone_ref, height_lea_path, temp_zone, coeff_wind_pressure_path, u_wind_site,
                                     temp_ext)

    # calculation of leakage air volume flow at path
    qv_lea_path = calc_qv_lea_path(coeff_lea_path, delta_p_path)

    # Eq. (65) in [1], infiltration is sum of air flows greater zero
    qv_lea_in = qv_lea_path[np.where(qv_lea_path > 0)].sum()

    # Eq. (66) in [1], exfiltration is sum of air flows smaller zero
    qv_lea_out = qv_lea_path[np.where(qv_lea_path < 0)].sum()

    # conversion to air mass flows according to 6.4.3.8 in [1]
    # Eq. (67) in [1]
    qm_lea_in = qv_lea_in * calc_rho_air(temp_ext)
    # Eq. (68) in [1]
    qm_lea_out = qv_lea_out * calc_rho_air(temp_zone)

    # print (qm_lea_in, qm_lea_out)

    return qm_lea_in, qm_lea_out


# ++++ VENTILATION OPENINGS ++++


def calc_qv_vent_path(coeff_vent_path, delta_p_vent_path):
    """
    Calculate volume air flow of single ventilation opening path according to 6.4.3.6.4 in [1]

    Parameters
    ----------
    coeff_vent_path
    delta_p_vent_path

    Returns
    -------

    """
    # default values in [1]
    # TODO reference global variables
    n_vent = 0.5  # (-), B.1.2.2 in [1]

    # Equation (60) in [1]
    qv_vent_path = coeff_vent_path * np.sign(delta_p_vent_path) * np.abs(delta_p_vent_path) ** n_vent
    return qv_vent_path


def calc_coeff_vent_zone(area_vent_zone):
    """
    Calculate air volume flow coefficient of ventilation openings of zone according to 6.4.3.6.4 in [1]

    Parameters
    ----------
    area_vent_zone

    Returns
    -------

    """

    # default values in [1]
    # TODO reference global variables
    n_vent = 0.5  # (-), B.1.2.2 in [1]
    coeff_d_vent = 0.6  # (-), B.1.2.1 in [1]
    delta_p_vent_ref = 50  # (Pa) FIXME no default value specified in standard
    # constants from Table 12 in [1]
    rho_air_ref = 1.23  # (kg/m3)

    # Eq. (61) in [1]
    coeff_vent_zone = 3600 / 10000 * coeff_d_vent * area_vent_zone * (2 / rho_air_ref) ** 0.5 * \
                      (1 / delta_p_vent_ref) ** (n_vent - 0.5)

    return coeff_vent_zone


def allocate_default_ventilation_openings(coeff_vent_zone, height_zone):
    """
    Allocate default ventilation openings according to B.1.3.13 in [1]

    Parameters
    ----------
    coeff_vent_zone
    height_zone

    Returns
    -------

    """

    # initialize
    coeff_vent_path = np.zeros(4)
    height_vent_path = np.zeros(4)
    orientation_vent_path = np.zeros(4)

    # Table B.9 in [1]
    # default leakage path 1
    coeff_vent_path[0] = 0.25 * coeff_vent_zone
    height_vent_path[0] = 0.25 * height_zone
    orientation_vent_path[0] = 0  # facade facing the wind

    # default leakage path 2
    coeff_vent_path[1] = 0.25 * coeff_vent_zone
    height_vent_path[1] = 0.25 * height_zone
    orientation_vent_path[1] = 1  # facade not facing the wind

    # default leakage path 3
    coeff_vent_path[2] = 0.25 * coeff_vent_zone
    height_vent_path[2] = 0.75 * height_zone
    orientation_vent_path[2] = 0  # facade facing the wind

    # default leakage path 4
    coeff_vent_path[3] = 0.25 * coeff_vent_zone
    height_vent_path[3] = 0.75 * height_zone
    orientation_vent_path[3] = 1  # facade not facing the wind

    return coeff_vent_path, height_vent_path, orientation_vent_path


def calc_qm_vent(p_zone_ref, temp_zone, temp_ext, u_wind_site, dict_locals):
    """
    Calculation of air flows through ventilation openings in the facade

    Parameters
    ----------
    p_zone_ref
    temp_zone : zone air temperature (°C)
    temp_ext : exterior air temperature (°C)
    u_wind_site
    dict_locals

    Returns
    -------

    """

    # get properties from locals()
    coeff_vent_path = dict_locals['dict_props_nat_vent']['coeff_vent_path']
    height_vent_path = dict_locals['dict_props_nat_vent']['height_vent_path']
    coeff_wind_pressure_path = dict_locals['dict_props_nat_vent']['coeff_wind_pressure_path_vent']

    # calculation of pressure difference at leakage path
    delta_p_path = calc_delta_p_path(p_zone_ref, height_vent_path, temp_zone, coeff_wind_pressure_path, u_wind_site,
                                     temp_ext)

    # calculation of leakage air volume flow at path
    qv_vent_path = calc_qv_vent_path(coeff_vent_path, delta_p_path)

    # Eq. (62) in [1], air flow entering through ventilation openings is sum of air flows greater zero
    qv_vent_in = qv_vent_path[np.where(qv_vent_path > 0)].sum()

    # Eq. (63) in [1], air flow entering through ventilation openings is sum of air flows smaller zero
    qv_vent_out = qv_vent_path[np.where(qv_vent_path < 0)].sum()

    # conversion to air mass flows according to 6.4.3.8 in [1]
    # Eq. (67) in [1]
    qm_vent_in = qv_vent_in * calc_rho_air(temp_ext)
    # Eq. (68) in [1]
    qm_vent_out = qv_vent_out * calc_rho_air(temp_zone)

    # print (qm_lea_in, qm_lea_out)

    return qm_vent_in, qm_vent_out


# ++++ WINDOW VENTILATION ++++

def calc_area_window_free(area_window_max, r_window_arg):
    """
    Calculate free window opening area according to 6.4.3.5.2 in [1]

    Parameters
    ----------
    area_window_max
    r_window_arg

    Returns
    -------

    """

    # default values
    # r_window_arg = 0.5  # (-), Tab 11 in [1]
    # TODO: this might be a dynamic parameter

    # Eq. (42) in [1]
    area_window_free = r_window_arg * area_window_max
    return area_window_free


def calc_area_window_tot(dict_windows_building, r_window_arg):
    """
    Calculation of total open window area according to 6.4.3.5.2 in [1]

    Parameters
    ----------
    dict_windows_building
    r_window_arg

    Returns
    -------

    """

    # Eq. (43) in [1]
    # TODO account only for operable windows and not total building window area
    area_window_tot = calc_area_window_free(sum(dict_windows_building['area_window']), r_window_arg)

    return area_window_tot


def calc_effective_stack_height(dict_windows_building):
    """
    Calculation of effective stack height for window ventilation according to 6.4.3.4.1 in [1]

    Parameters
    ----------
    dict_windows_building

    Returns
    -------

    """
    # TODO: maybe this formula is wrong --> check final edition of standard as soon as possible

    # first part of Eq. (46) in [1]
    height_window_stack_1 = dict_windows_building['height_window_in_zone'] + np.array(dict_windows_building[
                                                                               'height_window_above_ground']) / 2
    # second part of Eq. (46) in [1]
    height_window_stack_2 = dict_windows_building['height_window_in_zone'] - np.array(dict_windows_building[
                                                                               'height_window_above_ground']) / 2
    # Eq. (46) in [1]
    height_window_stack = max(height_window_stack_1) - min(height_window_stack_2)

    return height_window_stack


def calc_area_window_cros(df_windows_building, r_window_arg):
    """
    Calculate cross-ventilation window area according to the procedure in 6.4.3.5.4.3 in [1]

    Parameters
    ----------
    df_windows_building
    r_window_arg

    Returns
    -------

    """

    # initialize results
    area_window_ori = np.zeros(4)
    area_window_cros = np.zeros(2)

    # area window tot
    area_window_tot = calc_area_window_tot(df_windows_building, r_window_arg)

    for i in range(2):
        for j in range(4):

            # Eq. (51) in [1]
            alpha_ref = i * 45 + j * 90
            alpha_max = alpha_ref + 45
            alpha_min = alpha_ref - 45
            for k in range(len(df_windows_building['name_building'])):
                if alpha_min <= df_windows_building['orientation_window'][k] <= \
                        alpha_max and df_windows_building['angle_window'][k] >= 60:
                    # Eq. (52) in [1]
                    area_window_free = calc_area_window_free(df_windows_building['area_window'][k], r_window_arg)
                    area_window_ori[j] = area_window_ori[j] + area_window_free
        for j in range(4):
            if area_window_ori[j] > 0:
                # Eq. (53) in [1]
                area_window_cros[i] += 0.25 * 1 / (((1 / area_window_ori[j] ** 2) +
                                                    (1 / (area_window_tot - area_window_ori[j]) ** 2)) ** 0.5)

    # Eq. (54) in [1]
    return min(area_window_cros)


def calc_qm_arg(factor_cros, temp_ext, dict_windows_building, u_wind_10, temp_zone, r_window_arg):
    """
    Calculation of cross ventilated and non-cross ventilated window ventilation according to procedure in 6.4.3.5.4
    in [1]

    Parameters
    ----------
    factor_cros
    temp_ext : exterior temperature (°C)
    dict_windows_building
    u_wind_10
    temp_zone : zone temperature (°C)
    r_window_arg

    Returns
    -------
    window ventilation air mass flows in (kg/h)
    """

    # initialize result
    q_v_arg_in = 0
    q_v_arg_out = 0
    qm_arg_in = qm_arg_out = 0  # this is the output for buildings without windows

    # if building has windows
    if dict_windows_building:

        # constants from Table 12 in [1]
        # TODO import from global variables
        rho_air_ref = 1.23  # (kg/m3)
        coeff_turb = 0.01  # (m/s)
        coeff_wind = 0.001  # (1/(m/s))
        coeff_stack = 0.0035  # ((m/s)/(mK))

        # default values from annex B in [1]
        coeff_d_window = 0.67  # (-), B.1.2.1 in [1]
        delta_c_p = 0.75  # (-), option 2 in B.1.3.4 in [1]

        # get necessary inputs
        rho_air_ext = calc_rho_air(temp_ext)
        rho_air_zone = calc_rho_air(temp_zone)
        area_window_tot = calc_area_window_tot(dict_windows_building, r_window_arg)
        h_window_stack = calc_effective_stack_height(dict_windows_building)
        # print(h_window_stack, area_window_tot)

        # volume flow rates of non-cross ventilated zone according to 6.4.3.5.4.2 in [1]
        if factor_cros == 0:

            # Eq. (47) in [1]
            # FIXME: this equation was modified from the version in the standard (possibly wrong in preliminary version)
            # TODO: check final edition of standard as soon as possible
            q_v_arg_in = 3600 * rho_air_ref / rho_air_ext * area_window_tot / 2 * (
                coeff_turb + coeff_wind * u_wind_10 ** 2 + coeff_stack * h_window_stack * abs(
                    temp_zone - temp_ext))  # ** 0.5
            # Eq. (48) in [1]
            q_v_arg_out = -3600 * rho_air_ref / rho_air_zone * area_window_tot / 2 * (
                coeff_turb + coeff_wind * u_wind_10 ** 2 + coeff_stack * h_window_stack * abs(
                    temp_zone - temp_ext))  # ** 0.5

            # print(coeff_turb + coeff_wind * u_wind_10 ** 2 + coeff_stack * h_window_stack * abs(temp_zone - temp_ext))

        elif factor_cros == 1:

            # get window area of cross-ventilation
            area_window_cros = calc_area_window_cros(dict_windows_building, r_window_arg)
            # print(area_window_cros)

            # Eq. (49) in [1]
            q_v_arg_in = 3600 * rho_air_ref / rho_air_ext * ((
                                                                 coeff_d_window * area_window_cros * u_wind_10 * delta_c_p ** 0.5) ** 2 + (
                                                                 area_window_tot / 2 * (
                                                                 coeff_stack * h_window_stack * abs(
                                                                     temp_zone - temp_ext))) ** 2) ** 0.5

            # Eq. (50) in [1]
            # TODO this formula was changed from the standard to use the air density in the zone
            # TODO adjusted from the standard to have consistent units
            # TODO check final edition of standard as soon as possible
            q_v_arg_out = -3600 * rho_air_ref / rho_air_zone * ((
                                                                    coeff_d_window * area_window_cros * u_wind_10 * delta_c_p ** 0.5) ** 2 + (
                                                                    area_window_tot / 2 * (
                                                                        coeff_stack * h_window_stack * abs(
                                                                            temp_zone - temp_ext))) ** 2) ** 0.5

        # conversion to air mass flows according to 6.4.3.8 in [1]
        # Eq. (67) in [1]
        qm_arg_in = q_v_arg_in * calc_rho_air(temp_ext)
        # Eq. (68) in [1]
        qm_arg_out = q_v_arg_out * calc_rho_air(temp_zone)

    return qm_arg_in, qm_arg_out


# ++++ MASS BALANCE ++++

def calc_air_flow_mass_balance(p_zone_ref, temp_zone, u_wind_site, temp_ext, dict_locals, option):
    """
    Air flow mass balance for iterative calculation according to 6.4.3.9 in [1]

    Parameters
    ----------
    p_zone_ref
    temp_zone : air temperature in ventilation zone (°C)
    u_wind_site
    temp_ext : exterior air temperature (°C)
    dict_locals
    option

    Returns
    -------
    sum of air mass flows in and out of zone in (kg/h)

    """

    qm_sup_dis = 0
    qm_eta_dis = 0
    qm_lea_sup_dis = 0
    qm_lea_eta_dis = 0
    qm_comb_in = 0
    qm_comb_out = 0
    qm_pdu_in = 0
    qm_pdu_out = 0

    qm_arg_in = 0  # dict_locals['qm_arg_in'], removed to speed up code, as window ventilation is always balanced
                                                #  with the currently implemented method
    qm_arg_out = 0  # dict_locals['qm_arg_out']

    qm_vent_in, qm_vent_out = calc_qm_vent(p_zone_ref, temp_zone, temp_ext, u_wind_site, dict_locals)
    qm_lea_in, qm_lea_out = calc_qm_lea(p_zone_ref, temp_zone, temp_ext, u_wind_site, dict_locals)

    # print('iterate air flows')
    # print(qm_arg_in, qm_arg_out)
    # print(qm_vent_in, qm_vent_out)
    # print(qm_lea_in, qm_lea_out)

    # mass balance, Eq. (69) in [1]
    qm_balance = qm_sup_dis + qm_eta_dis + qm_lea_sup_dis + qm_lea_eta_dis + qm_comb_in + qm_comb_out + \
                 qm_pdu_in + qm_pdu_out + qm_arg_in + qm_arg_out + qm_vent_in + qm_vent_out + qm_lea_in + qm_lea_out
    qm_sum_in = qm_sup_dis + qm_lea_sup_dis + qm_comb_in + qm_pdu_in + qm_arg_in + qm_vent_in + qm_lea_in
    qm_sum_out = qm_eta_dis + qm_lea_eta_dis + qm_comb_out + qm_pdu_out + qm_arg_out + qm_vent_out + qm_lea_out

    # switch output according to selected option
    if option == 'minimize':
        return abs(qm_balance)  # for minimization the mass balance is the output
    elif option == 'calculate':
        return qm_sum_in, qm_sum_out  # for the calculation the total air mass flows are output


# ++++ HELPERS ++++

def get_building_geometry_ventilation(gdf_building_geometry):
    """

    Parameters
    ----------
    gdf_building_geometry : geodataframe contains single building

    Returns
    -------
    building properties for natural ventilation calculation
    """

    # TODO: get real slope of roof in the future
    slope_roof_default = 0

    area_facade_zone = gdf_building_geometry['perimeter'] * gdf_building_geometry.height_ag
    area_roof_zone = gdf_building_geometry['footprint']
    height_zone = gdf_building_geometry.height_ag
    slope_roof = slope_roof_default

    return area_facade_zone, area_roof_zone, height_zone, slope_roof


def get_properties_natural_ventilation(gdf_geometry_building, gdf_architecture_building):
    """

    Parameters
    ----------
    gdf_geometry_building

    Returns
    -------

    """

    # FIXME: for testing the scripts
    n50 = gdf_architecture_building['n50']  # 0.3  # air tight # TODO: get from building properties
    vol_building = gdf_geometry_building['footprint'] * gdf_geometry_building['height_ag']  # TODO: get from building properties
    qv_delta_p_lea_ref_zone = calc_qv_delta_p_ref(n50, vol_building)
    area_facade_zone, area_roof_zone, height_zone, slope_roof = get_building_geometry_ventilation(
        gdf_geometry_building)  # TODO: maybe also from building properties
    class_shielding = 2  # open # TODO: get from globalvars or dynamic simulation parameters or building properties
    factor_cros = gdf_architecture_building['f_cros']  # 1  # 1 = cross ventilation possible # TODO: get from building properties
    area_vent_zone = 0  # (cm2) area of ventilation openings # TODO: get from buildings properties

    # calculate properties that remain constant in the minimization
    # (a) LEAKAGES
    coeff_lea_path, height_lea_path, orientation_lea_path = allocate_default_leakage_paths(
        calc_coeff_lea_zone(qv_delta_p_lea_ref_zone),
        area_facade_zone,
        area_roof_zone, height_zone)

    coeff_wind_pressure_path_lea = lookup_coeff_wind_pressure(height_lea_path, class_shielding, orientation_lea_path,
                                                              slope_roof, factor_cros)

    # (b) VENTILATION OPENINGS
    coeff_vent_path, height_vent_path, orientation_vent_path = allocate_default_ventilation_openings(
        calc_coeff_vent_zone(area_vent_zone),
        height_zone)
    coeff_wind_pressure_path_vent = lookup_coeff_wind_pressure(height_vent_path, class_shielding, orientation_vent_path,
                                                               slope_roof, factor_cros)

    # make dict for output
    dict_props_nat_vent = {'coeff_lea_path': coeff_lea_path,
                           'height_lea_path': height_lea_path,
                           'coeff_wind_pressure_path_lea': coeff_wind_pressure_path_lea,
                           'coeff_vent_path': coeff_vent_path,
                           'height_vent_path': height_vent_path,
                           'coeff_wind_pressure_path_vent': coeff_wind_pressure_path_vent}

    return dict_props_nat_vent


def calc_air_flows(temp_zone, u_wind, temp_ext, dict_locals):
    """
    Minimization of variable air flows as a function of zone gauge

    Parameters
    ----------
    temp_zone : zone indoor air temperature (°C)
    u_wind
    temp_ext : exterior air temperature (°C)
    dict_locals

    Returns
    -------

    """
    # solver_options_nelder_mead ={'disp': False, 'maxiter': 100, 'maxfev': None, 'xtol': 0.1, 'ftol': 0.1}
    # solver_options_cg ={'disp': False, 'gtol': 1e-05, 'eps': 1.4901161193847656e-08, 'return_all': False,
    #                     'maxiter': None, 'norm': -np.inf}
    # solver_options_powell = {'disp': True, 'maxiter': None, 'direc': None, 'maxfev': None,
    #            'xtol': 0.0001, 'ftol': 0.0001}
    # solver_options_tnc = {'disp': True, 'minfev': 0, 'scale': None, 'rescale': -1, 'offset': None, 'gtol': -1,
    #                       'eps': 1e-08, 'eta': -1, 'maxiter': None, 'maxCGit': -1, 'mesg_num': None,
    #                       'ftol': -1, 'xtol': -1, 'stepmx': 0, 'accuracy': 0}
    solver_options_cobyla = {'iprint': 1, 'disp': False, 'maxiter': 100, 'rhobeg': 1.0, 'tol': 0.001}

    # solve air flow mass balance via iteration
    p_zone_ref = 1  # (Pa) zone pressure, THE UNKNOWN VALUE
    res = minimize(calc_air_flow_mass_balance, p_zone_ref,
                   args=(temp_zone, u_wind, temp_ext, dict_locals, 'minimize',),
                   method='COBYLA',
                   options=solver_options_cobyla)
    # print(res)
    # get zone pressure of air flow mass balance
    p_zone = res.x

    # calculate air flows at zone pressure
    qm_sum_in, qm_sum_out = calc_air_flow_mass_balance(p_zone, temp_zone, u_wind,
                                                       temp_ext, dict_locals, 'calculate')

    return qm_sum_in, qm_sum_out


def get_windows_of_building(dataframe_windows, name_building):
    return dataframe_windows.loc[dataframe_windows['name_building'] == name_building]


def testing():
    # generate windows based on geometry of vertical surfaces in radiation file
    locator = inputlocator.InputLocator(scenario_path=r'C:\reference-case\baseline')

    df_radiation = pd.read_csv(locator.get_radiation())
    gdf_building_architecture = gpd.GeoDataFrame.from_file(locator.get_building_architecture())
    gdf_building_geometry = gpd.GeoDataFrame.from_file(locator.get_building_geometry())
    df_windows = create_windows(df_radiation, gdf_building_architecture)

    building_test = 'B153737'  # 'B154767' this building doesn't have windows
    # get building windows
    df_windows_building_test = get_windows_of_building(df_windows, building_test)
    # get building geometry
    gdf_building_test = gdf_building_geometry.loc[gdf_building_geometry['Name'] == building_test]

    r_window_arg = 0
    temp_ext = 5
    temp_zone = 22
    u_wind = 0.5
    u_wind_10 = u_wind
    factor_cros = 1  # 1 = cross ventilation possible # TODO: get from building properties

    dict_props_nat_vent = get_properties_natural_ventilation(gdf_building_test)
    qm_arg_in, qm_arg_out \
        = calc_qm_arg(factor_cros, temp_ext, df_windows_building_test, u_wind_10, temp_zone, r_window_arg)

    t0 = time.time()
    res = calc_air_flows(temp_zone, u_wind, temp_ext, locals())
    t1 = time.time()

    print(res)
    print(['time: ', t1 - t0])


# TESTING
if __name__ == '__main__':
    testing()
