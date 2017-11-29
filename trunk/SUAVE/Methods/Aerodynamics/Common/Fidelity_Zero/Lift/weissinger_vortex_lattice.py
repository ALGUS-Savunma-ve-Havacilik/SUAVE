## @ingroup Methods-Aerodynamics-Common-Fidelity_Zero-Lift
# weissinger_vortex_lattice.py
# 
# Created:  Dec 2013, SUAVE Team
# Modified: Apr 2017, T. MacDonald
#           Oct 2017, E. Botero

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

# package imports
import numpy as np 

# ----------------------------------------------------------------------
#  Weissinger Vortex Lattice
# ----------------------------------------------------------------------

## @ingroup Methods-Aerodynamics-Common-Fidelity_Zero-Lift
def weissinger_vortex_lattice(conditions,configuration,wing):
    """Uses the vortex lattice method to compute the lift coefficient and induced drag component

    Assumptions:
    None

    Source:
    An Introduction to Theoretical and Computational Aerodynamics by Jack Moran

    Inputs:
    wing.
      spans.projected                       [m]
      chords.root                           [m]
      chords.tip                            [m]
      sweeps.quarter_chord                  [radians]
      taper                                 [Unitless]
      twists.root                           [radians]
      twists.tip                            [radians]
      symmetric                             [Boolean]
      aspect_ratio                          [Unitless]
      areas.reference                       [m^2]
      vertical                              [Boolean]
    configuration.number_panels_spanwise    [Unitless]
    configuration.number_panels_chordwise   [Unitless]
    conditions.aerodynamics.angle_of_attack [radians]

    Outputs:
    Cl                                      [Unitless]
    Cd                                      [Unitless]

    Properties Used:
    N/A
    """ 

    #unpack
    span        = wing.spans.projected
    root_chord  = wing.chords.root
    tip_chord   = wing.chords.tip
    sweep       = wing.sweeps.quarter_chord
    taper       = wing.taper
    twist_rc    = wing.twists.root
    twist_tc    = wing.twists.tip
    sym_para    = wing.symmetric
    Sref        = wing.areas.reference
    orientation = wing.vertical

    n  = configuration.number_panels_spanwise

    # conditions
    aoa = conditions.aerodynamics.angle_of_attack
    
    # chord difference
    dchord = (root_chord-tip_chord)
    if sym_para is True :
        span = span/2
        
    deltax = span/n
    
    sin_aoa = np.sin(aoa)
    cos_aoa = np.cos(aoa)

    if orientation == False :

        # Determine if wing segments are defined  
        segment_keys = wing.Segments.keys()
        n_segments   = len(segment_keys)
        # If spanwise stations are setup
        if n_segments>0:
            # discretizing the wing sections into panels
            i              = np.arange(0,n)
            j              = np.arange(0,n+1)
            y_coordinates = (j)*deltax             
            segment_chord = np.zeros(n_segments)
            segment_twist = np.zeros(n_segments)
            segment_sweep = np.zeros(n_segments)
            segment_span = np.zeros(n_segments)
            
            # obtain chord and twist at the beginning/end of each segment
            for i_seg in xrange(n_segments):                
                segment_chord[i_seg] = wing.Segments[segment_keys[i_seg]].root_chord_percent*root_chord
                segment_twist[i_seg] = wing.Segments[segment_keys[i_seg]].twist
                segment_sweep[i_seg] = wing.Segments[segment_keys[i_seg]].sweeps.quarter_chord
                if i_seg == 0:
                    segment_span[i_seg] = 0
                else:
                    segment_span[i_seg] = wing.Segments[segment_keys[i_seg]].percent_span_location*span - wing.Segments[segment_keys[i_seg-1]].percent_span_location*span
            
            # shift spanwise vortices onto section breaks 
            for i_seg in xrange(n_segments):
                idx =  (np.abs(y_coordinates-segment_span[i_seg])).argmin()
                y_coordinates[idx] = segment_span[i_seg]
            
            # define y coordinates of horseshoe vortices      
            ya = np.atleast_2d(y_coordinates[i])                                                          # y coordinate of start of horseshoe vortex on panel
            yb = np.atleast_2d(y_coordinates[i+1])                                                        # y coordinate of end horseshoe vortex on panel
            xa =  np.zeros(n)
            x  = np.zeros(n)
            y  =  np.zeros(n)
            twist_distri =  np.zeros(n)
            section_length =  np.zeros(n)
            
            # define coordinates of horseshoe vortices and control points
            i_seg = 0;
            for idx in xrange(n):
                if  y_coordinates[idx] == wing.Segments[segment_keys[i_seg]].percent_span_location*span: 
                    twist_distri[idx] = segment_twist[i_seg] - ((ya[0][idx] + (yb[0][idx]-ya[0][idx])/2)*(segment_twist[i_seg] - segment_twist[i_seg+1])/segment_span[i_seg+1])     
                    section_length[idx] =  section_length[idx] =  segment_chord[i_seg] - ((ya[0][idx] + (yb[0][idx]-ya[0][idx])/2)*(segment_chord[i_seg] - segment_chord[i_seg+1])/segment_span[i_seg+1])
                    if idx == 0:
                        pass
                    else: 
                        i_seg += 1
                else:
                    twist_distri[idx]   =  segment_twist[i_seg] - ((ya[0][idx] + (yb[0][idx]-ya[0][idx])/2)*(segment_twist[i_seg] - segment_twist[i_seg+1])/segment_span[i_seg+1])     
                    section_length[idx] =  segment_chord[i_seg] - ((ya[0][idx] + (yb[0][idx]-ya[0][idx])/2)*(segment_chord[i_seg] - segment_chord[i_seg+1])/segment_span[i_seg+1])
                    
                    
                xa[idx]= (yb[0][idx] - (yb[0][idx]-ya[0][idx])/2)*np.tan(segment_sweep[i_seg]) + 0.25*section_length[idx]   # x coordinate of horseshoe vortex on panel        
                x[idx] = (yb[0][idx] - (yb[0][idx]-ya[0][idx])/2)*np.tan(segment_sweep[i_seg]) + 0.75*section_length[idx]  # x coordinate of control points on panel  
                y[idx] = (yb[0][idx] - (yb[0][idx]-ya[0][idx])/2)                                                      # y coordinate of control points on panel 
                    
            RHS  = np.atleast_2d(np.sin(twist_distri+aoa))                                                             # twist distribution along wing 
   
        else:   # no segments defined on wing     
            i              = np.arange(0,n)
            section_length = dchord/span*(span-(i+1)*deltax+deltax/2) + tip_chord
            twist_distri   = twist_rc + i/float(n)*(twist_tc-twist_rc)
            
            ya = np.atleast_2d((i)*deltax)                                                  # y coordinate of start of horseshoe vortex on panel
            yb = np.atleast_2d((i+1)*deltax)                                                # y coordinate of end horseshoe vortex on panel
            xa = np.atleast_2d(((i+1)*deltax-deltax/2)*np.tan(sweep) + 0.25*section_length) # x coordinate of horseshoe vortex on panel
            x  = np.atleast_2d(((i+1)*deltax-deltax/2)*np.tan(sweep) + 0.75*section_length) # x coordinate of control points on panel
            y  = np.atleast_2d(((i+1)*deltax-deltax/2))                                     # y coordinate of control points on panel 
                    
            RHS  = np.atleast_2d(np.sin(twist_distri+aoa))                                  # twist distribution along wing 
                
        
        A = (whav(x,y,xa.T,ya.T)-whav(x,y,xa.T,yb.T)\
            -whav(x,y,xa.T,-ya.T)+whav(x,y,xa.T,-yb.T))*0.25/np.pi
    
        # Vortex strength computation by matrix inversion
        T = np.linalg.solve(A.T,RHS.T).T
        
        # Calculating the effective velocty         
        A_v = A*0.25/np.pi*T
        v   = np.sum(A_v,axis=1)
        
        Lfi = -T * (sin_aoa-v)
        Lfk =  T * cos_aoa 
        Lft = -Lfi * sin_aoa + Lfk * cos_aoa
        Dg  =  Lfi * cos_aoa + Lfk * sin_aoa
            
        L  = deltax * Lft
        D  = deltax * Dg
        
        # Total lift
        LT = np.sum(L)
        DT = np.sum(D)
    
        Cl = 2*LT/(0.5*Sref)
        Cd = 2*DT/(0.5*Sref)     
    
    else:
        
        Cl = 0.0
        Cd = 0.0         

    return Cl, Cd

# ----------------------------------------------------------------------
#   Helper Functions
# ----------------------------------------------------------------------
def whav(x1,y1,x2,y2):
    """ Helper function of vortex lattice method      
        Inputs:
            x1,x2 -x coordinates of bound vortex
            y1,y2 -y coordinates of bound vortex

        Outpus:
            Cl_comp - lift coefficient
            Cd_comp - drag  coefficient       

        Assumptions:
            if needed

    """    

    use_base    = 1 - np.isclose(x1,x2)*1.
    no_use_base = np.isclose(x1,x2)*1.
    
    whv = 1/(y1-y2)*(1+ (np.sqrt((x1-x2)**2+(y1-y2)**2)/(x1-x2)))*use_base + (1/(y1 -y2))*no_use_base
    
    return whv