import distutils.cmd
import distutils.log
from pathlib import Path
from setuptools import setup

from ovmapper.processor import OutputVariableMapper


class Mapper(distutils.cmd.Command):
    """A custom command to run Mapping operations"""

    description = 'Run E+ output variable mapping process'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        sch = OutputVariableMapper(
            Path('/eplus/repos/4eplus/builds/r')  # TODO: Make this path into arg
        )
        output_path = Path('.') / '_build'
        output_path.mkdir(exist_ok=True)
        sch.dump_results(output_path)


setup(
    name='EnergyPlus Output Variable Mapper',
    version='0.1',
    packages=['ovmapper'],
    url='https://github.com/Myoldmopar/EPOutputMapper',
    license='',
    author='Edwin Lee',
    author_email='',
    description='',
    cmdclass={
        'map': Mapper,
    },
)
