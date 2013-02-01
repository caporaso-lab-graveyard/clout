#!/usr/bin/env python
from __future__ import division

__author__ = "Jai Ram Rideout"
__copyright__ = "Copyright 2012-2013, The Clout Project"
__credits__ = ["Jai Ram Rideout"]
__license__ = "GPLv2"
__version__ = "0.9-dev"
__maintainer__ = "Jai Ram Rideout"
__email__ = "jai.rideout@gmail.com"

from sys import stderr, version_info
from distutils.core import setup

long_description = """
Clout: Cloud-based Automated Testing
http://qiime.org/clout
"""
 
if version_info < (2, 5):
    print >> stderr, "Error: Clout requires Python 2.5 or newer."
    exit(1)

setup(name='Clout',
      version=__version__,
      license=__license__,
      description='Cloud-based Automated Testing',
      long_description=long_description,
      author=__author__,
      author_email=__email__,
      maintainer=__maintainer__,
      maintainer_email=__email__,
      url='http://qiime.org/clout',
      packages=['clout'],
      scripts=['scripts/clout'])
