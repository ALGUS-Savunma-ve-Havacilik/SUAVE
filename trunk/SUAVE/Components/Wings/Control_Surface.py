# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import numpy as np

from SUAVE.Core import Data, Data_Exception, Data_Warning
from SUAVE.Components import Component, Physical_Component, Lofted_Body, Mass_Properties

# ------------------------------------------------------------
#  Control Surfaces
# ------------------------------------------------------------

class Control_Surface(Lofted_Body):
    def __defaults__(self):
        self.tag    = 'control_surface'
        self.span   = 0.0
        self.span_fraction = 0.0
        self.deflection_symmetry = 1.0
        self.origin = [0.0,0.0,0.0]
        self.transformation_matrix = [[1,0,0],[0,1,0],[0,0,1]]

        self.sections = Data()
        

    def append_section(self,section):
        """adds a component to vehicle """

        # assert database type
        if not isinstance(section,Data):
            raise Component_Exception, 'input control surface section must be of type Data()'

        # store data
        self.sections.append(section)

        return



class Control_Surface_Section(Lofted_Body.Section):
    def __defaults__(self):
        self.tag    = 'control_section'
        self.chord  = 0.0
        self.chord_fraction = 0.0
        self.twist  = 0.0 # Offset / deflection in neutral position

        self.origins = Data()
        self.origins.dimensional    = [0.0,0.0,0.0]
        self.origins.span_fraction  = 0.0
        self.origins.chord_fraction = 0.0

        self.points = Data()
        self.points.leading_edge =  0.0
        self.points.trailing_edge = 0.0
