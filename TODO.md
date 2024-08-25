# TODOs

* implement sigrok integration to trigger a logic analyzer capture during glitching
* sigrok macos installation:
    $ sudo port install libzip libftdi libusb libtool glibmm doxygen autoconf-archive sdcc boost cmake autoconf automake swig check qt5
    $ git clone git://sigrok.org/sigrok-util
    $ cd sigrok-util/cross-compile/macosx
    $ ./sigrok-native-macosx