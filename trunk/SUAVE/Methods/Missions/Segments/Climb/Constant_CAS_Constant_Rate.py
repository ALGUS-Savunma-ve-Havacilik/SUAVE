# Constant_CAS_Constant_Rate.py
#
# Created: Jul 2016, Tarik
# Modified:

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------
import numpy as np
import SUAVE
from compute_TAS_from_CAS import compute_TAS_from_CAS

# ----------------------------------------------------------------------
#  Initialize Conditions
# ----------------------------------------------------------------------
def initialize_conditions(segment,state):

    # unpack
    climb_rate = segment.climb_rate
    cas        = segment.calibrated_air_speed
    alt0       = segment.altitude_start
    altf       = segment.altitude_end
    t_nondim   = state.numerics.dimensionless.control_points
    conditions = state.conditions

    # check for initial altitude
    if alt0 is None:
        if not state.initials: raise AttributeError('initial altitude not set')
        alt0 = -1.0 * state.initials.conditions.frames.inertial.position_vector[-1,2]

    # discretize on altitude
    alt = t_nondim * (altf-alt0) + alt0

	# get atmospheric conditions
    conditions.freestream.altitude = alt
    SUAVE.Methods.Missions.Segments.Common.Aerodynamics.update_atmosphere(segment,state)

    # compute true airspeed based in input Calibrated Airspeed
    true_airspeed = compute_TAS_from_CAS(cas,conditions,segment.analyses.atmosphere)

   # process velocity vector
    v_mag = true_airspeed[:,0]
    v_z   = -climb_rate # z points down
    v_x   = np.sqrt( v_mag**2 - v_z**2 )

    # pack conditions
    conditions.frames.inertial.velocity_vector[:,0] = v_x
    conditions.frames.inertial.velocity_vector[:,2] = v_z
    conditions.frames.inertial.position_vector[:,2] = -alt[:,0] # z points down
    conditions.freestream.altitude[:,0]             =  alt[:,0] # positive altitude in this context