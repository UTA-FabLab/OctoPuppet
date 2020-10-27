storage module
==============

Working:
""""""""
The storage.py uses a couple of predefined abstract functions to access the Local File Storage. 
This holds all the files, folders and metadata related to OctoPuppet. Metadata is managed by ``metadata.yaml`` files in the respective 
folders, indexed by sanitized filenames stored within the folder.

Data Model:
"""""""""""
The fields listed below are updated in the metadata storage for OctoPuppet.
The data values listed below are fed to the metadata for every print command issued;
values are extracted from the gcode.

.. csv-table:: 
   :header: "Key", "Description"
   :widths: 20, 20

   "``estimatedPrintTime``", "Estimated time the file takes to print, in minutes"
   "``filament``", "Substructure describing estimated filament usage. Keys are ``tool0`` for the first extruder, ``tool1`` for the second and so on. For each tool extruded length and volume (based on diameter) are provided."
   "``filament.toolX.length``", "The extruded length in mm"
   "``filament.toolX.volume``", "The extruded volume in cm³"


.. automodule:: storage
   :members:
   :undoc-members:
   :show-inheritance:
