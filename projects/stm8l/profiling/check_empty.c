#include <stdint.h>
#include "./stm8l.h"

#define TRIG_PIN (1 << 1) // PB1
#define SUCCESS_PIN (1 << 4) // PB4
#define EXPECTED_PIN (1 << 5) // PB5

void main(void)
{
    CLK_PCKENR1 = 0xff;

    // set output
	PB_DDR |= TRIG_PIN | SUCCESS_PIN | EXPECTED_PIN; // PB1, PB4, PB5 as outputs
	PB_CR1 |= TRIG_PIN | SUCCESS_PIN | EXPECTED_PIN; // push-pull
	PB_CR2 |= TRIG_PIN | SUCCESS_PIN | EXPECTED_PIN; // fast

    // Create trigger on PB1
    PB_ODR |= TRIG_PIN;

    // The first part of the bootloader: getting to rdp_check
__asm
	sim
	ld A, 0x8000
	cp A, #0x82
	jreq bootl_check
	cp A, #0xac
	jreq bootl_check
	jra rdp_check

bootl_check:
	ld A, 0x480b
	cp A, #0x55
	jreq rdp_check
	jra enter_app 

rdp_check:
    bset 0x5005, #0x4 // Set success pin (PB4) to indicate RDP check
    jra asm_done

enter_app:
	bset 0x5005, #0x5 // Set expected pin (PB5)

asm_done:
    nop
__endasm;

#ifdef ALWAYS_SUCCESS
__asm
	bset 0x5005, #0x4 // Set success pin (PB4)
__endasm;
#endif

    for (;;)
        ;
}