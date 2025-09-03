#define F_CPU 16000000UL  // 16 MHz
#include <avr/io.h>
#include <util/delay.h>

int main(void) {
    DDRB |= (1 << PB5);  // set PB5 as output

    while (1) {
        PORTB ^= (1 << PB5); // toggle LED
        _delay_ms(100);      // 500 ms delay
    }
}