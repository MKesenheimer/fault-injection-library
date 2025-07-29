#include <stdio.h>
#include <stdint.h>
#include <string>
#include <sstream>
#include <iostream>
#include <time.h>

#include "pico/stdlib.h"
#include "hardware/irq.h"

#define add1 "add r0, r0, #1;"
#define add2 add1 add1
#define add4 add2 add2
#define add8 add4 add4
#define add16 add8 add8
#define add32 add16 add16
#define add64 add32 add32
#define add128 add64 add64
#define add256 add128 add128

uint32_t save_and_disable_interrupts() {
    uint32_t primask;
    __asm volatile(
        "MRS %0, PRIMASK; "
        "CPSID i; "
        : "=r" (primask)
        :
        : "memory"
    );
    return primask;
}

void restore_interrupts(uint32_t primask) {
    __asm volatile(
        "MSR PRIMASK, %0; "
        :
        : "r" (primask)
        : "memory"
    );
}

int unrolled_loop() {

    uint32_t counter = 0;

    gpio_put(PICO_DEFAULT_LED_PIN, 1);
    gpio_put(0, 1);

    asm volatile (
        "ldr r0, =0;"
        add256
        "str r0, %[cnt];"        // store R0 into the variable 'result'
        : [cnt] "=m" (counter)   // output operand
        :                        // no input operands
        : "r0"                   // clobbers (R0 register)
    );

    gpio_put(0, 0);
    gpio_put(PICO_DEFAULT_LED_PIN, 0);

    return counter;
}

int main() {
    // setup
    stdio_init_all();
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
    gpio_init(0);
    gpio_set_dir(0, GPIO_OUT);

    // init usb
    stdio_usb_init();
    // blink until usb is connected
    while (!stdio_usb_connected()) {
        gpio_put(PICO_DEFAULT_LED_PIN, 1);
        sleep_ms(250);
        gpio_put(PICO_DEFAULT_LED_PIN, 0);
        sleep_ms(250);
    }

    std::cout << "RP2040 Test Program" << std::endl;

    std::cout << "send something to start the counter." <<std::endl;
    int recv = 0;
    while (true) {
        std::string line;
        std::getline(std::cin, line);
        uint32_t primask = save_and_disable_interrupts();
        int counter = unrolled_loop();
        restore_interrupts(primask);
        std::cout << "XXX" << counter << "YYY" << counter << "ZZZ" << std::endl;
        std::cout << std::flush;
    }

    std::cout << "Jumped out of loop." << std::endl;
    return 0;
}