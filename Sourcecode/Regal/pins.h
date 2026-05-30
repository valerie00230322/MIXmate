// pins.h
#pragma once
#include <avr/io.h>

// ------------------------------------------------------------
// Generic helpers: use like PIN_OUTPUT(lift_STEP), PIN_HIGH(...)
// ------------------------------------------------------------
#define PIN_OUTPUT(sig)     do { sig##_DDR  |=  _BV(sig##_BIT); } while (0)
#define PIN_INPUT(sig)      do { sig##_DDR  &= ~_BV(sig##_BIT); } while (0)

#define PIN_HIGH(sig)       do { sig##_PORT |=  _BV(sig##_BIT); } while (0)
#define PIN_LOW(sig)        do { sig##_PORT &= ~_BV(sig##_BIT); } while (0)
#define PIN_TOGGLE(sig)     do { sig##_PORT ^=  _BV(sig##_BIT); } while (0)

#define PIN_PULLUP_ON(sig)  do { sig##_PORT |=  _BV(sig##_BIT); } while (0)
#define PIN_PULLUP_OFF(sig) do { sig##_PORT &= ~_BV(sig##_BIT); } while (0)

#define PIN_READ(sig)       ((sig##_PIN & _BV(sig##_BIT)) != 0)


// ============================================================
// Motor-Signale
// ============================================================

// ---------------- Motor 1 ----------------
#define lift_STEP_DDR   DDRB
#define lift_STEP_PORT  PORTB
#define lift_STEP_PIN   PINB
#define lift_STEP_BIT   PB5

#define lift_DIR_DDR    DDRA
#define lift_DIR_PORT   PORTA
#define lift_DIR_PIN    PINA
#define lift_DIR_BIT    PA0

#define lift_DIAG_DDR   DDRF
#define lift_DIAG_PORT  PORTF
#define lift_DIAG_PIN   PINF
#define lift_DIAG_BIT   PF0

// Arduino pin numbers for AccelStepper
#define STEP_PIN_lift   11
#define DIR_PIN_lift    22


// ---------------- Motor 3 ----------------
#define lift_band_STEP_DDR  DDRB
#define lift_band_STEP_PORT PORTB
#define lift_band_STEP_PIN  PINB
#define lift_band_STEP_BIT  PB7

#define lift_band_DIR_DDR   DDRA
#define lift_band_DIR_PORT  PORTA
#define lift_band_DIR_PIN   PINA
#define lift_band_DIR_BIT   PA2

#define lift_band_DIAG_DDR  DDRH
#define lift_band_DIAG_PORT PORTH
#define lift_band_DIAG_PIN  PINH
#define lift_band_DIAG_BIT  PH2

// Arduino pin numbers for AccelStepper
#define STEP_PIN_lift_band 13
#define DIR_PIN_lift_band  24


// ---------------- Motor 4 (STEP über X4_1) ----------------
#define MOTOR4_STEP_DDR   DDRE
#define MOTOR4_STEP_PORT  PORTE
#define MOTOR4_STEP_PIN   PINE
#define MOTOR4_STEP_BIT   PE0

#define MOTOR4_DIR_DDR    DDRA
#define MOTOR4_DIR_PORT   PORTA
#define MOTOR4_DIR_PIN    PINA
#define MOTOR4_DIR_BIT    PA3

#define MOTOR4_DIAG_DDR   DDRH
#define MOTOR4_DIAG_PORT  PORTH
#define MOTOR4_DIAG_PIN   PINH
#define MOTOR4_DIAG_BIT   PH3

// Arduino pin numbers for AccelStepper
#define STEP_PIN_MOTOR4   0
#define DIR_PIN_MOTOR4    25


// ---------------- Motor 5 (STEP über X4_2) ----------------
#define MOTOR5_STEP_DDR   DDRE
#define MOTOR5_STEP_PORT  PORTE
#define MOTOR5_STEP_PIN   PINE
#define MOTOR5_STEP_BIT   PE1

#define MOTOR5_DIR_DDR    DDRA
#define MOTOR5_DIR_PORT   PORTA
#define MOTOR5_DIR_PIN    PINA
#define MOTOR5_DIR_BIT    PA4

#define MOTOR5_DIAG_DDR   DDRG
#define MOTOR5_DIAG_PORT  PORTG
#define MOTOR5_DIAG_PIN   PING
#define MOTOR5_DIAG_BIT   PG0

// Arduino pin numbers for AccelStepper
#define STEP_PIN_MOTOR5   1
#define DIR_PIN_MOTOR5    26


// ---------------- Motor 6 (STEP über X4_4) ----------------
#define MOTOR6_STEP_DDR   DDRE
#define MOTOR6_STEP_PORT  PORTE
#define MOTOR6_STEP_PIN   PINE
#define MOTOR6_STEP_BIT   PE3

#define MOTOR6_DIR_DDR    DDRA
#define MOTOR6_DIR_PORT   PORTA
#define MOTOR6_DIR_PIN    PINA
#define MOTOR6_DIR_BIT    PA5

#define MOTOR6_DIAG_DDR   DDRG
#define MOTOR6_DIAG_PORT  PORTG
#define MOTOR6_DIAG_PIN   PING
#define MOTOR6_DIAG_BIT   PG1

#define STEP_PIN_MOTOR6   5
#define DIR_PIN_MOTOR6    27


// ---------------- Wartepositionsband (Motor 7) ----------------
#define wait_band_STEP_DDR   DDRH
#define wait_band_STEP_PORT  PORTH
#define wait_band_STEP_PIN   PINH
#define wait_band_STEP_BIT   PH3

#define wait_band_DIR_DDR    DDRA
#define wait_band_DIR_PORT   PORTA
#define wait_band_DIR_PIN    PINA
#define wait_band_DIR_BIT    PA6

#define wait_band_DIAG_DDR   DDRG
#define wait_band_DIAG_PORT  PORTG
#define wait_band_DIAG_PIN   PING
#define wait_band_DIAG_BIT   PG2

#define STEP_PIN_wait_band   6
#define DIR_PIN_wait_band    28


// ---------------- Ebene 2 (Motor 8) ----------------
#define Ebene2_STEP_DDR   DDRH
#define Ebene2_STEP_PORT  PORTH
#define Ebene2_STEP_PIN   PINH
#define Ebene2_STEP_BIT   PH4

#define Ebene2_DIR_DDR    DDRA
#define Ebene2_DIR_PORT   PORTA
#define Ebene2_DIR_PIN    PINA
#define Ebene2_DIR_BIT    PA7

#define Ebene2_DIAG_DDR   DDRG
#define Ebene2_DIAG_PORT  PORTG
#define Ebene2_DIAG_PIN   PING
#define Ebene2_DIAG_BIT   PG3

#define STEP_PIN_Ebene2   7
#define DIR_PIN_Ebene2    29


// ---------------- Ebene 1 (Motor 9) ----------------
#define Ebene1_STEP_DDR   DDRH
#define Ebene1_STEP_PORT  PORTH
#define Ebene1_STEP_PIN   PINH
#define Ebene1_STEP_BIT   PH5

#define Ebene1_DIR_DDR    DDRC
#define Ebene1_DIR_PORT   PORTC
#define Ebene1_DIR_PIN    PINC
#define Ebene1_DIR_BIT    PC0

#define Ebene1_DIAG_DDR   DDRG
#define Ebene1_DIAG_PORT  PORTG
#define Ebene1_DIAG_PIN   PING
#define Ebene1_DIAG_BIT   PG4

#define STEP_PIN_Ebene1   8
#define DIR_PIN_Ebene1    37


// ---------------- Motor 10 ----------------
#define MOTOR10_STEP_DDR   DDRL
#define MOTOR10_STEP_PORT  PORTL
#define MOTOR10_STEP_PIN   PINL
#define MOTOR10_STEP_BIT   PL3

#define MOTOR10_DIR_DDR    DDRC
#define MOTOR10_DIR_PORT   PORTC
#define MOTOR10_DIR_PIN    PINC
#define MOTOR10_DIR_BIT    PC1

#define MOTOR10_DIAG_DDR   DDRG
#define MOTOR10_DIAG_PORT  PORTG
#define MOTOR10_DIAG_PIN   PING
#define MOTOR10_DIAG_BIT   PG5

#define STEP_PIN_MOTOR10   46
#define DIR_PIN_MOTOR10    36


// ---------------- Motor 11 ----------------
#define MOTOR11_STEP_DDR   DDRL
#define MOTOR11_STEP_PORT  PORTL
#define MOTOR11_STEP_PIN   PINL
#define MOTOR11_STEP_BIT   PL4

#define MOTOR11_DIR_DDR    DDRC
#define MOTOR11_DIR_PORT   PORTC
#define MOTOR11_DIR_PIN    PINC
#define MOTOR11_DIR_BIT    PC2

#define MOTOR11_DIAG_DDR   DDRH
#define MOTOR11_DIAG_PORT  PORTH
#define MOTOR11_DIAG_PIN   PINH
#define MOTOR11_DIAG_BIT   PH6

#define STEP_PIN_MOTOR11   45
#define DIR_PIN_MOTOR11    35


// ---------------- Motor 12 ----------------
#define MOTOR12_STEP_DDR  DDRL
#define MOTOR12_STEP_PORT PORTL
#define MOTOR12_STEP_PIN  PINL
#define MOTOR12_STEP_BIT  PL5

#define MOTOR12_DIR_DDR   DDRC
#define MOTOR12_DIR_PORT  PORTC
#define MOTOR12_DIR_PIN   PINC
#define MOTOR12_DIR_BIT   PC3

#define MOTOR12_DIAG_DDR  DDRH
#define MOTOR12_DIAG_PORT PORTH
#define MOTOR12_DIAG_PIN  PINH
#define MOTOR12_DIAG_BIT  PH7

#define STEP_PIN_MOTOR12  44
#define DIR_PIN_MOTOR12   34


// ---------------- EN ----------------
#define EN_DDR   DDRL
#define EN_PORT  PORTL
#define EN_PIN   PINL
#define EN_BIT   PL6


// ============================================================
// Klemmen X1..X4
// ============================================================

// ---------------- X1 (PJ2..PJ5) ----------------
#define X1_1_DDR   DDRJ
#define X1_1_PORT  PORTJ
#define X1_1_PIN   PINJ
#define X1_1_BIT   PJ2

#define X1_2_DDR   DDRJ
#define X1_2_PORT  PORTJ
#define X1_2_PIN   PINJ
#define X1_2_BIT   PJ3

#define X1_3_DDR   DDRJ
#define X1_3_PORT  PORTJ
#define X1_3_PIN   PINJ
#define X1_3_BIT   PJ4

#define X1_4_DDR   DDRJ
#define X1_4_PORT  PORTJ
#define X1_4_PIN   PINJ
#define X1_4_BIT   PJ5


// ---------------- X2 (PK0..PK3) ----------------
#define X2_1_DDR   DDRK
#define X2_1_PORT  PORTK
#define X2_1_PIN   PINK
#define X2_1_BIT   PK0

#define X2_2_DDR   DDRK
#define X2_2_PORT  PORTK
#define X2_2_PIN   PINK
#define X2_2_BIT   PK1

#define X2_3_DDR   DDRK
#define X2_3_PORT  PORTK
#define X2_3_PIN   PINK
#define X2_3_BIT   PK2

#define X2_4_DDR   DDRK
#define X2_4_PORT  PORTK
#define X2_4_PIN   PINK
#define X2_4_BIT   PK3


// ---------------- X3 (PK4..PK7) ----------------
#define X3_1_DDR   DDRK
#define X3_1_PORT  PORTK
#define X3_1_PIN   PINK
#define X3_1_BIT   PK4

#define X3_2_DDR   DDRK
#define X3_2_PORT  PORTK
#define X3_2_PIN   PINK
#define X3_2_BIT   PK5

#define X3_3_DDR   DDRK
#define X3_3_PORT  PORTK
#define X3_3_PIN   PINK
#define X3_3_BIT   PK6

#define X3_4_DDR   DDRK
#define X3_4_PORT  PORTK
#define X3_4_PIN   PINK
#define X3_4_BIT   PK7


// ---------------- X4 (PE0..PE3) ----------------
#define X4_1_DDR   DDRE
#define X4_1_PORT  PORTE
#define X4_1_PIN   PINE
#define X4_1_BIT   PE0

#define X4_2_DDR   DDRE
#define X4_2_PORT  PORTE
#define X4_2_PIN   PINE
#define X4_2_BIT   PE1

#define X4_3_DDR   DDRE
#define X4_3_PORT  PORTE
#define X4_3_PIN   PINE
#define X4_3_BIT   PE2

#define X4_4_DDR   DDRE
#define X4_4_PORT  PORTE
#define X4_4_PIN   PINE
#define X4_4_BIT   PE3


// ============================================================
// Aliase für Sensoren (damit PIN_* Makros sauber funktionieren)
// HOME = X1_4
// ============================================================
#define HOME_DDR   X1_4_DDR
#define HOME_PORT  X1_4_PORT
#define HOME_PIN   X1_4_PIN
#define HOME_BIT   X1_4_BIT

// ============================================================
// Regal-Sensoren (digitale Belegungssignale)
// Die Logik (LOW oder HIGH = belegt) wird in Regal.ino ueber
// SENSOR_ACTIVE_LOW konfiguriert.
// ============================================================
#define SENS_LEVEL1_FRONT_DDR   X2_1_DDR
#define SENS_LEVEL1_FRONT_PORT  X2_1_PORT
#define SENS_LEVEL1_FRONT_PIN   X2_1_PIN
#define SENS_LEVEL1_FRONT_BIT   X2_1_BIT

#define SENS_LEVEL2_FRONT_DDR   X2_2_DDR
#define SENS_LEVEL2_FRONT_PORT  X2_2_PORT
#define SENS_LEVEL2_FRONT_PIN   X2_2_PIN
#define SENS_LEVEL2_FRONT_BIT   X2_2_BIT

#define SENS_LIFT_DDR           X2_3_DDR
#define SENS_LIFT_PORT          X2_3_PORT
#define SENS_LIFT_PIN           X2_3_PIN
#define SENS_LIFT_BIT           X2_3_BIT

#define SENS_WAIT_START_DDR     X2_4_DDR
#define SENS_WAIT_START_PORT    X2_4_PORT
#define SENS_WAIT_START_PIN     X2_4_PIN
#define SENS_WAIT_START_BIT     X2_4_BIT

#define SENS_WAIT_END_DDR       X3_1_DDR
#define SENS_WAIT_END_PORT      X3_1_PORT
#define SENS_WAIT_END_PIN       X3_1_PIN
#define SENS_WAIT_END_BIT       X3_1_BIT
