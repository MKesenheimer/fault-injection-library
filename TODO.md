# TODOs

* implement sigrok integration to trigger a logic analyzer capture during glitching
* sigrok macos installation:
    $ sudo port install libzip libftdi libusb libtool glibmm doxygen autoconf-archive sdcc boost cmake autoconf automake swig check qt5
    $ git clone git://sigrok.org/sigrok-util
    $ cd sigrok-util/cross-compile/macosx
    $ ./sigrok-native-macosx
* build functions to automatically recognize the PicoGlitcher board, if it is plugged in
* implement a "findus-launcher" that handles all the common things, like command line parsing, database setup and so on. The user should only provide the handles for classification, and the contents of the glitching loop.
* make use of the analog input

* Reduce dependencies even more
* remove annoying message that rd6006 is not installed (make ExternalPowerSupply an separate module and import it if necessary)
* remove numpy dependency