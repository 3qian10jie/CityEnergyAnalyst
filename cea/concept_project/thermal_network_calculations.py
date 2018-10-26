from __future__ import division
import time
from cea.concept_project import process_results
from cea.concept_project.electrical_grid_calculations import electrical_grid_calculations
import cea.globalvar
import cea.inputlocator
import cea.config

from cea.technologies.thermal_network.network_layout.main import network_layout
from cea.technologies.thermal_network import thermal_network_matrix

def thermal_network_calculations(dict_connected, config):
    # ============================
    # Solve the electrical grid problem, and decide on the best electrical line types and lengths. It is an optimization
    # problem for a fixed demand
    # ============================
    m = electrical_grid_calculations(dict_connected)

    electrical_grid_file_name = 'grid'
    thermal_network_file_name = 'thermal_network_1'

    # ============================
    # Create shape file of the thermal network based on the buildings connected, which is further processed
    # ============================
    process_results.creating_thermal_network_shape_file_main(m, electrical_grid_file_name, thermal_network_file_name)

    print (config.scenario)
    locator = cea.inputlocator.InputLocator(scenario=config.scenario)
    connected_building_names = []  # Placeholder, this is only used in Network optimization
    network_layout(config, locator, connected_building_names, input_path_name='streets')
    thermal_network_matrix.main(config)

def main(config):

    dict_connected = {0: 1, 1: 1, 2: 0,
                      3: 1, 4: 0, 5: 1,
                      6: 0, 7: 1, 8: 1,
                      9: 1}
    #                        , 10: 1, 11: 1,
    #                   12: 1, 13: 1, 14: 1,
    #                   15: 1, 16: 1, 17: 1,
    #                   18: 1, 19: 1, 20: 1,
    #                   21: 1, 22: 1, 23: 1,
    #                   }

    t0 = time.clock()
    thermal_network_calculations(dict_connected, config)
    print 'main() succeeded'
    print 'total time: ', time.clock() - t0


if __name__ == '__main__':
    main(cea.config.Configuration())
