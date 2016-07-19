"""log_radiation.py
run the radiation.py script with the functionlogger.
"""
import os

import cea.dem
import contributions.thermal_loads_new_ventilation.simple_window_generator
import contributions.thermal_loads_new_ventilation.ventilation
import functionlogger

if __name__ == '__main__':
    path_to_log = os.path.join(os.path.dirname(__file__), 'cea.dem.log.sql')
    path_to_md = os.path.join(os.path.dirname(__file__), 'cea.dem.log.md')

    if os.path.exists(path_to_log):
        os.remove(path_to_log)

    functionlogger.connect_to(path_to_log)
    functionlogger.wrap_module(cea.dem, first_only=True)
    #functionlogger.wrap_module(cea.maker, first_only=True)
    functionlogger.wrap_module(cea.dem.f, first_only=True)
    functionlogger.wrap_module(cea.thermal_loads, first_only=True)
    functionlogger.wrap_module(cea.hvac_kaempf, first_only=True)
    functionlogger.wrap_module(contributions.thermal_loads_new_ventilation.simple_window_generator, first_only=True)
    functionlogger.wrap_module(contributions.thermal_loads_new_ventilation.ventilation, first_only=True)

    cea.dem.run_as_script()

    with open(path_to_md, 'w') as writer:
        functionlogger.generate_output(path_to_log, writer)
