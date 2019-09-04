"""
hydraulic network
"""


from __future__ import division
import pandas as pd

__author__ = "Thuy-An Nguyen"
__copyright__ = "Copyright 2015, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Thuy-An Nguyen", "Tim Vollrath", "Jimeno A. Fonseca"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


# Pumping Cost

def calc_Closs_pressure(locator, network_name, network_type):
    """
    This function calculates the cost caused by the pump making up for the pressure losses in the system
    :param locator:
    :param network_name:
    :param network_type:

    :return hourly_cost:
    :return total_cost:
    """
    #read in electric requirement of pump per timestep
    pressure_loss_kw = pd.read_csv(locator.get_thermal_network_layout_pressure_drop_kw_file(network_type, network_name))
    # read in electricity price
    electricity_price = 1 # todo: find timeseries of data and read in
    #multiply with electricity cost
    hourly_cost = pressure_loss_kw * electricity_price
    #sum over all hours
    total_cost = sum(hourly_cost)
    return hourly_cost, total_cost


# Thermal losses Cost
def calc_Closs_heat(locator, network_name, network_type):
    """
    This function calculates the cost of additional heat which has to be produced to make up for heat
    losses in the system

    :param locator:
    :param network_name:
    :param network_type:

    :return hourly_cost:
    :return total_cost:
    """
    # read in electric requirement of pump per timestep
    heat_loss_kw = pd.read_csv(locator.get_thermal_network_qloss_system_file(network_type, network_name))
    # read in electricity price
    heat_price = 1  # todo: find timeseries of data of cost of producing 1 kWh at plant in that timestep and read in
    # multiply with electricity cost
    hourly_cost = heat_loss_kw * heat_price
    # sum over all hours
    total_cost = sum(hourly_cost)
    return hourly_cost, total_cost