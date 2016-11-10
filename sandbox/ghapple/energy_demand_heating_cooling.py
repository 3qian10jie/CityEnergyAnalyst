# -*- coding: utf-8 -*-
"""

Calculation procedure for space heating and cooling
based on:
ISO 13790 [DIN EN ISO 13790:2008-9]


"""


from __future__ import division
import numpy as np
from sandbox.ghapple import helpers as h
from sandbox.ghapple import control
from sandbox.ghapple import rc_model as rc
from sandbox.ghapple import ventilation_xx as v
from sandbox.ghapple import space_emission_systems as ses
from cea.demand import sensible_loads
from cea.demand import airconditioning_model as ac


__author__ = "Gabriel Happle"
__copyright__ = "Copyright 2016, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Gabriel Happle"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Daren Thomas"
__email__ = "thomas@arch.ethz.ch"
__status__ = "Production"



def procedure_1(bpr, tsd, hoy, gv):

    """

    :param hoy:
    :param bpr:
    :param tsd:
    :return:
    """

    tsd = sensible_loads.calc_Qgain_sen(hoy, tsd, bpr, gv)


    # +++++++++++++++++++++++++++++++
    # VENTILATION FOR HOUR
    # +++++++++++++++++++++++++++++++
    v.calc_m_ve_mech(bpr, tsd, hoy)
    v.calc_m_ve_window(bpr, tsd, hoy)
    v.calc_theta_ve_mech(bpr, tsd, hoy)
    rc.calc_h_ve_adj(tsd, hoy, gv)



    # +++++++++++++++++++++++++++++++
    # HEATING COOLING DEMAND FOR HOUR
    # +++++++++++++++++++++++++++++++

    # check demand
    # ++++++++++++
    if not rc.has_heating_demand(bpr, tsd, hoy) and not rc.has_cooling_demand(bpr, tsd, hoy):

        # no heating or cooling demand
        # calculate temperatures of building R-C-model and exit
        # --> rc_model_function_1(...)
        phi_hc_nd = 0
        temp_rc = rc.calc_temperatures_crank_nicholson( phi_hc_nd, bpr, tsd, hoy )

        theta_m_t = temp_rc[0]
        theta_air = temp_rc[1]
        theta_op = temp_rc[2]

        # write to tsd
        tsd['Tm'][hoy] = theta_m_t
        tsd['Ta'][hoy] = theta_air
        tsd['Top'][hoy] = theta_op
        tsd['Qhs_sen'][hoy] = 0  # no energy demand for heating (temperature ok)
        tsd['Qhs_em_ls'][hoy] = 0  # no emission loss of heating space emission systems
        tsd['Qcs_sen'][hoy] = 0  # no energy demand for cooling
        tsd['Qcs_em_ls'][hoy] = 0  # no losses of cooling space emission systems
        tsd['Qcs_lat_HVAC'][hoy] = 0
        tsd['Qcs_sen_HVAC'][hoy] = 0
        tsd['ma_sup_cs'][hoy] = 0
        tsd['Ta_sup_cs'][hoy] = 0
        tsd['Ta_re_cs'][hoy] = 0
        tsd['ma_sup_hs'][hoy] = 0
        tsd['Ta_sup_hs'][hoy] = 0
        tsd['Ta_re_hs'][hoy] = 0

        # return
        print('Building has no heating or cooling demand at hour', hoy)
        return

    elif rc.has_heating_demand(bpr, tsd, hoy):

        # has heating demand
        print('Building has heating demand at hour', hoy)
        # check if heating system is turned on

        # no cooling energy demand in any case
        tsd['Qcs_sen'][hoy] = 0  # no energy demand for cooling
        tsd['Qcs_em_ls'][hoy] = 0  # no losses of cooling space emission systems

        if not control.is_heating_active(hoy, bpr):

            # no heating
            # calculate temperatures of building R-C-model and exit
            # --> rc_model_function_1(...)
            phi_hc_nd = 0
            temp_rc = rc.calc_temperatures_crank_nicholson(phi_hc_nd, bpr, tsd, hoy)

            theta_m_t = temp_rc[0]
            theta_air = temp_rc[1]
            theta_op = temp_rc[2]

            # write to tsd
            tsd['Tm'][hoy] = theta_m_t
            tsd['Ta'][hoy] = theta_air
            tsd['Top'][hoy] = theta_op
            tsd['Qhs_sen'][hoy] = 0  # no heating energy demand (system off)
            tsd['Qhs_em_ls'][hoy] = 0  # no losses of heating space emission systems
            tsd['Qcs_lat_HVAC'][hoy] = 0
            tsd['Qcs_sen_HVAC'][hoy] = 0
            tsd['ma_sup_cs'][hoy] = 0
            tsd['Ta_sup_cs'][hoy] = 0
            tsd['Ta_re_cs'][hoy] = 0
            tsd['ma_sup_hs'][hoy] = 0
            tsd['Ta_sup_hs'][hoy] = 0
            tsd['Ta_re_hs'][hoy] = 0


            # return # TODO: check speed with and without return here
            # return

        elif control.is_heating_active(hoy, bpr) and control.heating_system_is_ac(bpr):

            tsd['theta_ve_mech'][hoy] = tsd['T_ext'][hoy]
            rc.calc_h_ve_adj(tsd, hoy, gv)

            # cooling with AC
            # calculate load and enter AC calculation
            # --> r_c_model_function_3(...)
            # --> kaempf_ac(...)
            # --> (iteration of air flows)
            # TODO: HVAC model
            theta_m_t_ac, \
            theta_air_ac, \
            theta_op_ac, \
            phi_hc_nd_ac = rc.calc_phi_hc_ac_cooling(bpr, tsd, hoy)

            tsd['Tm'][hoy] = theta_m_t_ac
            tsd['Ta'][hoy] = theta_air_ac
            tsd['Top'][hoy] = theta_op_ac
            tsd['Qcs_sen'][hoy] = phi_hc_nd_ac  # no heating energy demand (system off)

            ac.calc_hvac_heating(bpr, tsd, hoy, gv)

        elif control.is_heating_active(hoy, bpr) and control.heating_system_is_radiative(bpr):

            # heating with radiative system
            # calculate loads and emission losses
            # --> rc_model_function_2(...)
            theta_m_t_ac,\
            theta_air_ac,\
            theta_op_ac,\
            phi_hc_nd_ac = rc.calc_phi_hc_ac_heating(bpr, tsd, hoy)

            # write to tsd
            tsd['Tm'][hoy] = theta_m_t_ac
            tsd['Ta'][hoy] = theta_air_ac
            tsd['Top'][hoy] = theta_op_ac
            tsd['Qhs_sen'][hoy] = phi_hc_nd_ac

            # space emission system losses
            q_em_ls_heating = ses.calc_q_em_ls_heating(bpr, tsd, hoy)

            tsd['Qhs_em_ls'][hoy] = q_em_ls_heating

            # TODO: losses
            # TODO: how to calculate losses if phi_h_ac is phi_h_max ???
            tsd['Qcs_lat_HVAC'][hoy] = 0
            tsd['Qcs_sen_HVAC'][hoy] = 0
            tsd['ma_sup_cs'][hoy] = 0
            tsd['Ta_sup_cs'][hoy] = 0
            tsd['Ta_re_cs'][hoy] = 0
            tsd['ma_sup_hs'][hoy] = 0
            tsd['Ta_sup_hs'][hoy] = 0
            tsd['Ta_re_hs'][hoy] = 0

    elif rc.has_cooling_demand(bpr, tsd, hoy):

        # has cooling demand
        print('Building has cooling demand at hour', hoy)
        # check if cooling system is turned on
        # no heating demand in any case:
        tsd['Qhs_sen'][hoy] = 0  # no heating energy demand (system off)
        tsd['Qhs_em_ls'][hoy] = 0  # no losses of heating space emission systems
        tsd['ma_sup_hs'][hoy] = 0
        tsd['Ta_sup_hs'][hoy] = 0
        tsd['Ta_re_hs'][hoy] = 0

        if not control.is_cooling_active(bpr, tsd, hoy, gv):

            # no cooling
            # calculate temperatures of R-C-model and exit
            # --> rc_model_function_1(...)
            phi_hc_nd = 0
            temp_rc = rc.calc_temperatures_crank_nicholson(phi_hc_nd, bpr, tsd, hoy)

            theta_m_t = temp_rc[0]
            theta_air = temp_rc[1]
            theta_op = temp_rc[2]

            # write to tsd
            tsd['Tm'][hoy] = theta_m_t
            tsd['Ta'][hoy] = theta_air
            tsd['Top'][hoy] = theta_op
            tsd['Qcs_sen'][hoy] = 0  # no heating energy demand (system off)
            tsd['Qcs_em_ls'][hoy] = 0  # no losses of heating space emission systems

            # return # TODO: check speed with and without return here
            # return
            tsd['Qcs_lat_HVAC'][hoy] = 0
            tsd['Qcs_sen_HVAC'][hoy] = 0
            tsd['ma_sup_cs'][hoy] = 0
            tsd['Ta_sup_cs'][hoy] = 0
            tsd['Ta_re_cs'][hoy] = 0

        elif control.is_cooling_active(bpr, tsd, hoy, gv) and control.cooling_system_is_ac(bpr):

            # calculate cooling load without mechanical ventilation
            # recalculate rc-model properties for ventilation
            tsd['theta_ve_mech'][hoy] = gv.temp_sup_cool_hvac
            rc.calc_h_ve_adj(tsd, hoy, gv)


            # cooling with AC
            # calculate load and enter AC calculation
            # --> r_c_model_function_3(...)
            # --> kaempf_ac(...)
            # --> (iteration of air flows)
            # TODO: HVAC model
            theta_m_t_ac, \
            theta_air_ac, \
            theta_op_ac, \
            phi_hc_nd_ac = rc.calc_phi_hc_ac_cooling(bpr, tsd, hoy)

            tsd['Tm'][hoy] = theta_m_t_ac
            tsd['Ta'][hoy] = theta_air_ac
            tsd['Top'][hoy] = theta_op_ac
            tsd['Qcs_sen'][hoy] = phi_hc_nd_ac  # no heating energy demand (system off)

            ac.calc_hvac_cooling(bpr, tsd, hoy, gv)

            print('HVAC')

        elif control.is_cooling_active(bpr, tsd, hoy, gv) and control.cooling_system_is_radiative(bpr):

            # cooling with radiative system
            # calculate loads and emission losses
            # --> rc_model_function_2(...)
            theta_m_t_ac, \
            theta_air_ac, \
            theta_op_ac, \
            phi_hc_nd_ac = rc.calc_phi_hc_ac_cooling(bpr, tsd, hoy)

            # write to tsd
            tsd['Tm'][hoy] = theta_m_t_ac
            tsd['Ta'][hoy] = theta_air_ac
            tsd['Top'][hoy] = theta_op_ac
            tsd['Qcs_sen'][hoy] = phi_hc_nd_ac

            # space emission system losses
            q_em_ls_heating = ses.calc_q_em_ls_heating(bpr, tsd, hoy)

            tsd['Qcs_em_ls'][hoy] = q_em_ls_heating

            tsd['Qcs_lat_HVAC'][hoy] = 0
            tsd['Qcs_sen_HVAC'][hoy] = 0
            tsd['ma_sup_cs'][hoy] = 0
            tsd['Ta_sup_cs'][hoy] = 0
            tsd['Ta_re_cs'][hoy] = 0

    else:
        print('Error: Unknown HVAC system status')
        return

    return












# TODO: night flushing: 9.3.3.10 in ISO 13790