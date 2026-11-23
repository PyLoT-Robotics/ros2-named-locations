from glob import glob
from setuptools import setup,find_packages
setup(name='named_locations',version='0.1.0',description='Named robot location recording and navigation',python_requires='>=3.10',
      packages=find_packages(exclude=['test']),install_requires=['PyYAML'],extras_require={'test': ['pytest']},
      license='Apache-2.0',maintainer='PyLoT Robotics',maintainer_email='163533636+PyLoT-Robotics@users.noreply.github.com',
      data_files=[('share/ament_index/resource_index/packages',['resource/named_locations']),
                  ('share/named_locations',['package.xml']),('share/named_locations/config',glob('config/*')),
                  ('share/named_locations/launch',glob('launch/*.py'))],
      entry_points={'console_scripts':['ros2-named-locations = named_locations.cli:main','named_locations_node = named_locations.node:main']})
