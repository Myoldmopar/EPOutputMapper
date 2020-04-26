# EPOutputMapper
A mapping library for output variables in EnergyPlus.

# Running
 - Generate a release build of EnergyPlus from the *** branch
   - this branch has two changes: it writes out all output variable requests to output_vars.csv, and
   - it has a -c argument in the energyplus cmake test commands, so that energyplus will write an epJSON file
 - Run all integration files from the build dir:
   - `cd build/dir`
   - `ctest -R integration* -j 8`
 - Run this script using `python setup.py map`, which will
   - find all output_var.csv files
   - mine the contents of each, along with the contents of the matching epJSON file
   - match up output var requests with object types in the IDF
   - collapse that down into a unique list
   - report it as a JSON blob
