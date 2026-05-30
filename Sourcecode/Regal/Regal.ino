#include "pins.h"
#include <TMCStepper.h>
#include <AccelStepper.h>
#include <Wire.h>
#include <stdint.h>
#include <math.h>

volatile bool busy = false;
volatile bool is_homed = false;

static const uint8_t EN_PIN_NUM = 43;
static const float LIFT_STEPS_PER_MM = 20.00f;
static const unsigned long SENSOR_REFRESH_MS = 80UL;
static const unsigned long DRIVER_INIT_DELAY_MS = 5000UL;
static const bool SENSOR_ACTIVE_LOW = true;
static const int LIFT_HOME_PREMOVE_MM = 70;

// Zeitwerte fuer die Foerderablaufe.
static const unsigned long ENTLADEN_MIN_RUNTIME_MS = 5000UL;
static const unsigned long ENTLADEN_SENSOR_TIMEOUT_MS = 30000UL;
static const unsigned long BELADEN_LEVEL_REFILL_TIMEOUT_MS = 10000UL;

static const bool DIR_LEVEL_FORWARD = true;
static const bool DIR_LIFT_FORWARD = true;
static const bool DIR_LIFT_REVERSE = !DIR_LIFT_FORWARD;
static const bool DIR_WAIT_FORWARD = true;
static const uint8_t LEVEL_WAIT_POSITION = 3;


// I2C-Variablen

volatile uint8_t aufgabe_i2c = 0;
volatile int16_t par_generic = 0;
volatile uint8_t ebene_id_i2c = 0;
volatile bool new_message = false;
volatile uint8_t last_cmd = 0;


// Befehlscodes
enum : uint8_t {
  CMD_LIFT = 0,
  CMD_HOME = 1,
  CMD_STATUS = 2,
  CMD_EBENE = 3,
  CMD_BELADEN = 4,
  CMD_ENTLADEN = 5,
  CMD_STOP = 8
};

// Status byte1 bitfield:
// bit0 lift belegt
// bit1 wait start belegt
// bit2 wait ende belegt
// bit3 level1 front belegt
// bit4 level2 front belegt
// bit5 reserved (Mixer-Sensor liegt am Mixer-Controller)
// bit6 entladen blockiert

volatile uint8_t selected_level = 1;
bool selected_level_forward = DIR_LEVEL_FORWARD;
bool beladen_active = false;
bool entladen_active = false;
bool entladen_blocked = false;
bool beladen_lift_done = false;
bool beladen_level_cleared = false;
bool beladen_level_done = false;
unsigned long beladen_started_ms = 0;
unsigned long beladen_level_refill_started_ms = 0;
unsigned long entladen_started_ms = 0;
unsigned long entladen_clear_started_ms = 0;
bool entladen_wait_end_seen = false;

// Zwischengespeicherte Sensorzustaende.
bool sens_level1 = false;
bool sens_level2 = false;
bool sens_lift = false;
bool sens_wait_start = false;
bool sens_wait_end = false;
unsigned long last_sensor_update_ms = 0;

// ==============================
// Motorparameter
// ==============================
float max_speed[5] = {
  1500.0f,  // [0] lift
  1500.0f,  // [1] lift_band
  1500.0f,  // [2] Ebene1
  1500.0f,  // [3] Ebene2
  1500.0f   // [4] wait_band
};
float accel_sps2[5] = {
  500.0f,  // [0] lift
  1000.0f,  // [1] lift_band
  1000.0f,  // [2] Ebene1
  1000.0f,  // [3] Ebene2
  1000.0f   // [4] wait_band
};
uint8_t ihold_vals[5] = {
  15,  // [0] lift
  1,   // [1] lift_band
  1,   // [2] Ebene1
  1,   // [3] Ebene2
  1    // [4] wait_band
};
const int steps_u[5] = {
  4,   // [0] lift
  4,   // [1] lift_band
  4,   // [2] Ebene1
  4,   // [3] Ebene2
  4    // [4] wait_band
};
const int current_mA[5] = {
  2000,  // [0] lift
  1500,  // [1] lift_band
  1000,  // [2] Ebene1
  1000,  // [3] Ebene2
  1500   // [4] wait_band
};

// ==============================
// Hardware
// ==============================
#define SERIAL_PORT Serial1
#define SERIAL_PORT_2 Serial2
#define SERIAL_PORT_3 Serial3
#define R_SENSE 0.11f
#define I2C_ADDR 0x12

#define ADDR_lift 0b00
#define ADDR_lift_band 0b10
#define ADDR_Ebene1 0b00
#define ADDR_Ebene2 0b11
#define ADDR_wait_band 0b10

TMC2209Stepper driver_lift(&SERIAL_PORT, R_SENSE, ADDR_lift);
TMC2209Stepper driver_lift_band(&SERIAL_PORT, R_SENSE, ADDR_lift_band);
TMC2209Stepper driver_Ebene1(&SERIAL_PORT_3, R_SENSE, ADDR_Ebene1);
TMC2209Stepper driver_Ebene2(&SERIAL_PORT_2, R_SENSE, ADDR_Ebene2);
TMC2209Stepper driver_wait_band(&SERIAL_PORT_2, R_SENSE, ADDR_wait_band);

AccelStepper lift(AccelStepper::DRIVER, STEP_PIN_lift, DIR_PIN_lift);
AccelStepper lift_band(AccelStepper::DRIVER, STEP_PIN_lift_band, DIR_PIN_lift_band);
AccelStepper Ebene1(AccelStepper::DRIVER, STEP_PIN_Ebene1, DIR_PIN_Ebene1);
AccelStepper Ebene2(AccelStepper::DRIVER, STEP_PIN_Ebene2, DIR_PIN_Ebene2);
AccelStepper wait_band(AccelStepper::DRIVER, STEP_PIN_wait_band, DIR_PIN_wait_band);

AccelStepper* MOT[] = {&lift, &lift_band, &Ebene1, &Ebene2, &wait_band};
TMC2209Stepper* DRV[] = {&driver_lift, &driver_lift_band, &driver_Ebene1, &driver_Ebene2, &driver_wait_band};

// Initialisiert einen TMC2209-Treiber mit den gespeicherten Werten.
void driverCommonInit(TMC2209Stepper& d, int microsteps, int current, uint8_t ihold_val) {
  d.begin();
  d.pdn_disable(true);
  d.mstep_reg_select(true);
  d.toff(8);
  d.microsteps(microsteps);
  d.en_spreadCycle(true);
  d.pwm_autoscale(true);
  d.I_scale_analog(false);
  d.vsense(true);
  d.rms_current(current);
  d.ihold(ihold_val);
  d.iholddelay(0);
}

// Initialisiert ein Stepper-Objekt mit Geschwindigkeit und Beschleunigung.
void stepperCommonInit(AccelStepper& s, float vmax, float acc) {
  s.setMaxSpeed(vmax);
  s.setAcceleration(acc);
  s.setMinPulseWidth(5);
}

// Rechnet Millimeter fuer den Lift in die passende Schrittzahl um.
inline long mmToStepsLift(int mm) {
  return lroundf((float)mm * LIFT_STEPS_PER_MM);
}

// Wandelt den Pegel eines Sensors in "belegt / nicht belegt" um.
inline bool readOccupiedDigital(bool pin_state_high) {
  return SENSOR_ACTIVE_LOW ? !pin_state_high : pin_state_high;
}

// Liest alle Sensoren in einem festen Zeitraster ein.
void refreshSensors(bool force = false) {
  unsigned long now = millis();
  if (!force && (now - last_sensor_update_ms) < SENSOR_REFRESH_MS) {
    return;
  }
  last_sensor_update_ms = now;

  sens_level1 = readOccupiedDigital(PIN_READ(SENS_LEVEL1_FRONT));
  sens_level2 = readOccupiedDigital(PIN_READ(SENS_LEVEL2_FRONT));
  sens_lift = readOccupiedDigital(PIN_READ(SENS_LIFT));
  sens_wait_start = readOccupiedDigital(PIN_READ(SENS_WAIT_START));
  sens_wait_end = readOccupiedDigital(PIN_READ(SENS_WAIT_END));
}

// Liefert den Belegt-Zustand der aktuell gewaehlten Ebene.
inline bool selectedLevelOccupied() {
  if (selected_level == LEVEL_WAIT_POSITION) {
    return sens_wait_start;
  }
  return (selected_level == 2) ? sens_level2 : sens_level1;
}

// Liefert den Motor der aktuell gewaehlten Ebene.
inline AccelStepper* selectedLevelMotor() {
  if (selected_level == LEVEL_WAIT_POSITION) {
    return &wait_band;
  }
  return (selected_level == 2) ? &Ebene2 : &Ebene1;
}

// True, wenn statt einer Ebene die Warteposition ausgewaehlt ist.
inline bool selectedLevelIsWaitingArea() {
  return selected_level == LEVEL_WAIT_POSITION;
}

// Stoppt alle Foerderbaender und Ebenenmotoren.
void stopConveyors() {
  lift_band.setSpeed(0);
  Ebene1.setSpeed(0);
  Ebene2.setSpeed(0);
  wait_band.setSpeed(0);
}

// Laesst ein Foerderband mit seiner konfigurierten Maximalgeschwindigkeit laufen.
void runConveyor(AccelStepper& s, bool forward) {
  float speed_abs = s.maxSpeed();
  s.setSpeed(forward ? speed_abs : -speed_abs);
  s.runSpeed();
}

// Setzt alle Band-Modi und Zwischenzustaende zurueck.
void clearBandModes() {
  beladen_active = false;
  entladen_active = false;
  entladen_blocked = false;
  beladen_lift_done = false;
  beladen_level_cleared = false;
  beladen_level_done = false;
  beladen_started_ms = 0;
  beladen_level_refill_started_ms = 0;
  entladen_started_ms = 0;
  entladen_clear_started_ms = 0;
  entladen_wait_end_seen = false;
  stopConveyors();
}

// Stoppt alle laufenden Bewegungen und Foerderablaeufe sofort.
void stopAllMotion() {
  clearBandModes();

  lift.setSpeed(0);
  lift.moveTo(lift.currentPosition());

  entladen_blocked = false;
  busy = false;
}

// Verwirft eventuell noch uebrige Bytes aus dem I2C-Empfangspuffer.
void discardRemainingI2CBytes() {
  while (Wire.available()) {
    (void)Wire.read();
  }
}

// Setzt busy zurueck, wenn wirklich keine Bewegung und kein Bandmodus mehr aktiv ist.
void updateBusyState() {
  if (lift.distanceToGo() == 0 && !beladen_active && !entladen_active) {
    busy = false;
  }
}

// Arbeitet den Beladen-Ablauf schrittweise weiter ab.
void updateBeladenTask() {
  if (!beladen_active) {
    return;
  }

  bool lift_occ = sens_lift;

  // Spezialfall: Rueckgabe vom Mixer auf den Lift.
  if (selectedLevelIsWaitingArea()) {
    if (!lift_occ) {
      // Die Richtung kommt direkt vom Master ueber CMD_EBENE.
      runConveyor(lift_band, selected_level_forward);
    } else {
      lift_band.setSpeed(0);
    }

    wait_band.setSpeed(0);
    Ebene1.setSpeed(0);
    Ebene2.setSpeed(0);

    bool timeout_elapsed =
      (beladen_started_ms != 0) &&
      ((millis() - beladen_started_ms) >= ENTLADEN_SENSOR_TIMEOUT_MS);

    if (lift_occ || timeout_elapsed) {
      beladen_active = false;
      busy = false;
      stopConveyors();
    }
    return;
  }

  bool level_occ = selectedLevelOccupied();

  if (!beladen_lift_done && !lift_occ) {
    // Auch hier gilt: der Master gibt die gewuenschte Richtung direkt vor.
    runConveyor(lift_band, selected_level_forward);
  } else {
    lift_band.setSpeed(0);
    if (lift_occ) {
      beladen_lift_done = true;
    }
  }

  AccelStepper* lvl_motor = selectedLevelMotor();
  if (!beladen_level_done) {
    if (!beladen_level_cleared) {
      runConveyor(*lvl_motor, selected_level_forward);
      if (!level_occ) {
        beladen_level_cleared = true;
        beladen_level_refill_started_ms = millis();
      }
    } else if (level_occ) {
      lvl_motor->setSpeed(0);
      beladen_level_done = true;
    } else {
      runConveyor(*lvl_motor, selected_level_forward);
      if ((millis() - beladen_level_refill_started_ms) >= BELADEN_LEVEL_REFILL_TIMEOUT_MS) {
        lvl_motor->setSpeed(0);
        beladen_level_done = true;
      }
    }
  } else {
    lvl_motor->setSpeed(0);
  }

  if (selected_level == 2) {
    Ebene1.setSpeed(0);
  } else {
    Ebene2.setSpeed(0);
  }

  if (beladen_lift_done && beladen_level_done) {
    beladen_active = false;
    busy = false;
    stopConveyors();
  }
}

// Arbeitet den Entladen-Ablauf schrittweise weiter ab.
void updateEntladenTask() {
  if (!entladen_active) {
    return;
  }

  entladen_blocked = false;

  if (selectedLevelIsWaitingArea()) {
    runConveyor(lift_band, selected_level_forward);
    runConveyor(wait_band, selected_level_forward);
    Ebene1.setSpeed(0);
    Ebene2.setSpeed(0);

    if (sens_wait_end) {
      entladen_wait_end_seen = true;
    }

    unsigned long runtime_ms = millis() - entladen_started_ms;
    bool sensor_timeout_elapsed = (runtime_ms >= ENTLADEN_SENSOR_TIMEOUT_MS);
    bool wait_start_cleared = entladen_wait_end_seen && !sens_wait_start;

    if (wait_start_cleared || sensor_timeout_elapsed) {
      entladen_active = false;
      entladen_started_ms = 0;
      entladen_clear_started_ms = 0;
      entladen_blocked = sensor_timeout_elapsed && !wait_start_cleared;
      entladen_wait_end_seen = false;
      busy = false;
      stopConveyors();
    }
    return;
  }

  runConveyor(lift_band, selected_level_forward);
  Ebene1.setSpeed(0);
  Ebene2.setSpeed(0);
  wait_band.setSpeed(0);

  unsigned long runtime_ms = millis() - entladen_started_ms;
  bool sensor_timeout_elapsed = (runtime_ms >= ENTLADEN_SENSOR_TIMEOUT_MS);
  bool lift_clear = !sens_lift;

  if (lift_clear) {
    if (entladen_clear_started_ms == 0) {
      entladen_clear_started_ms = millis();
    }
  } else {
    entladen_clear_started_ms = 0;
  }

  bool clear_delay_elapsed =
    (entladen_clear_started_ms != 0) &&
    ((millis() - entladen_clear_started_ms) >= ENTLADEN_MIN_RUNTIME_MS);

  if (clear_delay_elapsed || sensor_timeout_elapsed) {
    entladen_active = false;
    entladen_started_ms = 0;
    entladen_clear_started_ms = 0;
    busy = false;
    stopConveyors();
  }
}

// Baut das 5-Byte-Statuspaket und sendet es an den Master.
void writeStatusPacket() {
  refreshSensors(true);

  uint8_t out[5];
  bool current_busy = busy;
  if (!current_busy) {
    current_busy = (lift.distanceToGo() != 0) || beladen_active || entladen_active;
  }

  uint8_t sensor_flags = 0;
  if (sens_lift)       sensor_flags |= (1u << 0);
  if (sens_wait_start) sensor_flags |= (1u << 1);
  if (sens_wait_end)   sensor_flags |= (1u << 2);
  if (sens_level1)     sensor_flags |= (1u << 3);
  if (sens_level2)     sensor_flags |= (1u << 4);
  // bit5 bleibt reserviert
  if (entladen_blocked) sensor_flags |= (1u << 6);

  long pos_steps = lift.currentPosition();
  long pos_mm_long = lroundf((float)pos_steps / LIFT_STEPS_PER_MM);
  if (pos_mm_long > 32767) pos_mm_long = 32767;
  if (pos_mm_long < -32768) pos_mm_long = -32768;
  int16_t pos_mm = (int16_t)pos_mm_long;

  out[0] = current_busy ? 1 : 0;
  out[1] = sensor_flags;
  out[2] = (uint8_t)(pos_mm & 0xFF);
  out[3] = (uint8_t)((pos_mm >> 8) & 0xFF);
  out[4] = is_homed ? 1 : 0;

  Wire.write(out, sizeof(out));
}

// Fuehrt ein zuvor empfangenes I2C-Kommando erst im loop() aus.
void handlePendingCommand() {
  if (!new_message) {
    return;
  }

  noInterrupts();
  uint8_t cmd = aufgabe_i2c;
  int16_t mm = par_generic;
  uint8_t ebene = ebene_id_i2c;
  new_message = false;
  interrupts();

  switch (cmd) {
    case CMD_LIFT:     fahren_mm(mm); break;
    case CMD_HOME:     (void)home();  break;
    case CMD_STATUS:   break;
    case CMD_EBENE:    Ebene(ebene);  break;
    case CMD_ENTLADEN: entladen();    break;
    case CMD_BELADEN:  beladen();     break;
    case CMD_STOP:     stopAllMotion(); break;
    default: break;
  }
}


// Funktionen
// Referenziert den Lift am Home-Sensor.
bool home() {
  clearBandModes();
  busy = true;
  is_homed = false;

  const float HOME_SPEED = -800.0f;
  const unsigned long TIMEOUT_MS = 200000UL;
  const long PREMOVE_STEPS = mmToStepsLift(LIFT_HOME_PREMOVE_MM);

  float oldMax = lift.maxSpeed();
  float oldAcc = lift.acceleration();

  // Zuerst 5 cm vom Sensor wegfahren, dann die eigentliche Referenzfahrt starten.
  lift.moveTo(lift.currentPosition() + PREMOVE_STEPS);
  while (lift.distanceToGo() != 0) {
    lift.run();
  }

  lift.setMaxSpeed(fabsf(HOME_SPEED));
  lift.setAcceleration(accel_sps2[0]);
  lift.setSpeed(HOME_SPEED);

  unsigned long t0 = millis();
  while (PIN_READ(HOME)) {
    lift.runSpeed();
    if (millis() - t0 > TIMEOUT_MS) {
      lift.setMaxSpeed(oldMax);
      lift.setAcceleration(oldAcc);
      busy = false;
      is_homed = false;
      return false;
    }
  }

  lift.setSpeed(0);
  lift.moveTo(lift.currentPosition());
  lift.setCurrentPosition(0);
  lift.setMaxSpeed(oldMax);
  lift.setAcceleration(oldAcc);

  busy = false;
  is_homed = true;
  return true;
}

// Faehrt den Lift auf die vom Master gewuenschte Position.
void fahren_mm(int16_t mm) {
  clearBandModes();
  busy = true;
  lift.moveTo(mmToStepsLift((int)mm));
}

// Waehlt die aktive Ebene und optional deren Fahrtrichtung aus.
void Ebene(uint8_t ebene_id) {
  // Kodierung:
  // bit6: Richtungsbit vorhanden, bit7: Richtungswert, bits0..5: Ebenennummer.
  // level 3 ist im Projekt als Warteposition reserviert.
  // Ohne bit6 wird aus Kompatibilitaetsgruenden die Standardrichtung verwendet.
  bool has_direction_flag = ((ebene_id & 0x40u) != 0u);
  bool forward = ((ebene_id & 0x80u) != 0u);
  uint8_t level_raw = (ebene_id & 0x3Fu);
  if (level_raw == 0) {
    level_raw = 1;
  }

  if (level_raw == 2) {
    selected_level = 2;
  } else if (level_raw == LEVEL_WAIT_POSITION) {
    selected_level = LEVEL_WAIT_POSITION;
  } else {
    selected_level = 1;
  }
  selected_level_forward = has_direction_flag ? forward : DIR_LEVEL_FORWARD;
}

// Startet den Beladen-Ablauf der aktuell gewaehlten Ebene.
void beladen() {
  entladen_active = false;
  entladen_blocked = false;
  beladen_lift_done = false;
  beladen_level_cleared = false;
  beladen_level_done = false;
  beladen_started_ms = millis();
  beladen_level_refill_started_ms = 0;
  beladen_active = true;
  busy = true;
}

// Startet den Entladen-Ablauf vom Lift in Richtung Mixer.
void entladen() {
  refreshSensors(true);
  if (!sens_lift) {
    entladen_blocked = true;
    entladen_active = false;
    entladen_started_ms = 0;
    beladen_active = false;
    busy = false;
    stopConveyors();
    return;
  }

  if (selectedLevelIsWaitingArea() && sens_wait_end) {
    entladen_blocked = true;
    entladen_active = false;
    entladen_started_ms = 0;
    entladen_clear_started_ms = 0;
    beladen_active = false;
    busy = false;
    stopConveyors();
    return;
  }

  entladen_blocked = false;
  beladen_active = false;
  entladen_active = true;
  entladen_started_ms = millis();
  entladen_clear_started_ms = 0;
  entladen_wait_end_seen = false;
  busy = true;
}


// I2C

void onI2CReceive(int count) {
  if (count <= 0) {
    discardRemainingI2CBytes();
    return;
  }

  uint8_t cmd = Wire.read();
  aufgabe_i2c = cmd;
  last_cmd = cmd;

  if (cmd == CMD_LIFT) {
    if (count >= 3 && Wire.available() >= 2) {
      uint8_t low = Wire.read();
      uint8_t high = Wire.read();
      par_generic = (int16_t)((uint16_t)low | ((uint16_t)high << 8));
    }
    discardRemainingI2CBytes();
    new_message = true;
    return;
  }

  if (cmd == CMD_EBENE) {
    if (count >= 2 && Wire.available() >= 1) {
      ebene_id_i2c = Wire.read();
    }
    discardRemainingI2CBytes();
    new_message = true;
    return;
  }

  discardRemainingI2CBytes();
  new_message = true;
}

// Status (5 Bytes):
// [0]  busy
// [1]  sensor_flags
// [2]  pos_low
// [3]  pos_high
// [4]  is_homed
void onI2CRequest() {
  if (last_cmd == CMD_STATUS) {
    writeStatusPacket();
    return;
  }

  const uint8_t ack = 0x06;
  Wire.write(&ack, 1);
}


// Setup / Loop

void setup() {
  // I2C-Slave starten und Handler registrieren.
  Wire.begin(I2C_ADDR);
  Wire.onReceive(onI2CReceive);
  Wire.onRequest(onI2CRequest);

  // Serielle Verbindungen fuer die Treiber starten.
  SERIAL_PORT.begin(57600);
  SERIAL_PORT_2.begin(57600);
  SERIAL_PORT_3.begin(57600);

  // Treiber zunaechst deaktivieren.
  pinMode(EN_PIN_NUM, OUTPUT);
  digitalWrite(EN_PIN_NUM, HIGH);

  // Home-Sensor vorbereiten.
  PIN_INPUT(HOME);
  PIN_PULLUP_ON(HOME);

  // Alle Belegt-Sensoren vorbereiten.
  PIN_INPUT(SENS_LEVEL1_FRONT);
  PIN_INPUT(SENS_LEVEL2_FRONT);
  PIN_INPUT(SENS_LIFT);
  PIN_INPUT(SENS_WAIT_START);
  PIN_INPUT(SENS_WAIT_END);

  PIN_PULLUP_OFF(SENS_LEVEL1_FRONT);
  PIN_PULLUP_OFF(SENS_LEVEL2_FRONT);
  PIN_PULLUP_OFF(SENS_LIFT);
  PIN_PULLUP_OFF(SENS_WAIT_START);
  PIN_PULLUP_OFF(SENS_WAIT_END);

  is_homed = false;

  delay(DRIVER_INIT_DELAY_MS);

  // Alle Treiber und Stepper mit den Tabellenwerten initialisieren.
  for (int i = 0; i < 5; ++i) {
    driverCommonInit(*DRV[i], steps_u[i], current_mA[i], ihold_vals[i]);
    stepperCommonInit(*MOT[i], max_speed[i], accel_sps2[i]);
    MOT[i]->setSpeed(0);
    MOT[i]->moveTo(MOT[i]->currentPosition());
  }

  // Treiber aktiv schalten und Startzustand einlesen.
  digitalWrite(EN_PIN_NUM, LOW);
  refreshSensors(true);
}

void loop() {
  // Sensoren und laufende Bewegungen zyklisch aktualisieren.
  refreshSensors();

  lift.run();

  updateBeladenTask();
  updateEntladenTask();
  updateBusyState();

  // Neue I2C-Kommandos werden immer erst hier im loop() ausgefuehrt.
  handlePendingCommand();
}
