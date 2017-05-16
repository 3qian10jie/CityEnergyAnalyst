"""
building properties algorithm
"""

# HISTORY:
# J. A. Fonseca  script development          22.03.15

from __future__ import division
from __future__ import absolute_import

import numpy as np
import pandas as pd
from cea.utilities.dbfreader import dbf2df, df2dbf

import cea.inputlocator

__author__ = "Jimeno A. Fonseca"
__copyright__ = "Copyright 2015, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Jimeno A. Fonseca", "Daren Thomas"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


def properties(locator, prop_architecture_flag, prop_hvac_flag, prop_comfort_flag, prop_internal_loads_flag):
    """
    algorithm to query building properties from statistical database
    Archetypes_HVAC_properties.csv. for more info check the integrated demand
    model of Fonseca et al. 2015. Appl. energy.

    :param InputLocator locator: an InputLocator instance set to the scenario to work on
    :param boolean prop_architecture_flag: if True, get properties about the construction and architecture.
    :param boolean prop_comfort_flag: if True, get properties about thermal comfort.
    :param boolean prop_hvac_flag: if True, get properties about types of HVAC systems, otherwise False.
    :param boolean prop_internal_loads_flag: if True, get properties about internal loads, otherwise False.

    The following files are created by this script, depending on which flags were set:

    - building_HVAC: .dbf
        describes the queried properties of HVAC systems.

    - architecture.dbf
        describes the queried properties of architectural features

    - building_thermal: .shp
        describes the queried thermal properties of buildings

    - indoor_comfort.shp
        describes the queried thermal properties of buildings
    """

    # get occupancy and age files
    building_occupancy_df = dbf2df(locator.get_building_occupancy())
    list_uses = list(building_occupancy_df.drop(['PFloor', 'Name'], axis=1).columns) #parking excluded in U-Values
    building_age_df = dbf2df(locator.get_building_age())

    # prepare shapefile to store results (a shapefile with only names of buildings
    names_df = building_age_df[['Name']]

    # define main use:
    building_occupancy_df['mainuse'] = calc_mainuse(building_occupancy_df, list_uses)

    # dataframe with jonned data for categories
    categories_df = building_occupancy_df.merge(building_age_df, on='Name')

    # get properties about the construction and architecture
    if prop_architecture_flag:
        architecture_DB = get_database(locator.get_archetypes_properties(), 'ARCHITECTURE')
        architecture_DB['Code'] = architecture_DB.apply(lambda x: calc_code(x['building_use'], x['year_start'],
                                                                            x['year_end'], x['standard']),axis=1)
        categories_df['cat_architecture'] = calc_category(architecture_DB, categories_df)

        prop_architecture_df = categories_df.merge(architecture_DB, left_on='cat_architecture', right_on='Code')

        # adjust 'Hs' and 'Es' for multiuse buildings
        prop_architecture_df['Hs'], prop_architecture_df['Es'] = \
            correct_archetype_areas(prop_architecture_df, architecture_DB, list_uses)

        # write to shapefile
        prop_architecture_df_merged = names_df.merge(prop_architecture_df, on="Name")
        fields = ['Name', 'Hs', 'win_wall', 'type_cons', 'type_leak',  'type_roof', 'type_wall', 'type_win', 'type_shade']
        df2dbf(prop_architecture_df_merged[fields], locator.get_building_architecture())


    # get properties about types of HVAC systems
    if prop_hvac_flag:
        HVAC_DB = get_database(locator.get_archetypes_properties(), 'HVAC')
        HVAC_DB['Code'] = HVAC_DB.apply(lambda x: calc_code(x['building_use'], x['year_start'],
                                                            x['year_end'], x['standard']),axis=1)

        categories_df['cat_HVAC'] = calc_category(HVAC_DB, categories_df)

        # define HVAC systems types
        prop_HVAC_df = categories_df.merge(HVAC_DB, left_on='cat_HVAC', right_on='Code')

        # write to shapefile
        prop_HVAC_df_merged = names_df.merge(prop_HVAC_df, on="Name")
        fields = ['Name','type_cs', 'type_hs', 'type_dhw', 'type_ctrl', 'type_vent']
        df2dbf(prop_HVAC_df_merged[fields], locator.get_building_hvac())

    if prop_comfort_flag:
        comfort_DB = get_database(locator.get_archetypes_properties(), 'INDOOR_COMFORT')

        # define comfort
        prop_comfort_df = categories_df.merge(comfort_DB, left_on='mainuse', right_on='Code')

        # write to shapefile
        prop_comfort_df_merged = names_df.merge(prop_comfort_df, on="Name")
        fields = ['Name','Tcs_set_C', 'Ths_set_C', 'Tcs_setb_C', 'Ths_setb_C', 'Ve_lps']
        df2dbf(prop_comfort_df_merged[fields], locator.get_building_comfort())

    if prop_internal_loads_flag:
        internal_DB = get_database(locator.get_archetypes_properties(), 'INTERNAL_LOADS')

        # define comfort
        prop_internal_df = categories_df.merge(internal_DB, left_on='mainuse', right_on='Code')

        # write to shapefile
        prop_internal_df_merged = names_df.merge(prop_internal_df, on="Name")
        fields = ['Name','Qs_Wp', 'X_ghp', 'Ea_Wm2', 'El_Wm2',	'Epro_Wm2',	'Ere_Wm2', 'Ed_Wm2', 'Vww_lpd',	'Vw_lpd']
        df2dbf(prop_internal_df_merged[fields], locator.get_building_internal())


def calc_code(code1, code2, code3, code4):
    return str(code1)+str(code2)+str(code3)+str(code4)


def calc_mainuse(uses_df, uses):

    databaseclean = uses_df[uses].transpose()
    array_max = np.array(databaseclean[databaseclean[:] > 0].idxmax(skipna=True), dtype='S10')
    for i in range(len(array_max)):
        if databaseclean[i][array_max[i]] != 1:
            databaseclean[i][array_max[i]] = 0
    array_second = np.array(databaseclean[databaseclean[:] > 0].idxmax(skipna=True), dtype='S10')
    mainuse = np.array(map(calc_comparison, array_second, array_max))

    return mainuse


def get_database(path_database, sheet):
    database = pd.read_excel(path_database, sheet)
    return database


def calc_comparison(array_second, array_max):
    if array_max == 'PARKING':
        if array_second != 'PARKING':
            array_max = array_second
    return array_max


def calc_category(archetype_DB, age):
    category = []
    for row in age.index:
        if age.loc[row, 'envelope'] > 0:
            category.append(archetype_DB[(archetype_DB['year_start'] <= age.loc[row, 'envelope']) & \
                                         (archetype_DB['year_end'] >= age.loc[row, 'envelope']) & \
                                         (archetype_DB['building_use'] == age.loc[row, 'mainuse']) & \
                                         (archetype_DB['standard'] == 'R')].Code.values[0])
        else:
            category.append(archetype_DB[(archetype_DB['year_start'] <= age.loc[row, 'built']) & \
                                         (archetype_DB['year_end'] >= age.loc[row, 'built']) & \
                                         (archetype_DB['building_use'] == age.loc[row, 'mainuse']) & \
                                         (archetype_DB['standard'] == 'C')].Code.values[0])
    return category


def correct_archetype_areas(prop_architecture_df, architecture_DB, list_uses):
    """
        Corrects the heated and electrical areas 'Hs' and 'Es' for buildings with multiple uses.

         :var prop_architecture_df: DataFrame containing each building's occupancy, construction and renovation data as
         well as the architectural properties obtained from the archetypes.
         :type prop_architecture_df: DataFrame
         :var architecture_DB: architecture database for each archetype
         :type architecture_DB: DataFrame
         :var list_uses: list of all occupancy types in the project
         :type list_uses: list[str]

         :return Hs_list: the corrected values for 'Hs' for each building
         :type Hs_list: list[float]
         :return Es_list: the corrected values for 'Es' for each building
         :type Es_list: list[float]
    """
    indexed_DB = architecture_DB.set_index('Code')

    # weighted average of values
    def calc_average(last, current, share_of_use):
        return last + current * share_of_use
    Hs_list = []
    Es_list = []
    for building in prop_architecture_df.index:
        Hs = Es = 0
        for use in list_uses:
            if prop_architecture_df[use][building] > 0:
                current_use_code = calc_category(use, prop_architecture_df['built'][building],
                                                 prop_architecture_df['envelope'][building])
                Hs = calc_average(Hs, indexed_DB['Hs'][current_use_code], prop_architecture_df[use][building])
                Es = calc_average(Es, indexed_DB['Es'][current_use_code], prop_architecture_df[use][building])

        Hs_list.append(Hs)
        Es_list.append(Es)

    return Hs_list, Es_list

def calc_internal_loads(categories_df, internal_DB, list_uses, fields):
    """

    :param categories_df:
    :type categories_df: DataFrame
    :param internal_DB:
    :type internal_DB: DataFrame
    :param list_uses:
    :type list_uses: list[str]
    :param fields:
    :type fields: list[str]

    :return internal_loads:
    """
    indexed_DB = internal_DB.set_index('Code')

    # weighted average of values
    def calc_average(last, current, share_of_use):
        return last + current * share_of_use

    internal_loads = {}
    building_loads = {}
    for field in fields:
        internal_loads[field] = []

    for building in categories_df.index:
        for field in fields:
            building_loads[field] = 0
        for use in list_uses:
            if categories_df[use][building] > 0:
                for field in fields:
                    building_loads[field] = calc_average(building_loads[field], indexed_DB[field][use], categories_df[use][building])
        for field in fields:
            internal_loads[field].append(building_loads[field])

    internal_loads_df = pd.DataFrame(data=None)
    internal_loads_df['Name'] = categories_df['Name']
    for field in fields:
        internal_loads_df[field] = internal_loads[field]

    return internal_loads_df

def run_as_script(scenario_path=None, prop_thermal_flag=True, prop_architecture_flag=True, prop_hvac_flag=True,
                  prop_comfort_flag=True, prop_internal_loads_flag=True):
    """
    Run the properties script with input from the reference case and compare the results. This ensures that changes
    made to this script (e.g. refactorings) do not stop the script from working and also that the results stay the same.
    """
    import cea.globalvar
    gv = cea.globalvar.GlobalVariables()
    if not scenario_path:
        scenario_path = gv.scenario_reference
    locator = cea.inputlocator.InputLocator(scenario_path=scenario_path)
    properties(locator=locator, prop_architecture_flag=prop_architecture_flag,
               prop_hvac_flag=prop_hvac_flag, prop_comfort_flag=prop_comfort_flag,
               prop_internal_loads_flag=prop_internal_loads_flag)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--scenario', help='Path to the scenario folder')
    args = parser.parse_args()

    run_as_script(scenario_path=args.scenario)
