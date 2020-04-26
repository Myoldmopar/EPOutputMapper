from json import loads
from pathlib import Path
from typing import List, Set

from ovmapper.output_variable import OutputVarClassification, OutputVarLine


class SingleFile:

    def __init__(self, path_to_output_var_file: Path):
        """
        This constructor takes the path to an output_vars.csv file and validates the path and gets extra data.
        This function tries to carefully find the appropriate epJSON file.  There is one special case where the epJSON
        won't exist, but all other cases will have an epJSON path.
        :param path_to_output_var_file: pathlib.Path location of the output_vars.csv file for a single run.
        """
        self.keep = True
        self.original_output_var_file = path_to_output_var_file
        self.run_dir_in_build = path_to_output_var_file.parent
        self.idf_base_name = self.run_dir_in_build.name
        primary_expected_file = self.run_dir_in_build / (self.idf_base_name + '.epJSON')
        possible_expanded_file = self.run_dir_in_build / 'expanded.epJSON'
        possible_param_file = self.run_dir_in_build / (self.idf_base_name + '-000001.epJSON')
        possible_app_g_file = self.run_dir_in_build / (self.idf_base_name + '-G000.epJSON')
        # Gotcha: skipping the pre-converted epJSON file because the converted file will be IDF, not JSON
        known_skipped_files = ['RefBldgMediumOfficeNew2004_Chicago_epJSON']
        if primary_expected_file.exists():
            self.converted_json_file = primary_expected_file
        elif possible_expanded_file.exists():
            self.converted_json_file = possible_expanded_file
        elif possible_param_file.exists():
            self.converted_json_file = possible_param_file
        elif possible_app_g_file.exists():
            self.converted_json_file = possible_app_g_file
        elif self.idf_base_name in known_skipped_files:
            print("Skipping known-skip file: " + str(self.idf_base_name))
            self.keep = False
        else:
            print("Skipping missing epJSON file: " + str(self.idf_base_name))
            self.keep = False
        if self.keep:
            self.output_variable_data = self._cross_reference_vars_and_inputs()

    @staticmethod
    def _handle_special_var_cases(ov: OutputVarLine, o: Set[str]) -> bool:
        """
        This function handles a series of special cases based on variable information.
        :param ov: The current output variable line, as an OutputVarLine instance
        :param o: The mutable list of objects that could be associated with this output variable
        :return: A boolean flag for whether this situation has been associated and handled
        """
        var_key = ov.key
        var_type_name = ov.var_name
        initial_length_of_o = len(o)
        # Gotcha: Some output variables have keys that do not appear in the IDF, not sure what to call this input type
        known_non_object_keys = [
            'Environment', 'Simulation', 'SimHVAC', 'SimAir', 'Whole Building', 'Facility', 'Site', 'ManageDemand',
        ]
        if var_key in known_non_object_keys:
            o.add("*GLOBAL*")
        # Gotcha: Node and AFN Node variables do not need to have a specific input object
        if var_type_name.startswith('System Node '):
            o.add("*NODE*")
        if var_type_name.startswith('AFN Node '):
            o.add("*AFN NODE*")
        # Gotcha: Some objects don't have a name, and the output key is associated with the unique object's type name
        unnamed_objects_with_object_type_as_key = [
            'Site:Precipitation', 'RoofIrrigation'
        ]
        if var_key in unnamed_objects_with_object_type_as_key:
            o.add(var_key.upper())
        # Gotcha: Refrigerated Case variables use a key that is a concatenation of: "{case_name}InZone{zone_name}"
        if var_type_name.startswith("Refrigeration Walk In"):
            o.add("REFRIGERATION:WALKIN")
        # Gotcha: Int gain vars that use a zone list instead of a single zone name have name like "{zone_name} {people}"
        internal_gain_zone_list_shared_vars = ['People', 'Lights', 'Electric Equipment', 'Hot Water Equipment']
        for v in internal_gain_zone_list_shared_vars:
            if var_type_name.startswith(v + ' '):
                o.add(v.replace(' ', '').upper())
        # Gotcha: Performance curve output variables are associated with any curve type
        if var_type_name.startswith('Performance Curve '):
            o.add("*CURVE OR TABLE*")
        # Gotcha: Enclosure stuff is formed a little different too
        enclosure_vars_with_funny_keys = [
            'Daylighting Window Reference Point ', 'Zone Windows Total ',
            'Zone Interior Windows Total ', 'Zone Exterior Windows Total '
        ]
        if any([var_type_name.startswith(x) for x in enclosure_vars_with_funny_keys]):
            o.add("*ENCLOSURES*")
        return len(o) > initial_length_of_o

    @staticmethod
    def _handle_gotchas_because_of_instance_names(var_name: str, o: Set[str]) -> bool:
        """
        This function quickly maps some known variables primarily because of naming problems in the input files.
        This project is based around mining the output variables requested during a simulation then matching up the
        keys with the objects found in the input file.  This breaks down when multiple objects are named the same thing.
        In a number of example files, the zone name is used to name every internal gain in the zone.  For example:
        Zone, ZoneA, ...;  Lights, ZoneA, ...; People, ZoneA, ...;
        While this is not a problem for EnergyPlus, it does mean we cannot disambiguate the association, so this
        function does it in a brute force way.
        :param var_name: The name of the output variable: Zone Air Drybulb Temperature
        :param o: The mutable list of objects that could be associated with this output variable
        :return: A boolean flag for whether this variable name has been associated and handled
        """
        initial_length_of_o = len(o)
        if var_name.startswith('Zone '):  # Internal gains often named the same: Zone, Lights, People
            o.add('ZONE')
        elif var_name.startswith('People '):  # Internal gains often named the same: Zone, Lights, People
            o.add('PEOPLE')
        elif var_name.startswith('Lights '):  # Internal gains often named the same: Zone, Lights, People
            o.add('LIGHTS')
        elif var_name.startswith('Air System '):  # often associated with AirLoopHVAC and AirLoopHVAC:SupplyPath
            o.add('AIRLOOPHVAC')
        elif var_name.startswith('Water Use '):  # often associated with WaterUse:Equipment and WaterUse:Connections
            o.add('WATERUSE:EQUIPMENT')
        elif var_name.startswith('Steam Equipment '):  # steam and elec equipment named the same - 5ZoneWaterSystems
            o.add('STEAMEQUIPMENT')
        elif var_name.startswith('Fluid Heat Exchanger '):  # HX and SP Manager named the same - FreeCoolingChiller
            o.add('HEATEXCHANGER:FLUIDTOFLUID')
        elif var_name.startswith('Electric Load Center '):  # Generator and dist same name - GeneratorWithWindTurbine
            o.add('ElectricLoadCenter:Distribution')
        elif var_name.startswith('Room Air Zone '):  # Zone name used for room air model and others - UserDefRoomAirPatt
            o.add('ZONE')
        elif var_name.startswith('RoomAirflowNetwork Node '):  # RoomAirNode and Intrazone node - RoomAirflowNetwork
            o.add('ROOMAIR:NODE:AIRFLOWNETWORK')
        elif var_name.startswith('Refrigeration Zone Case and Walk In'):
            # zone, people given same name in ASHRAE9012016_RestaurantFastFood_Denver - should just be a zone
            o.add('ZONE')
        elif var_name.startswith('Surface Other Side Conditions '):
            # Surface Prop Other side Conditions Model and Surface Prop * named the same, just use the OSCM
            o.add('SURFACEPROPERTY:OTHERSIDECONDITIONSMODEL')
        elif var_name.startswith('Schedule Value'):
            # schedule:day:hourly and schedule:year given the same name in HAMT_DailyProfileReport, but it maps to four
            o.add('SCHEDULE:YEAR')
            o.add('SCHEDULE:COMPACT')
            o.add('SCHEDULE:FILE')
            o.add('SCHEDULE:CONSTANT')
        elif var_name.startswith('Unitary System '):  # AirLoop Unitary object and AirLoopHVAC sometimes named the same
            o.add('*UNITARY*')
        elif var_name.startswith('Availability Manager Hybrid Ventilation Control '):
            # given the same name with people and zone in FanCoil_HybridVent_VentSch, but really it maps to two objects
            o.add('AIRLOOPHVAC')
            o.add('ZONE')
        return len(o) > initial_length_of_o

    def _cross_reference_vars_and_inputs(self) -> List[OutputVarClassification]:
        """
        This function takes a single output_vars generated csv file and parses it into a list of output variable data.
        Then it takes the epJSON representation of the input file and gathers a small dict of object {type => instance}
        It then loops over all output variables and tries to find the input object that matches the output variable by
        matching the output variable key with an input object instance name.  There are a couple dozen gotchas that are
        handled along the way because of object naming problems, output variable corner cases, etc.
        :return: A list of output variable classes, which contain the full set of likely input objects for each var.
        """
        all_output_vars_this_file = list()
        var_name_list = list()
        with open(str(self.original_output_var_file)) as f:
            for line in f.readlines():
                if line.strip():
                    var = OutputVarLine(line)
                    if var.keep and var.var_name not in var_name_list:
                        var_name_list.append(var.var_name)
                        all_output_vars_this_file.append(var)
        with open(str(self.converted_json_file)) as f:
            input_file_object = loads(f.read())
        objects_and_instance_names = dict()
        for obj_type, instance_dict in input_file_object.items():
            names = list()
            for instance_name, instance_fields in instance_dict.items():
                # Gotcha: The newer VRF object does not have a name, it uses heat_pump_name
                if obj_type == 'AirConditioner:VariableRefrigerantFlow:FluidTemperatureControl':
                    names.append(instance_fields['heat_pump_name'])
                else:
                    names.append(instance_name)
            objects_and_instance_names[obj_type] = names
        classifications = []
        for output_var in all_output_vars_this_file:
            o = OutputVarClassification(output_var.var_name.upper())
            if self._handle_special_var_cases(output_var, o.possible_input_objects):
                continue
            if not self._handle_gotchas_because_of_instance_names(output_var.var_name, o.possible_input_objects):
                for obj_type, instance_names in objects_and_instance_names.items():
                    if obj_type.upper().startswith('COMPONENTCOST') or obj_type.upper().startswith('ENERGYMANAGEMENT'):
                        # Gotcha: ComponentCost is not associated with a report variable, but is sometimes named
                        #         the same as the associated input objects, so need to just skip this variable
                        # Gotcha: EnergyManagementSystem:OutputVariable objects are all custom, not linked to one input
                        continue
                    for instance_name in instance_names:
                        if instance_name.upper() == output_var.key.upper():
                            o.possible_input_objects.add(obj_type.upper())
            classifications.append(o)
        return classifications
