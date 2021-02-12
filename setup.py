#!/usr/bin/env python
"""
    webchecker
    Checks a website and records this into a Postgres DB via kafka.

    https://github.com/agustinhenze/webchecker
"""
from distutils.core import setup


setup(name='Webchecker',
      version='1.0',
      description='Web page checker',
      author='Agustin Henze',
      author_email='tin@aayy.com.ar',
      url='https://github.com/agustinhenze/webchecker',
      packages=['src'],
      )
