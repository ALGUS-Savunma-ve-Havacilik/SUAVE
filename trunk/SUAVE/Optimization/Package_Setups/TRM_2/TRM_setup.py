# pyopt_setup.py
#
# Created:  Jul 2015, E. Botero
# Modified: Apr 2017, T. MacDonald

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

# suave imports
import numpy as np
from SUAVE.Optimization import helper_functions as help_fun
from SUAVE.Optimization.Package_Setups.TRM_2 import Trust_Region_Optimization as tro
from SUAVE.Optimization.Package_Setups.TRM_2.Trust_Region import Trust_Region

# ----------------------------------------------------------------------
#  Pyopt_Solve
# ----------------------------------------------------------------------

def TRM_Solve(problem,tr=None,tr_opt=None):
   
    if tr == None:
        tr = Trust_Region()
    problem.trust_region = tr
    if tr_opt == None:
        TRM_opt = tro.Trust_Region_Optimization()
    else:
        TRM_opt = tr_opt
    TRM_opt.optimize(problem)
    
    return
