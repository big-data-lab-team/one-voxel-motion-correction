import sys
from setuptools import setup
import sys

VERSION = "0.1"
DEPS = ["nibabel", "boutiques", "termcolor"]

setup(name="ovmc",
      version=VERSION,
      description="Scripts for one-voxel experiment on fMRI motion correction",
      url=("https://github.com/big-data-lab-team/"
           "one-voxel-motion-correction.git"),
      author="Tristan Glatard",
      classifiers=[
                "Programming Language :: Python",
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.4",
                "Programming Language :: Python :: 3.5",
                "Programming Language :: Python :: 3.6",
                "Programming Language :: Python :: 3.7",
                "Programming Language :: Python :: Implementation :: PyPy",
                "License :: OSI Approved :: GPL License",
                "Topic :: Software Development :: Libraries :: Python Modules",
                "Operating System :: OS Independent",
                "Natural Language :: English"
                  ],
      license="GPL",
      packages=["ovmc"],
      include_package_data=True,
      test_suite="pytest",
      tests_require=["pytest"],
      setup_requires=DEPS,
      install_requires=DEPS,
      entry_points={
        "console_scripts": [
            "one_voxel=ovmc:one_voxel",
            "ovmc=ovmc:ovmc",
        ]
      },
      zip_safe=False)
