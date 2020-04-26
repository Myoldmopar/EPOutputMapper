from json import dumps
from pathlib import Path
from time import time
from typing import Dict, List, Set

from ovmapper.input_file import SingleFile
from ovmapper.output_variable import OutputVarClassification


class OutputVariableMapper:
    """
    This class mines out results of test runs, and cross references them with input file contents, in order to create
    an output variable "schema".  For now, this is just a list of a mapping between input objects and output variable
    names so that interfaces can use this information to figure out what output variables are available for different
    input objects prior to a simulation.
    """

    def __init__(self, path_to_build_dir: Path):
        """
        This constructor takes the path to a build directory and processes output variable map files.
        :param path_to_build_dir: Path to a build directory where the build was created using the `GenerateReportSchema`
                                  branch and `ctest -R "integration*"` has been executed

        """
        self.build_dir = path_to_build_dir
        self.all_files = self._get_all_applicable_files()
        self.final_mapping = self._down_select_object_types()
        self.inverted_map = self._invert_mapping()

    def dump_results(self, output_dir: Path) -> None:
        """
        Dumps mapping results files to the output directory specified
        :param output_dir: The output directory to dump the map files
        :return: Nothing
        """
        ov_to_object_path = output_dir / 'output_var_to_object_map.json'
        object_to_ov_path = output_dir / 'object_to_output_var_map.json'
        print("Creating OV->OBJECT map at %s" % ov_to_object_path)
        with open(str(ov_to_object_path), 'w') as f:
            json_data = {'OutputVariables': [x.to_object() for x in self.final_mapping]}
            json_string = dumps(json_data, indent=2)
            f.write(json_string)
        print("Creating OBJECT->OV map at %s" % object_to_ov_path)
        with open(str(object_to_ov_path), 'w') as f:
            json_data = {'OutputVariables': self.inverted_map}
            json_string = dumps(json_data, indent=2)
            f.write(json_string)

    def _get_all_applicable_files(self) -> List[SingleFile]:
        """
        This function finds all folders in the build directory that include an output_vars.csv file, as this is the clue
        that this file was run with the special branch and has output variable data to process.  This only adds the file
        to the master list if the file is valid (the file .keep flag is true)
        :return: A list of SingleFile instances, all with an output_vars.csv path and an epJSON input file path.
        """
        s: List[SingleFile] = list()
        test_file_dir = self.build_dir / 'testfiles'
        i = 0
        t_initial = time()
        test_dirs = [x for x in test_file_dir.iterdir() if x.is_dir()]
        num_dirs = len(test_dirs)
        for test_dir in test_dirs:
            i += 1
            t_passed = time() - t_initial
            print("Processing dir # %i/%i (total time = %is) - \"%s\"" % (i, num_dirs, round(t_passed), test_dir.name))
            output_var_path = test_dir / 'output_vars.csv'
            if output_var_path.exists():
                f = SingleFile(output_var_path)
                if f.keep:
                    s.append(f)
        return s

    def _down_select_object_types(self) -> List[OutputVarClassification]:
        """
        This function takes the huge list of all output variable to input object mappings for all files and creates a
        new list that finds all unique matches for each output variable.  This is presumably the master list of
        output variable to input object mappings.
        :return: A list of output variable classifications with all file data collapsed into a single list.
        """
        output_variable_objects: Dict[str, Set[str]] = dict()
        for input_file in self.all_files:  # loop over all input files to try to collect all info
            for output in input_file.output_variable_data:  # loop over all output variables to find type matches
                if output.output_variable_name not in output_variable_objects:
                    output_variable_objects[output.output_variable_name] = set()
                for this_possible_input_object in output.possible_input_objects:
                    output_variable_objects[output.output_variable_name].add(this_possible_input_object)
        all_output_vars: List[OutputVarClassification] = list()
        for var_name, objects in output_variable_objects.items():
            all_output_vars.append(OutputVarClassification(var_name, objects))
        return all_output_vars

    def _invert_mapping(self) -> Dict[str, List[str]]:
        """
        This function takes the completed mapping of output variable to input objects and inverts it so that it returns
        a list of input objects with all the identified output variables for that input object.  This is likely the form
        most interfaces would want to see.
        :return: A plain Python dict where keys are string input objects and values are lists of output variable names.
        """
        object_to_ov_map = dict()
        for ov in self.final_mapping:
            for obj_type in ov.possible_input_objects:
                if obj_type not in object_to_ov_map:
                    object_to_ov_map[obj_type] = [ov.output_variable_name]
                else:
                    if ov not in object_to_ov_map[obj_type]:
                        object_to_ov_map[obj_type].append(ov.output_variable_name)
        return object_to_ov_map
