# untrimmed.py
#
# Created:  Jan 2014, T. Orra (base file in low fidelity)
# Modified: May 2017, T. MacDonald  

def untrimmed(state,settings,geometry):

    # Unpack inputs
    conditions     = state.conditions
    configuration  = settings
    drag_breakdown = conditions.aerodynamics.drag_breakdown

    # Various drag components
    parasite_total        = conditions.aerodynamics.drag_breakdown.parasite.total            
    induced_total         = conditions.aerodynamics.drag_breakdown.induced.total  
    invisid_total         = parasite_total + induced_total
    compressibility_total = conditions.aerodynamics.drag_breakdown.compressible.total         
    miscellaneous_drag    = conditions.aerodynamics.drag_breakdown.miscellaneous.total 

    # Untrimmed drag
    aircraft_untrimmed = invisid_total        \
        + compressibility_total \
        + miscellaneous_drag
    
    conditions.aerodynamics.drag_breakdown.untrimmed = aircraft_untrimmed
    
    return aircraft_untrimmed