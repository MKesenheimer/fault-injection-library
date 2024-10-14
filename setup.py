from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='findus',
   version='0.9',
   description='Library to perform fault injection attacks with the PicoGlitcher, Chipwhisperer Husky or Chipwhisperer Pro',
   license="GPL",
   long_description=long_description,
   url="https://mkesenheimer.github.io/blog/pico-glitcher-pcb.html",
   author='Matthias Kesenheimer',
   author_email='m.kesenheimer@gmx.net',
   packages=['findus'],
   install_requires=['setuptools', 'adafruit-ampy', 'pyserial', 'termcolor', 'plotly', 'pandas', 'dash', 'dash_bootstrap_components', 'chipwhisperer', 'minimalmodbus'],
   scripts=[]
)