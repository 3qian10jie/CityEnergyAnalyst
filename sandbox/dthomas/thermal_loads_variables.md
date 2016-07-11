# List of variables in thermal_loads

Especially since I am refactoring them to one big dataframe...

The main variables introduced is `tsd`, which stands for "time step data".

## calc_thermal_loads_new_ventilation

- `T_ext` -> `tsd['T_ext']`
  - outdoor drybulb temperature
  - from: `weather_data.drybulb_C.values`
  - to: `calc_Qdis_ls:text`
  - to: `calc_dhw_heating_demand:T_ext`
- `rh_ext` -> `tsd['rh_ext']`
  - relative humidity
  - from: `weather_data.relhum_percent.values`
-  mixed_schedule -> `tsd[['occ', 'el', 'pro', 'dhw']]`
  - schedule data (occupancy, electric use, probability of occupancy, domestic hot water use
  - from: `functions.calc_mixed_schedule`
  - to: `functions.get_internal_loads`
  - to: `functions.get_occupancy`
- `Ealf`, `Edataf`,  `Eprof`,  `Eref`,  `Qcrefri`,  `Qcdata`,  `vww`, `vw` -> `tsd[['Ealf', 'Edataf', 'Eprof', 'Eref', 'Qcrefri', 'Qcdata', 'vww', 'vw']]`
  - from: `functions.get_internal_loads:Ealf, Edataf, Eprof, Eref, Qcrefri, Qcdata, vww, vw`
  - to: `calc_heat_gains_internal_sensible:Eal_nove, Eprof, Qcdata, Qcrefri`
  - to: `calc_dhw_heating_demand:vw, vww`
  - to: `calc_loads_electrical:Ealf, Edataf, Eprof`
- `people` -> `tsd['people']`
  - from: `functions.get_occupancy:people`
  - to: `functions.get_internal_comfort:people`
  - to: `calc_qv_req:people`
  - to: `calc_heat_gains_internal_sensible:people`
  - to: `calc_heat_gains_internal_latent:people`
- `ve_schedule,  ta_hs_set,  ta_cs_set` -> `tsd[['ve',  'ta_hs_set',  'ta_cs_set']]`
  - from: `functions.get_internal_comfort:ve, ta_hs_set, ta_cs_set`
  - to: `calc_qv_req:ve`
  - to: `ThermalLoadsInput:temp_hs_set, temp_cs_set`
  - to: `calc_temperatures_emission_systems:ta_hs_set`
- `qv_req` -> `tsd['qv_req']`
  - from: `calc_qv_req`
  - to `calc_pumping_systems_aux_loads:qv_req`
- `qm_ve_req` -> `tsd['qm_ve_req']`
  - from: `tsd['qv_req'] * gv.Pair`
  - to: `ThermalLoadsInput:qm_ve_req`
- `i_sol` -> `tsd['I_sol']`
  - from: `calc_heat_gains_solar:I_sol`
  - to: `calc_comp_heat_gains_sensible:I_sol`
- `i_int_sen` -> `tsd['I_int_sen']`
  - from: `calc_heat_gains_internal_sensible:I_int_sen`
  - to: `functions.calc_comp_heat_gains_sensible:I_int_sen`
- `i_ia, i_m, i_st` -> `tsd[['I_ia', 'I_m', 'I_st']]`
  - from: `functions.calc_comp_heat_gains_sensible:I_ia, I_m, I_st`
  - to: `ThermalLoadsInput:i_st, i_ia, i_m`
- `w_int` -> `tsd['w_int']`
  - from: `functions.calc_heat_gains_internal_latent:w_int`
  - to: `ThermalLoadsInput:w_int`
- `uncomfort` -> `tsd['uncomfort']
  - from: `calc_thermal_load_hvac_timestep:uncomfort`
  - from: `calc_thermal_load_mechanical_and_natural_ventilation_timestep:uncomfort`
- `Ta` -> `tsd['Ta']`
  - from: `calc_thermal_load_hvac_timestep:temp_a`
  - from: `calc_thermal_load_mechanical_and_natural_ventilation_timestep:temp_a`
  - to: `state_prev['temp_air_prev']`
  - to: `functions.calc_Qdis_ls:tair`
  - to: `functions.calc_temperatures_emission_systems:Ta`
  - to: `functions.calc_dhw_heating_demand:Ta`
- `Tm` -> `tsd['Tm']`
  - from: `calc_thermal_load_hvac_timestep:temp_m`
  - from: `calc_thermal_load_mechanical_and_natural_ventilation_timestep:temp_m`
  - to: `state_prev['temp_m_prev']`
- `Qhs_sen` -> `tsd['Qhs_sen']`
  - from: `calc_thermal_load_hvac_timestep:q_hs_sen`
  - from: `calc_thermal_load_mechanical_and_natural_ventilation_timestep:q_hs_sen`
- `Qcs_sen` -> `tsd['Qcs_sen']`
  - from: `calc_thermal_load_hvac_timestep:q_cs_sen`
  - from: `calc_thermal_load_mechanical_and_natural_ventilation_timestep:q_cs_sen`
- `Qhs_lat` -> `tsd['Qhs_lat']`
  - from: `calc_thermal_load_hvac_timestep:q_cs_sen`
  - from: `calc_thermal_load_mechanical_and_natural_ventilation_timestep:q_cs_sen`  
- in fact, we do these substitutions for `calc_thermal_load_hvac_timestep` results:
  - `tsd['Tm'][t]` <- `calc_thermal_load_hvac_timestep:temp_m`
  - `tsd['Ta'][t]` <- `calc_thermal_load_hvac_timestep:temp_a`
  - `Qhs_sen_incl_em_ls[t]` <- `calc_thermal_load_hvac_timestep:q_hs_sen_loss_true`
  - `Qcs_sen_incl_em_ls[t]` <- `calc_thermal_load_hvac_timestep:q_cs_sen_loss_true`
  - `tsd['uncomfort'][t]` <- `calc_thermal_load_hvac_timestep:uncomfort`
  - `tsd['Top'][t]` <- `calc_thermal_load_hvac_timestep:temp_op`
  - `tsd['Im_tot'][t]` <- `calc_thermal_load_hvac_timestep:i_m_tot`
  - `tsd['q_hs_sen_hvac'][t]` <- `calc_thermal_load_hvac_timestep:q_hs_sen_hvac`
  - `tsd['q_cs_sen_hvac'][t]` <- `calc_thermal_load_hvac_timestep:q_cs_sen_hvac`
  - `tsd['Qhs_lat'][t]` <- `calc_thermal_load_hvac_timestep:q_hum_hvac`
  - `tsd['Qcs_lat'][t]` <- `calc_thermal_load_hvac_timestep:q_dhum_hvac`
  - `tsd['Ehs_lat_aux'][t]` <- `calc_thermal_load_hvac_timestep:e_hum_aux_hvac`
  - `tsd['qm_ve_mech'][t]` <- `calc_thermal_load_hvac_timestep:qm_ve_mech`
  - `tsd['Qhs_sen'][t]` <- `calc_thermal_load_hvac_timestep:q_hs_sen`
  - `tsd['Qcs_sen'][t]` <- `calc_thermal_load_hvac_timestep:q_cs_sen`
  - `tsd['Qhs_em_ls'][t]` <- `calc_thermal_load_hvac_timestep:qhs_em_ls`
  - `tsd['Qcs_em_ls'][t]` <- `calc_thermal_load_hvac_timestep:qcs_em_ls`
  - `tsd['ma_sup_hs'][t]` <- `calc_thermal_load_hvac_timestep:qm_ve_hvac_h`
  - `tsd['ma_sup_cs'][t]` <- `calc_thermal_load_hvac_timestep:qm_ve_hvac_c`
  - `tsd['Ta_sup_hs'][t]` <- `calc_thermal_load_hvac_timestep:temp_sup_h`
  - `tsd['Ta_sup_cs'][t]` <- `calc_thermal_load_hvac_timestep:temp_sup_c`
  - `tsd['Ta_re_hs'][t]` <- `calc_thermal_load_hvac_timestep:temp_rec_h`
  - `tsd['Ta_re_cs'][t]` <- `calc_thermal_load_hvac_timestep:temp_rec_c`
  - `tsd['w_re'][t]` <- `calc_thermal_load_hvac_timestep:w_rec`
  - `tsd['w_sup'][t]` <- `calc_thermal_load_hvac_timestep:w_sup`
- and here the map for `calc_thermal_load_mechanical_and_natural_ventilation_timestep`:
  - `tsd['Tm'][t]` <- `calc_thermal_load_hvac_timestep:temp_m`
  - `tsd['Ta'][t]` <- `calc_thermal_load_hvac_timestep:temp_a`
  - `tsd['Qhs_sen_incl_em_ls'][t]` <- `calc_thermal_load_hvac_timestep:q_hs_sen_loss_true`
  - `tsd['Qcs_sen_incl_em_ls'][t]` <- `calc_thermal_load_hvac_timestep:q_cs_sen_loss_true`
  - `tsd['uncomfort'][t]` <- `calc_thermal_load_hvac_timestep:uncomfort`
  - `tsd['Top'][t]` <- `calc_thermal_load_hvac_timestep:temp_op`
  - `tsd['Im_tot'][t]` <- `calc_thermal_load_hvac_timestep:i_m_tot`
  - `tsd['qm_ve_mech'][t]` <- `calc_thermal_load_hvac_timestep:qm_ve_mech`
  - `tsd['Qhs_sen'][t]` <- `calc_thermal_load_hvac_timestep:q_hs_sen`
  - `tsd['Qcs_sen'][t]` <- `calc_thermal_load_hvac_timestep:q_cs_sen`
  - `tsd['Qhs_em_ls'][t]` <- `calc_thermal_load_hvac_timestep:qhs_em_ls`
  - `tsd['Qcs_em_ls'][t]` <- `calc_thermal_load_hvac_timestep:qcs_em_ls`
- refactored output of `calc_thermal_load_hvac_timestep` to new parameter `tsd` 



  
  
