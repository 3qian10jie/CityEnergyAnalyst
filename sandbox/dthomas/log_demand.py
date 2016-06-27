"""log_radiation.py
run the radiation.py script with the functionlogger.
"""
import os

import cea.demand
import functionlogger
import cea.thermal_loads
import cea.maker
import cea.hvac_kaempf
import contributions.thermal_loads_new_ventilation.simple_window_generator
import contributions.thermal_loads_new_ventilation.ventilation

if __name__ == '__main__':
    path_to_log = os.path.join(os.path.dirname(__file__), 'cea.demand.log.sql')
    path_to_md = os.path.join(os.path.dirname(__file__), 'cea.demand.log.md')

    if os.path.exists(path_to_log):
        os.remove(path_to_log)

    functionlogger.connect_to(path_to_log)
    functionlogger.wrap_module(cea.demand, first_only=True)
    functionlogger.wrap_module(cea.maker, first_only=True)
    functionlogger.wrap_module(cea.demand.f, first_only=True)
    functionlogger.wrap_module(cea.thermal_loads, first_only=True)
    functionlogger.wrap_module(cea.hvac_kaempf, first_only=True)
    functionlogger.wrap_module(contributions.thermal_loads_new_ventilation.simple_window_generator, first_only=True)
    functionlogger.wrap_module(contributions.thermal_loads_new_ventilation.ventilation, first_only=True)

    cea.demand.test_demand()

    with open(path_to_md, 'w') as writer:
        functionlogger.generate_output(path_to_log, writer)
