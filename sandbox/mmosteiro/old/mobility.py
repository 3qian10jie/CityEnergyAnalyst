"""
===========================
Primary energy and CO2 emissions model algorithm for building operation
===========================
J. Fonseca  script development          26.08.15
D. Thomas   formatting and cleaning     27.08.15
D. Thomas   integration in toolbox      27.08.15
J. Fonseca  script redevelopment        19.04.16

"""
from __future__ import division

import pandas as pd
from geopandas import GeoDataFrame as gpdf

from cea import inputlocator

reload(inputlocator)

def lca_mobility(locator):
    """
    algorithm to calculate the primary energy and CO2 emissions for mobility
    in the area in order to compare with the 2000 Watt society benchmark
    based on SIA Standard 2039 (expanded to include industry and hospital
    buildings)
    
    Parameters
    ----------
    :param InputLocator locator: an InputLocator instance set to the scenario to work on

    Returns
    -------
    total_LCA_mobility:.csv
        csv file of yearly primary energy demand and emissions due to mobility
        for each building

    """

    # local files
    demand = pd.read_csv(locator.get_total_demand())
    prop_occupancy_df = gpdf.from_file(locator.get_building_occupancy()).drop('geometry', axis=1).set_index('Name')
    prop_occupancy = prop_occupancy_df.loc[:, (prop_occupancy_df != 0).any(axis=0)] # trick to erase occupancies that are not being used (it speeds up the code)
    data_mobility = locator.get_data_mobility()
    factors_mobility_2010 = pd.read_excel(data_mobility, sheetname='2010')

    # local variables
    result_folder = locator.get_lca_emissions_results_folder()

    # calculate total_LCA_mobility:.csv
    vt = data_mobility['code']
    pt = data_mobility['pen']
    gt = data_mobility['ghg']
    
    mobility = prop_occupancy.merge(demand,on='Name')
    fields_to_plot = ['Name', 'pen_GJ', 'ghg_ton', 'pen_MJm2', 'ghg_kgm2']
    for i in range(len(vt)):
        mobility[fields_to_plot[3]] = mobility[vt[i]] * pt[i]
        mobility[fields_to_plot[4]] = mobility[gt[i]] * gt[i]
    mobility[fields_to_plot[1]] = mobility['Af_m2'] * mobility[fields_to_plot[3]] / 1000
    mobility[fields_to_plot[2]] = mobility['Af_m2'] * mobility[fields_to_plot[4]] / 1000
    mobility[fields_to_plot].to_csv(locator.get_lca_mobility(), index=False, float_format='%.2f')

def test_lca_mobility():
    locator = inputlocator.InputLocator(scenario_path=r'C:\reference-case\baseline')
    lca_mobility(locator=locator)

    print 'test_properties() succeeded'

if __name__ == '__main__':
    test_lca_mobility()
