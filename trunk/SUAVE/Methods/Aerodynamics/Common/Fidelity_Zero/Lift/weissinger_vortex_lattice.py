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
import numpy as np
import pylab as plt
import matplotlib
# ----------------------------------------------------------------------
#  Weissinger Vortex Lattice
# ----------------------------------------------------------------------

## @ingroup Methods-Aerodynamics-Common-Fidelity_Zero-Lift
def weissinger_vortex_lattice(conditions,settings,wing, propulsors):
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
 

        
    orientation = wing.vertical    
    
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
    
    ##-----------------------------------
    ## test parameters  
    #V_inf = 65
    #V_j = 70    
    #rho = 1.2 
        
    #prop_Cl= 0.8 # propeller.sectional_lift_coefficent
    #C_T    =  1 #propeller.thrust_coeffient
    #T = 1 # thrust     
    
    #aoa  = 1 * np.pi/180  
    ##-----------------------------------

    n           = 50            # number_panels_spanwise
    # conditions
    rho              = conditions.freestream.density[0][0]
    aoa              = conditions.aerodynamics.angle_of_attack
    q_inf            = conditions.freestream.dynamic_pressure[0][0]
    q_distribution   = np.ones(n)*q_inf
    V                = conditions.propulsion.acoustic_outputs.velocity[0][0]
    V_distribution   = np.ones(n)*V 
    aoa_distribution = np.ones(n)*aoa[0][0]
    
    # chord difference
    dchord = (root_chord-tip_chord)
    if sym_para is True :
        span = span/2
        
    deltax = span/n

    if orientation == False :

        # Determine if wing segments are defined  
        segment_keys = wing.Segments.keys()
        n_segments   = len(segment_keys)
        segment_vortex_index = np.zeros(n_segments)
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
            segment_chord_x_offset = np.zeros(n_segments)
            section_stations = np.zeros(n_segments)

            # obtain chord and twist at the beginning/end of each segment
            for i_seg in xrange(n_segments):                
                segment_chord[i_seg] = wing.Segments[segment_keys[i_seg]].root_chord_percent*root_chord
                segment_twist[i_seg] = wing.Segments[segment_keys[i_seg]].twist
                segment_sweep[i_seg] = wing.Segments[segment_keys[i_seg]].sweeps.quarter_chord
                section_stations[i_seg] = wing.Segments[segment_keys[i_seg]].percent_span_location*span

                if i_seg == 0:
                    segment_span[i_seg] = 0.0
                    segment_chord_x_offset[i_seg] = 0.25*root_chord # weissinger uses quarter chord as reference
                else:
                    segment_span[i_seg]    = wing.Segments[segment_keys[i_seg]].percent_span_location*span - wing.Segments[segment_keys[i_seg-1]].percent_span_location*span
                    segment_chord_x_offset[i_seg]  = segment_chord_x_offset[i_seg-1] + segment_span[i_seg]*np.tan(segment_sweep[i_seg-1])

            # shift spanwise vortices onto section breaks 
            for i_seg in xrange(n_segments):
                idx =  (np.abs(y_coordinates-section_stations[i_seg])).argmin()
                y_coordinates[idx] = section_stations[i_seg]

            # define y coordinates of horseshoe vortices      
            ya = np.atleast_2d(y_coordinates[i])           
            yb = np.atleast_2d(y_coordinates[i+1])          
            deltax = y_coordinates[i+1] - y_coordinates[i]
            xa =  np.zeros(n)
            x  = np.zeros(n)
            y  =  np.zeros(n)
            twist_distribution =  np.zeros(n)
            chord_distribution =  np.zeros(n)

            # define coordinates of horseshoe vortices and control points
            i_seg = 0
            for idx in xrange(n):
                twist_distribution[idx]   =  segment_twist[i_seg] + ((yb[0][idx] - deltax[idx]/2 - section_stations[i_seg]) * (segment_twist[i_seg+1] - segment_twist[i_seg])/segment_span[i_seg+1])     
                chord_distribution[idx] =  segment_chord[i_seg] + ((yb[0][idx] - deltax[idx]/2 - section_stations[i_seg]) * (segment_chord[i_seg+1] - segment_chord[i_seg])/segment_span[i_seg+1])
                xa[idx]= segment_chord_x_offset[i_seg] + (yb[0][idx] - deltax[idx]/2 - section_stations[i_seg])*np.tan(segment_sweep[i_seg])                                                    # computer quarter chord points for each horseshoe vortex
                x[idx] = segment_chord_x_offset[i_seg] + (yb[0][idx] - deltax[idx]/2 - section_stations[i_seg])*np.tan(segment_sweep[i_seg])  + 0.5*chord_distribution[idx]                         # computer three-quarter chord control points for each horseshoe vortex
                y[idx] = (yb[0][idx] -  deltax[idx]/2)                

                if y_coordinates[idx] == wing.Segments[segment_keys[i_seg+1]].percent_span_location*span: 
                    i_seg += 1                    
                if y_coordinates[idx+1] == span:
                    continue

            ya = np.atleast_2d(ya)  # y coordinate of start of horseshoe vortex on panel
            yb = np.atleast_2d(yb)  # y coordinate of end horseshoe vortex on panel
            xa = np.atleast_2d(xa)  # x coordinate of horseshoe vortex on panel
            x  = np.atleast_2d(x)   # x coordinate of control points on panel
            y  = np.atleast_2d(y)   # y coordinate of control points on panel

        else:   # no segments defined on wing 
            # discretizing the wing sections into panels 
            i              = np.arange(0,n)
            chord_distribution = dchord/span*(span-(i+1)*deltax+deltax/2) + tip_chord
            twist_distribution   = twist_rc + i/float(n)*(twist_tc-twist_rc)

            ya = np.atleast_2d((i)*deltax)                                                  # y coordinate of start of horseshoe vortex on panel
            yb = np.atleast_2d((i+1)*deltax)                                                # y coordinate of end horseshoe vortex on panel
            xa = np.atleast_2d(((i+1)*deltax-deltax/2)*np.tan(sweep) + 0.25*chord_distribution) # x coordinate of horseshoe vortex on panel
            x  = np.atleast_2d(((i+1)*deltax-deltax/2)*np.tan(sweep) + 0.75*chord_distribution) # x coordinate of control points on panel
            y  = np.atleast_2d(((i+1)*deltax-deltax/2))                                     # y coordinate of control points on panel 

        # Check to see if there are any propellers  
        if propulsors.has_key('network'):
            propeller   =  propulsors['network'].propeller            
            propeller_status = True
        else: 
            propeller_status = False
        print propeller_status    
        if propeller_status : # If propellers present, find propeller location and re-vectorize wing with embedded propeller 
            if propeller.origin[0][0] < wing.origin[0] and propeller.origin[0][1] < span :
                num_prop = len(propeller.origin)                  # number of propellers  
                R_p = propeller.tip_radius
                A_eng = np.pi*R_p**2           
                V_eng      =  V
                F_eng      = -conditions.propulsion.acoustic_outputs.thrust[0][0]
                del_V_eng  =  np.sqrt(V_eng**2 + 2*F_eng/(rho*A_eng))              
                r_jet      = y[0] 

                for i in xrange(num_prop):
                    K_ep = 0.11
                    c = 1
                    b = 1
                    ep_c = K_ep *abs(del_V_eng)/(V_eng + del_V_eng)
                    ep_b = K_ep *abs(del_V_eng)/(V_eng + 0.5*del_V_eng)                                        
                    x_jet = propeller.origin[i][0] - wing.origin[0] 
                    R_p_prime = R_p*np.sqrt((V_eng + 0.5*del_V_eng)/(V_eng + del_V_eng))                    
                    x_mix = R_p_prime/ep_c
                    b_jet = R_p_prime + ep_b*x_jet
                    if x_jet < x_mix:
                        c_jet = R_p_prime - ep_c*x_jet
                    elif x_jet > x_mix:
                        c_jet = 0

                    k1 = c**2 + (9/10)*c*(b-c) + (9/35)*(b-c)**2
                    k2 = c**2 + (243/385)*c*(b-c) + (243/1820)*(b-c)**2
                    del_Vjet0 = np.sqrt(0.25*(k1**2/k2**2)*V_eng**2 + F_eng/(rho*np.pi*k2)) - 0.5*(k1/k2)*V_eng

                    for j in xrange(n):
                        if (propeller.origin[i][1]+b_jet) > r_jet[j] and r_jet[j]  > (propeller.origin[i][1]+c_jet):
                            del_V_jet = del_Vjet0*(1-((r_jet[j]-c_jet)/(b_jet - c_jet))**1.5)**2
                        elif (propeller.origin[i][1]-b_jet ) > r_jet[j] and r_jet[j]  > (propeller.origin[i][1]-c_jet):
                            del_V_jet = del_Vjet0*(((r_jet[j]-c_jet)/(b_jet - c_jet))**1.5)**2   # CHECK
                        elif (propeller.origin[i][1]+c_jet)  > r_jet[j] :
                            del_V_jet = del_Vjet0
                        elif (propeller.origin[i][1]-c_jet) > r_jet[j] :
                            del_V_jet = del_Vjet0                            
                        else:
                            del_V_jet = 0

                        V_distribution[j] =  V_distribution[j] + del_V_jet         

            q_distribution = 0.5*rho*V_distribution**2    
            LT , CL , DT, CD   ,Lift_distribution, Drag_distribution   = compute_forces(x,y,xa,ya,yb,deltax,twist_distribution,aoa_distribution ,q_inf,q_distribution,chord_distribution,Sref)            
        else:
            q_distribution = 0.5*rho*V_distribition**2    
            LT , CL , DT, CD   ,Lift_distribution, Drag_distribution   = compute_forces(x,y,xa,ya,yb,deltax,twist_distribution,aoa_distribution ,q_inf,q_distribution,chord_distribution,Sref)



        #-----------------------------------------------------------
        # PLOT LIFT & DRAF DISTRIBUTION
        #-----------------------------------------------------------
        wing_span          = np.array(np.linspace(0,span,n))
        
        fig = plt.figure('Semi Span Aerodynamics')
        fig.set_size_inches(10, 8)

        axes2 = fig.add_subplot(2,1,1)
        axes2.plot( wing_span , V_distribution, 'ro-' )
        axes2.set_xlabel('Span (m)')
        axes2.set_ylabel(r'Local Velocity $m/s$')
        axes2.grid(True)        


        axes3 = fig.add_subplot(2,1,2)
        axes3.plot( wing_span , Lift_distribution, 'bo-' )
        axes3.set_xlabel('Span (m)')
        axes3.set_ylabel(r'$Spanwise Lift$')
        axes3.grid(True)        
        plt.show()           

        return  LT , CL , DT, CD       



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


def compute_forces(x,y,xa,ya,yb,deltax,twist_distribution,aoa_distribution,q_inf,q_distribution,chord_distribution,Sref):    
    sin_aoa = np.sin(aoa_distribution)
    cos_aoa = np.cos(aoa_distribution)

    RHS  = np.atleast_2d(np.sin(twist_distribution+aoa_distribution))   
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

    # Lift & Drag distribution
    Lift_distribution      = q_distribution *L[0]*chord_distribution        
    Drag_distribution      = q_distribution *D[0]*chord_distribution       

    # Total Lift and Draf
    LT = sum(Lift_distribution) 
    DT = sum(Drag_distribution) 

    # CL and CD     
    CL  = 2*LT /( q_inf*Sref)
    CD =  2*DT /( q_inf*Sref)    

    return LT , CL , DT, CD  , Lift_distribution, Drag_distribution   


#------------------
# TO IMPLEMENT
#------------------
clc;
clear;
n = 50;
del_V_eng = 5;
V  = 50;
F_eng = 500;
rho =1.2;
V_eng = V;
R_p = 2;
prop_origin = 4;
r_jet = linspace(0,10,n);
V_distribution   = ones(1,n)*V; 

K_ep = 0.11;
c = 1;
b = 1;
ep_c = K_ep *abs(del_V_eng)/(V_eng + del_V_eng);
ep_b = K_ep *abs(del_V_eng)/(V_eng + 0.5*del_V_eng) ;                                       

x_jet = 80 ;
R_p_prime = R_p* sqrt((V_eng + 0.5*del_V_eng)/(V_eng + del_V_eng));                    
x_mix = R_p_prime/ep_c;
b_jet = R_p_prime + ep_b*x_jet;

if x_jet < x_mix
    c_jet = R_p_prime - ep_c*x_jet;
else
    c_jet = 0;
end

k1 = c^2 + (9/10)*c*(b-c) + (9/35)*(b-c)^2;
k2 = c^2 + (243/385)*c*(b-c) + (243/1820)*(b-c)^2;
del_Vjet0 =  sqrt(0.25*(k1^2/k2^2)*V_eng^2 + F_eng/(rho* pi*k2)) - 0.5*(k1/k2)*V_eng;


for j = 1:n 
    r_jet(j)
    if (prop_origin-b_jet) >= (r_jet(j));
        del_V_jet = 0;
                
    elseif  (prop_origin-b_jet) < (r_jet(j)) && (r_jet(j)) <=  (prop_origin-c_jet)  
        %del_V_jet = del_Vjet0* (2*((   (r_jet(j)-(prop_origin-b_jet))    - (prop_origin-b_jet) )/((prop_origin-c_jet)  - (prop_origin-b_jet))).^1.5 -  ((    (r_jet(j)-(prop_origin-b_jet))    - (prop_origin-b_jet)  )   /((prop_origin-c_jet)  - (prop_origin-b_jet))).^3 );
        start_val = prop_origin - b_jet;
        end_val   = prop_origin - c_jet;
        del_V_jet = del_Vjet0.* (2*((r_jet(j) - start_val)/(end_val  - start_val)).^1.5 -  ((r_jet(j) - start_val)/(end_val - start_val)).^3 );  
    elseif  (prop_origin - c_jet) < r_jet(j) && r_jet(j) <= (prop_origin+c_jet)
        del_V_jet = del_Vjet0;          
        
    elseif  (prop_origin + c_jet) < r_jet(j) && r_jet(j)  <= (prop_origin + b_jet)
        del_V_jet = del_Vjet0*(1-(((r_jet(j)-(prop_origin+c_jet))/((prop_origin + b_jet) - (prop_origin+c_jet)))^1.5))^2;                           
    
    elseif (prop_origin + b_jet ) < r_jet(j)
        del_V_jet = 0;
    end
        
    V_distribution(j) =  V_distribution(j) + del_V_jet;
end 
    
figure(2)
plot(r_jet,V_distribution) 

