# Raspberry Pico Test Program
Set up raspberry pi pico projects according the official [documentation](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico).

Build and flash the project:
```
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j4
picotool load rpi-test.bin -f && picotool reboot
```

