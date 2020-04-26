from typing import Union, Set


class OutputVarLine:
    """
    This class represents a single line in an output_vars file, which represents a single call into SetupOutputVariable
    during a simulation run
    """

    def __init__(self, line: str):
        """
        This constructor will simply parse a CSV line from the output_vars.csv file, and assign values to member
        variables.  One special case is handled: EMS keys are eliminated from contention at this point.
        :param line: A CSV line from an output_vars.csv file.
        """
        self.keep = True
        try:
            tokens = line.strip().split(',')
            self.var_name = tokens[0]
            self.units = tokens[1]
            self.time_step = tokens[2]
            self.key = tokens[3]
            if self.key == 'EMS':
                # Gotcha: EMS keys are for custom output variables and should be skipped
                self.keep = False
        except Exception as e:
            print("Could not process output var CSV line: \"" + line + "\"")
            print("Reason: " + str(e))
            self.keep = False


class OutputVarClassification:
    """
    This class represents an output variable and all input objects that are (likely) associated with this output.
    """
    def __init__(self, output_variable_name: str, found_types: Union[None, Set[str]] = None):
        """
        This constructor takes the variable name for direct assignment, and then optionally a list of already found
        input object types to store.
        :param output_variable_name: Name of the output variable
        :param found_types: If not passed in, a new set() is created, but if a list is passed in, it is used to
                            initialize a new list with this starting point.
        """
        self.output_variable_name = output_variable_name
        if found_types:
            self.possible_input_objects = found_types
        else:
            self.possible_input_objects = set()

    def __str__(self) -> str:
        """
        Simple debugging descriptor method.
        :return: String description.
        """
        return "%s : [%s]" % (self.output_variable_name, ','.join([x for x in self.possible_input_objects]))

    def to_object(self) -> dict:
        """
        Converts this object instance into a dict() for JSON serialization.
        :return: A dict with the variable name as the key and a plain Python list holding the input object type names.
        """
        return {self.output_variable_name: list(self.possible_input_objects)}
