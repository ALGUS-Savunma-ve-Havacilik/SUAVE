# AVL.py
#
# Created:  Tim Momose, Dec 2014 
# Modified: Feb 2016, Andrew Wendorff


# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

# SUAVE imports
import SUAVE
from SUAVE.Core import Units, Data
from SUAVE.Core import redirect

from SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics import Aerodynamics
from SUAVE.Analyses.Mission.Segments.Conditions.Conditions   import Conditions

from SUAVE.Methods.Aerodynamics.AVL.write_geometry   import write_geometry
from SUAVE.Methods.Aerodynamics.AVL.write_run_cases  import write_run_cases
from SUAVE.Methods.Aerodynamics.AVL.write_input_deck import write_input_deck
from SUAVE.Methods.Aerodynamics.AVL.run_analysis     import run_analysis
from SUAVE.Methods.Aerodynamics.AVL.translate_data   import translate_conditions_to_cases, translate_results_to_conditions
from SUAVE.Methods.Aerodynamics.AVL.purge_files      import purge_files
from SUAVE.Methods.Aerodynamics.AVL.Data.Results     import Results
from SUAVE.Methods.Aerodynamics.AVL.Data.Settings    import Settings
from SUAVE.Methods.Aerodynamics.AVL.Data.Cases       import Run_Case

# Package imports
import time
import pylab as plt
import os
import numpy as np
import sys
import sklearn
from sklearn import gaussian_process
from sklearn import neighbors
from sklearn import svm
from shutil import rmtree
from warnings import warn

## ----------------------------------------------------------------------
##  Class
## ----------------------------------------------------------------------

class AVL(Aerodynamics):
    """ SUAVE.Analyses.Aerodynamics.AVL
        aerodynamic model that performs a vortex lattice analysis using AVL
        (Athena Vortex Lattice, by Mark Drela of MIT).

        this class is callable, see self.__call__

    """

    def __defaults__(self):
        self.tag        = 'avl'
        self.keep_files = True

        self.settings = Settings()

        self.current_status = Data()
        self.current_status.batch_index = 0
        self.current_status.batch_file  = None
        self.current_status.deck_file   = None
        self.current_status.cases       = None
        
        self.geometry = None
        
        self.settings.filenames.log_filename = sys.stdout
        self.settings.filenames.err_filename = sys.stderr
        
        # Conditions table, used for surrogate model training
        self.training = Data()        
        self.training.angle_of_attack  = np.array([-2.,3.,8.]) * Units.deg
        self.training.Mach             = np.array([0.3,0.7,0.85])
        self.training.lift_coefficient = None
        self.training.drag_coefficient = None
        self.training_file             = None
        
        # Surrogate model
        self.surrogates = Data()

    def initialize(self):

        geometry = self.geometry
        self.tag      = 'avl_analysis_of_{}'.format(geometry.tag)

        run_folder = self.settings.filenames.run_folder
        if os.path.exists(run_folder):
            if self.keep_files:
                warn('deleting old avl run files',Warning)
            rmtree(run_folder)
        os.mkdir(run_folder)

        return

    def evaluate(self,state,settings,geometry):

        # Unpack
        surrogates = self.surrogates        
        conditions = state.conditions
        
        mach = conditions.freestream.mach_number
        AoA  = conditions.aerodynamics.angle_of_attack
        lift_model = surrogates.lift_coefficient
        drag_model = surrogates.drag_coefficient
        
        # Inviscid lift
        data_len = len(AoA)
        inviscid_lift = np.zeros([data_len,1])
        for ii,_ in enumerate(AoA):
            inviscid_lift[ii] = lift_model.predict(np.array([AoA[ii][0],mach[ii][0]]))
        conditions.aerodynamics.lift_breakdown.inviscid_wings_lift = inviscid_lift
        state.conditions.aerodynamics.lift_coefficient             = inviscid_lift
        state.conditions.aerodynamics.lift_breakdown.compressible_wings = inviscid_lift
        
        # Inviscid drag, zeros are a placeholder for possible future implementation
        inviscid_drag = np.zeros([data_len,1])
        #for ii,_ in enumerate(AoA):
        #    inviscid_drag[ii] = drag_model.predict([AoA[ii][0],mach[ii][0]])        
        state.conditions.aerodynamics.inviscid_drag_coefficient    = inviscid_drag
        
        return inviscid_lift, inviscid_drag
       
        
        

    def sample_training(self):
        
        # Unpack
        geometry = self.geometry
        training = self.training
        
        AoA  = training.angle_of_attack
        mach = training.Mach
        
        CL   = np.zeros([len(AoA)*len(mach),1])
        CD   = np.zeros([len(AoA)*len(mach),1])

        
        if self.training_file is None:
            # Calculate aerodynamics for table
            table_size = len(AoA)*len(mach)
            xy = np.zeros([table_size,2])
            count = 0
            time0 = time.time()
            for i,_ in enumerate(AoA):
                for j,_ in enumerate(mach):
                    
                    xy[count,:] = np.array([AoA[i],mach[j]])
                    
                    # Set training conditions
 
                    run_conditions = Aerodynamics()
                    run_conditions.weights.total_mass     = geometry.mass_properties.max_takeoff
                    run_conditions.freestream.density    = 1.225
                    run_conditions.freestream.gravity     = 9.81
                    run_conditions.aerodynamics.angle_of_attack = AoA[i]
                    run_conditions.freestream.mach_number            = mach[j]
                    run_conditions.freestream.velocity    = mach[j] * 340.29 #speed of sound
                    
                    #Run Analysis at AoA[i] and mach[j]
                    results =  evaluate_conditions(run_conditions)
                    
                    # Obtain CD and CL # Store other variables here as well 
                    CL[count] = results.aerodynamics.lift_coefficient
                    CD[count] = results.aerodynamics.drag_breakdown.induced.total
                    CM[count] = results.aerodynamics.pitch_moment_coefficient
 
                    count += 1
            
            time1 = time.time()
            
            print 'The total elapsed time to run SU2: '+ str(time1-time0) + '  Seconds'
        else:
            data_array = np.loadtxt(self.training_file)
            xy         = data_array[:,0:2]
            CL         = data_array[:,2:3]
            CD         = data_array[:,3:4]

        # Save the data
        np.savetxt(geometry.tag+'_data.txt',np.hstack([xy,CL,CD]),fmt='%10.8f',header='AoA Mach CL CD')

        # Store training data
        training.coefficients = np.hstack([CL,CD])
        training.grid_points  = xy
        

        return        

    def build_surrogate(self):

        # Unpack data
        training  = self.training
        AoA_data  = training.angle_of_attack
        mach_data = training.Mach
        CL_data   = training.coefficients[:,0]
        CD_data   = training.coefficients[:,1]
        xy        = training.grid_points 
        
        # Gaussian Process New
        regr_cl = gaussian_process.GaussianProcess()
        regr_cd = gaussian_process.GaussianProcess()
        cl_surrogate = regr_cl.fit(xy, CL_data)
        cd_surrogate = regr_cd.fit(xy, CD_data)          
   

        self.surrogates.lift_coefficient = cl_surrogate
        self.surrogates.drag_coefficient = cd_surrogate
        
        # Standard subsonic test case
        AoA_points = np.linspace(-1.,7.,100)*Units.deg
        mach_points = np.linspace(.25,.9,100)      
        
        AoA_mesh,mach_mesh = np.meshgrid(AoA_points,mach_points)
        
        CL_sur = np.zeros(np.shape(AoA_mesh))
        CD_sur = np.zeros(np.shape(AoA_mesh))        
        
        for jj in range(len(AoA_points)):
            for ii in range(len(mach_points)):
                CL_sur[ii,jj] = cl_surrogate.predict(np.array([AoA_mesh[ii,jj],mach_mesh[ii,jj]]))
                CD_sur[ii,jj] = cd_surrogate.predict(np.array([AoA_mesh[ii,jj],mach_mesh[ii,jj]]))
        

        fig = plt.figure('Coefficient of Lift Surrogate Plot')    
        plt_handle = plt.contourf(AoA_mesh/Units.deg,mach_mesh,CL_sur,levels=None)
        #plt.clabel(plt_handle, inline=1, fontsize=10)
        cbar = plt.colorbar()
        plt.scatter(xy[:,0]/Units.deg,xy[:,1])
        plt.xlabel('Angle of Attack (deg)')
        plt.ylabel('Mach Number')
        cbar.ax.set_ylabel('Coefficient of Lift')

        return
        
    

# ----------------------------------------------------------------------
#  Helper Functions
# ----------------------------------------------------------------------
        
def evaluate_conditions(self,run_conditions):
    """ process vehicle to setup geometry, condititon and configuration

        Inputs:
            run_conditions - DataDict() of aerodynamic conditions; until input
            method is finalized, will just assume mass_properties are always as 
            defined in self.features

        Outputs:
            results - a DataDict() of type 
            SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics(), augmented with
            case data on moment coefficients and control derivatives

        Assumptions:

    """
    
    # unpack
    run_folder      = os.path.abspath(self.settings.filenames.run_folder)
    output_template = self.settings.filenames.output_template
    batch_template  = self.settings.filenames.batch_template
    deck_template   = self.settings.filenames.deck_template
    
    # update current status
    self.current_status.batch_index += 1
    batch_index                      = self.current_status.batch_index
    self.current_status.batch_file   = batch_template.format(batch_index)
    self.current_status.deck_file    = deck_template.format(batch_index)
    
    # translate conditions
    cases                     = translate_conditions_to_cases(self,run_conditions)
    self.current_status.cases = cases        
    
    # case filenames
    for case in cases:
        case.result_filename = output_template.format(case.tag)

    # write the input files
    with redirect.folder(run_folder,force=False):
        write_geometry(self)
        write_run_cases(self)
        write_input_deck(self)

        # RUN AVL!
        results_avl = run_analysis(self)

    # translate results
    results = translate_results_to_conditions(cases,results_avl)

    if not self.keep_files:
        rmtree( run_folder )

    return results

   
    



    
    
    
    

## AVL.py
##
## Created:  Tim Momose, Dec 2014 
## Modified: Feb 2016, Andrew Wendorff
#
#
## ----------------------------------------------------------------------
##  Imports
## ----------------------------------------------------------------------
#
#import os
#import numpy as np
#from shutil import rmtree
#from warnings import warn
#
## SUAVE imports
#from SUAVE.Core import Data
#from SUAVE.Core import redirect
#
#from SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics import Aerodynamics
#from SUAVE.Analyses.Mission.Segments.Conditions.Conditions   import Conditions
#
#from SUAVE.Methods.Aerodynamics.AVL.write_geometry   import write_geometry
#from SUAVE.Methods.Aerodynamics.AVL.write_run_cases  import write_run_cases
#from SUAVE.Methods.Aerodynamics.AVL.write_input_deck import write_input_deck
#from SUAVE.Methods.Aerodynamics.AVL.run_analysis     import run_analysis
#from SUAVE.Methods.Aerodynamics.AVL.translate_data   import translate_conditions_to_cases, translate_results_to_conditions
#from SUAVE.Methods.Aerodynamics.AVL.purge_files      import purge_files
#from SUAVE.Methods.Aerodynamics.AVL.Data.Results     import Results
#from SUAVE.Methods.Aerodynamics.AVL.Data.Settings    import Settings
#from SUAVE.Methods.Aerodynamics.AVL.Data.Cases       import Run_Case
#
#from Aerodynamics import Aerodynamics as Aero_Analysis
#
#
## ----------------------------------------------------------------------
##  Class
## ----------------------------------------------------------------------
#
#class AVL(Aero_Analysis):
#    """ SUAVE.Analyses.Aerodynamics.AVL
#        aerodynamic model that performs a vortex lattice analysis using AVL
#        (Athena Vortex Lattice, by Mark Drela of MIT).
#
#        this class is callable, see self.__call__
#
#    """
#
#    def __defaults__(self):
#        self.tag        = 'avl'
#        self.keep_files = True
#
#        self.settings = Settings()
#
#        self.current_status = Data()
#        self.current_status.batch_index = 0
#        self.current_status.batch_file  = None
#        self.current_status.deck_file   = None
#        self.current_status.cases       = None
#        
#        self.features = None
#
#
#    def finalize(self):
#
#        features = self.features
#        self.tag      = 'avl_analysis_of_{}'.format(features.tag)
#
#        run_folder = self.settings.filenames.run_folder
#        if os.path.exists(run_folder):
#            if self.keep_files:
#                warn('deleting old avl run files',Warning)
#            rmtree(run_folder)
#        os.mkdir(run_folder)
#
#        return
#
#
#    def evaluate(self,state,**args):
#        
#        # unpack
#        conditions = state.conditions
#        results = self.evaluate_conditions(conditions)
#        
#        # pack conditions
#        state.conditions.aerodynamics.lift_coefficient         = results.conditions.aerodynamics.lift_coefficient
#        state.conditions.aerodynamics.drag_coefficient         = results.conditions.aerodynamics.drag_coefficient
#        state.conditions.aerodynamics.pitch_moment_coefficient = results.conditions.aerodynamics.pitch_moment_coefficient
#
#        return results
#
#
#    def evaluate_conditions(self,run_conditions):
#        """ process vehicle to setup geometry, condititon and configuration
#
#            Inputs:
#                run_conditions - DataDict() of aerodynamic conditions; until input
#                method is finalized, will just assume mass_properties are always as 
#                defined in self.features
#
#            Outputs:
#                results - a DataDict() of type 
#                SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics(), augmented with
#                case data on moment coefficients and control derivatives
#
#            Assumptions:
#
#        """
#        
#        # unpack
#        run_folder      = os.path.abspath(self.settings.filenames.run_folder)
#        output_template = self.settings.filenames.output_template
#        batch_template  = self.settings.filenames.batch_template
#        deck_template   = self.settings.filenames.deck_template
#        
#        # update current status
#        self.current_status.batch_index += 1
#        batch_index                      = self.current_status.batch_index
#        self.current_status.batch_file   = batch_template.format(batch_index)
#        self.current_status.deck_file    = deck_template.format(batch_index)
#        
#        # translate conditions
#        cases                     = translate_conditions_to_cases(self,run_conditions)
#        self.current_status.cases = cases        
#        
#        # case filenames
#        for case in cases:
#            case.result_filename = output_template.format(case.tag)
#
#        # write the input files
#        with redirect.folder(run_folder,force=False):
#            write_geometry(self)
#            write_run_cases(self)
#            write_input_deck(self)
#
#            # RUN AVL!
#            results_avl = run_analysis(self)
#
#        # translate results
#        results = translate_results_to_conditions(cases,results_avl)
#
#        if not self.keep_files:
#            rmtree( run_folder )
#
#        return results
#
#
#    def __call__(self,*args,**kwarg):
#        return self.evaluate(*args,**kwarg)
#    
#    
#    initialize = finalize
