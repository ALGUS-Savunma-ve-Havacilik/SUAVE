# Constant_Throttle_Constant_Speed.py
# 
# Created:  Jul 2014, SUAVE Team
# Modified: Jan 2016, E. Botero

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import numpy as np

# ----------------------------------------------------------------------
#  Unpack Unknowns
# ----------------------------------------------------------------------

def unpack_body_angle(segment,state):

    # unpack unknowns
    theta      = state.unknowns.body_angle

    # apply unknowns
    state.conditions.frames.body.inertial_rotations[:,1] = theta[:,0]      


# ----------------------------------------------------------------------
#  Initialize Conditions
# ----------------------------------------------------------------------

def initialize_conditions(segment,state):
    
    # unpack
    throttle   = segment.throttle
    Vo         = segment.air_speed_start
    Vf         = segment.air_speed_end
    alt0       = segment.altitude_start 
    altf       = segment.altitude_end
    t_nondim   = state.numerics.dimensionless.control_points
    conditions = state.conditions  

    # check for initial altitude
    if alt0 is None:
        if not state.initials: raise AttributeError('initial altitude not set')
        alt0 = -1.0 * state.initials.conditions.frames.inertial.position_vector[-1,2]

    # initial velocity values
    v_mag = (Vf-Vo)*t_nondim + Vo
    

    # pack conditions  
    conditions.propulsion.throttle[:,0] = throttle
    conditions.frames.inertial.velocity_vector[:,0] = v_mag[:,0] # start up value
    
def update_differentials_altitude(segment,state):
    """ Segment.update_differentials_altitude(conditions, numerics, unknowns)
        updates the differential operators t, D and I
        must return in dimensional time, with t[0] = 0

        Works with a segment discretized in vertical position, altitude

        Inputs - 
            unknowns      - data dictionary of segment free unknowns
            conditions    - data dictionary of segment conditions
            numerics - data dictionary of non-dimensional differential operators

        Outputs - 
            numerics - udpated data dictionary with dimensional numerics 

        Assumptions - 
            outputed operators are in dimensional time for the current solver iteration
            works with a segment discretized in vertical position, altitude

    """

    # unpack
    t = state.numerics.dimensionless.control_points
    D = state.numerics.dimensionless.differentiate
    I = state.numerics.dimensionless.integrate

    
    # Unpack segment initials
    alt0       = segment.altitude_start 
    altf       = segment.altitude_end    
    conditions = state.conditions  

    r = state.conditions.frames.inertial.position_vector
    v = state.conditions.frames.inertial.velocity_vector
    
    # check for initial altitude
    if alt0 is None:
        if not state.initials: raise AttributeError('initial altitude not set')
        alt0 = -1.0 * state.initials.conditions.frames.inertial.position_vector[-1,2]    
    
    # get overall time step
    vz = -v[:,2,None] # Inertial velocity is z down
    dz = altf- alt0    
    dt = dz / np.dot(I[-1,:],vz)[-1] # maintain column array
    
    # Integrate vz to get altitudes
    alt = alt0 + np.dot(I*dt,vz)

    # rescale operators
    t = t * dt

    # pack
    t_initial = state.conditions.frames.inertial.time[0,0]
    state.conditions.frames.inertial.time[:,0] = t_initial + t[:,0]
    conditions.frames.inertial.position_vector[:,2] = -alt[:,0] # z points down
    conditions.freestream.altitude[:,0]             =  alt[:,0] # positive altitude in this context    

    return

# ----------------------------------------------------------------------
#  Update Velocity Vector from Wind Angle
# ----------------------------------------------------------------------

def update_velocity_vector_from_wind_angle(segment,state):
    
    # unpack
    conditions = state.conditions 
    Vo         = segment.air_speed_start
    Vf         = segment.air_speed_end
    t_nondim   = state.numerics.dimensionless.control_points    
    v_mag      = (Vf-Vo)*t_nondim + Vo
    alpha      = state.unknowns.wind_angle[:,0][:,None]
    theta      = state.unknowns.body_angle[:,0][:,None]
    
    # Flight path angle
    gamma = theta-alpha

    # process
    v_x =  v_mag * np.cos(gamma)
    v_z = -v_mag * np.sin(gamma) # z points down

    # pack
    conditions.frames.inertial.velocity_vector[:,0] = v_x[:,0]
    conditions.frames.inertial.velocity_vector[:,2] = v_z[:,0]

    return conditions
