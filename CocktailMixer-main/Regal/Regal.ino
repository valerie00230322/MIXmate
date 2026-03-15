#include "pins.h"
#include <TMCStepper.h>
#include <AccelStepper.h>
#include <Wire.h>
#include <stdint.h>
#include <math.h>

volatile bool busy = false;
volatile bool homing_active = false;
volatile bool is_homed = false;

static const uint8_t EN_PIN_NUM = 43;
static const long STEPS_PER_MM = 17;

// Zentrale Distanz-Schwelle fuer alle SR04-Sensoren.
static const float OCCUPIED_THRESHOLD_CM = 10.0f;
static const unsigned long SR04_TIMEOUT_US = 25000UL;
static const unsigned long SENSOR_REFRESH_MS = 80UL;

// Conveyor tuning.
static const float SPEED_LEVEL_BAND = 1200.0f;
static const float SPEED_LIFT_BAND = 1200.0f;
static const float SPEED_WAIT_BAND = 1200.0f;
static const unsigned long ENTLADEN_MIN_RUNTIME_MS = 3000UL;
static const float AUSSCHUB_HOME_SPEED = -700.0f;          // links
static const unsigned long AUSSCHUB_HOME_TIMEOUT_MS = 30000UL;
static const long AUSSCHUB_HOME_OFFSET_STEPS = 120;        // Sensorversatz zur 0-Position

static const bool DIR_LEVEL_FORWARD = true;
static const bool DIR_LIFT_FORWARD = true;
static const bool DIR_WAIT_FORWARD = true;

// ==============================
// I2C variables
// ==============================
volatile uint8_t aufgabe_i2c = 0;
volatile int16_t par_generic = 0;
volatile uint8_t ebene_id_i2c = 0;
volatile bool new_message = false;
volatile uint8_t last_cmd = 0;

// ==============================
// Command codes
// ==============================
enum : uint8_t {
  CMD_LIFT = 0,
  CMD_HOME = 1,
  CMD_STATUS = 2,
  CMD_EBENE = 3,
  CMD_BELADEN = 4,
  CMD_ENTLADEN = 5,
  CMD_AUSSCHUB = 6,
  CMD_AUSSCHUB_HOME = 7
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
unsigned long entladen_started_ms = 0;

// Cached sensor states.
bool sens_level1 = false;
bool sens_level2 = false;
bool sens_lift = false;
bool sens_wait_start = false;
bool sens_wait_end = false;
unsigned long last_sensor_update_ms = 0;

// ==============================
// Motor parameters
// ==============================
float max_speed[5] = {3000.0f, 2000.0f, 2000.0f, 2000.0f, 2000.0f};
float accel_sps2[5] = {1000.0f, 1000.0f, 1000.0f, 1000.0f, 1000.0f};
uint8_t ihold_vals[5] = {15, 10, 1, 1, 1};
const int steps_u[5] = {4, 16, 2, 2, 2};
const int current_mA[5] = {1200, 1200, 2000, 2000, 2000};

// ==============================
// Hardware setup
// ==============================
#define SERIAL_PORT Serial1
#define SERIAL_PORT_2 Serial2
#define SERIAL_PORT_3 Serial3
#define R_SENSE 0.11f
#define I2C_ADDR 0x12

#define ADDR_lift 0b00
#define ADDR_ausschub 0b01
#define ADDR_lift_band 0b10
#define ADDR_Ebene1 0b11
#define ADDR_Ebene2 0b00

TMC2209Stepper driver_lift(&SERIAL_PORT, R_SENSE, ADDR_lift);
TMC2209Stepper driver_ausschub(&SERIAL_PORT, R_SENSE, ADDR_ausschub);
TMC2209Stepper driver_lift_band(&SERIAL_PORT, R_SENSE, ADDR_lift_band);
TMC2209Stepper driver_Ebene1(&SERIAL_PORT, R_SENSE, ADDR_Ebene1);
TMC2209Stepper driver_Ebene2(&SERIAL_PORT_2, R_SENSE, ADDR_Ebene2);

AccelStepper lift(AccelStepper::DRIVER, STEP_PIN_lift, DIR_PIN_lift);
AccelStepper ausschub(AccelStepper::DRIVER, STEP_PIN_ausschub, DIR_PIN_ausschub);
AccelStepper lift_band(AccelStepper::DRIVER, STEP_PIN_lift_band, DIR_PIN_lift_band);
AccelStepper Ebene1(AccelStepper::DRIVER, STEP_PIN_Ebene1, DIR_PIN_Ebene1);
AccelStepper Ebene2(AccelStepper::DRIVER, STEP_PIN_Ebene2, DIR_PIN_Ebene2);

AccelStepper* MOT[] = {&lift, &ausschub, &lift_band, &Ebene1, &Ebene2};
TMC2209Stepper* DRV[] = {&driver_lift, &driver_ausschub, &driver_lift_band, &driver_Ebene1, &driver_Ebene2};

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

void stepperCommonInit(AccelStepper& s, float vmax, float acc) {
  s.setMaxSpeed(vmax);
  s.setAcceleration(acc);
  s.setMinPulseWidth(5);
}

inline long mmToSteps(int mm) {
  return (long)mm * (long)STEPS_PER_MM;
}

inline void usTriggerPulse() {
  PIN_LOW(REGAL_US_TRIG);
  delayMicroseconds(2);
  PIN_HIGH(REGAL_US_TRIG);
  delayMicroseconds(10);
  PIN_LOW(REGAL_US_TRIG);
}

float measureDistanceCm(bool (*echo_read_fn)()) {
  usTriggerPulse();

  unsigned long t0 = micros();
  while (!echo_read_fn()) {
    if ((micros() - t0) > SR04_TIMEOUT_US) {
      return -1.0f;
    }
  }

  unsigned long start = micros();
  while (echo_read_fn()) {
    if ((micros() - start) > SR04_TIMEOUT_US) {
      return -1.0f;
    }
  }

  unsigned long dur = micros() - start;
  return (float)dur * 0.0343f * 0.5f;
}

inline bool occFromDistance(float cm) {
  return (cm > 0.0f && cm <= OCCUPIED_THRESHOLD_CM);
}

bool readEchoLevel1() { return PIN_READ(SENS_LEVEL1_ECHO); }
bool readEchoLevel2() { return PIN_READ(SENS_LEVEL2_ECHO); }
bool readEchoLift() { return PIN_READ(SENS_LIFT_ECHO); }
bool readEchoWaitStart() { return PIN_READ(SENS_WAIT_START_ECHO); }
bool readEchoWaitEnd() { return PIN_READ(SENS_WAIT_END_ECHO); }

void refreshSensors(bool force = false) {
  unsigned long now = millis();
  if (!force && (now - last_sensor_update_ms) < SENSOR_REFRESH_MS) {
    return;
  }
  last_sensor_update_ms = now;

  float d1 = measureDistanceCm(readEchoLevel1);
  float d2 = measureDistanceCm(readEchoLevel2);
  float d3 = measureDistanceCm(readEchoLift);
  float d4 = measureDistanceCm(readEchoWaitStart);
  float d5 = measureDistanceCm(readEchoWaitEnd);

  sens_level1 = occFromDistance(d1);
  sens_level2 = occFromDistance(d2);
  sens_lift = occFromDistance(d3);
  sens_wait_start = occFromDistance(d4);
  sens_wait_end = occFromDistance(d5);
}

inline bool selectedLevelOccupied() {
  return (selected_level == 2) ? sens_level2 : sens_level1;
}

inline AccelStepper* selectedLevelMotor() {
  return (selected_level == 2) ? &Ebene2 : &Ebene1;
}

void stopConveyors() {
  ausschub.setSpeed(0);
  lift_band.setSpeed(0);
  Ebene1.setSpeed(0);
  Ebene2.setSpeed(0);
}

void runConveyor(AccelStepper& s, float speed_abs, bool forward) {
  s.setSpeed(forward ? speed_abs : -speed_abs);
  s.runSpeed();
}

void clearBandModes() {
  beladen_active = false;
  entladen_active = false;
  entladen_blocked = false;
  entladen_started_ms = 0;
  stopConveyors();
}

bool home() {
  clearBandModes();
  busy = true;
  homing_active = true;
  is_homed = false;

  const float HOME_SPEED = -800.0f;
  const unsigned long TIMEOUT_MS = 200000UL;

  float oldMax = lift.maxSpeed();
  float oldAcc = lift.acceleration();

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
      homing_active = false;
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
  homing_active = false;
  is_homed = true;
  return true;
}

bool homeAusschubByInit() {
  const unsigned long t0 = millis();

  float oldMax = ausschub.maxSpeed();
  float oldAcc = ausschub.acceleration();

  ausschub.setMaxSpeed(fabsf(AUSSCHUB_HOME_SPEED));
  ausschub.setAcceleration(accel_sps2[1]);
  ausschub.setSpeed(AUSSCHUB_HOME_SPEED);

  while (!PIN_READ(AUSSCHUB_HOME)) {
    ausschub.runSpeed();
    if (millis() - t0 > AUSSCHUB_HOME_TIMEOUT_MS) {
      ausschub.setSpeed(0);
      ausschub.moveTo(ausschub.currentPosition());
      ausschub.setMaxSpeed(oldMax);
      ausschub.setAcceleration(oldAcc);
      return false;
    }
  }

  ausschub.setSpeed(0);
  ausschub.moveTo(ausschub.currentPosition() + AUSSCHUB_HOME_OFFSET_STEPS);
  while (ausschub.distanceToGo() != 0) {
    ausschub.run();
  }
  ausschub.moveTo(ausschub.currentPosition());
  ausschub.setCurrentPosition(0);
  ausschub.setMaxSpeed(oldMax);
  ausschub.setAcceleration(oldAcc);
  return true;
}

void fahren_mm(int16_t mm) {
  clearBandModes();
  busy = true;
  lift.moveTo(mmToSteps((int)mm));
}

void ausschub_fahren_mm(int16_t mm) {
  clearBandModes();
  busy = true;
  ausschub.moveTo(mmToSteps((int)mm));
}

void ausschub_home() {
  clearBandModes();
  busy = true;
  bool ok = homeAusschubByInit();
  busy = false;
  if (!ok) {
    is_homed = false;
  }
}

void Ebene(uint8_t ebene_id) {
  // Encoding:
  // bit6: direction flag present, bit7: direction value, bits0..5: level id.
  // Backward compatible: without bit6, default direction constant is used.
  bool has_direction_flag = ((ebene_id & 0x40u) != 0u);
  bool forward = ((ebene_id & 0x80u) != 0u);
  uint8_t level_raw = (ebene_id & 0x3Fu);
  if (level_raw == 0) {
    level_raw = 1;
  }

  selected_level = (level_raw == 2) ? 2 : 1;
  selected_level_forward = has_direction_flag ? forward : DIR_LEVEL_FORWARD;
}

void beladen() {
  entladen_active = false;
  entladen_blocked = false;
  beladen_active = true;
  busy = true;
}

void entladen() {
  refreshSensors(true);
  if (sens_wait_end) {
    entladen_blocked = true;
    entladen_active = false;
    entladen_started_ms = 0;
    beladen_active = false;
    busy = false;
    stopConveyors();
    return;
  }

  entladen_blocked = false;
  beladen_active = false;
  entladen_active = true;
  entladen_started_ms = millis();
  busy = true;
}

void onI2CReceive(int count) {
  if (count <= 0) {
    while (Wire.available()) (void)Wire.read();
    return;
  }

  uint8_t cmd = Wire.read();
  aufgabe_i2c = cmd;
  last_cmd = cmd;

  if (cmd == CMD_LIFT || cmd == CMD_AUSSCHUB) {
    if (count >= 3 && Wire.available() >= 2) {
      uint8_t low = Wire.read();
      uint8_t high = Wire.read();
      par_generic = (int16_t)((uint16_t)low | ((uint16_t)high << 8));
    }
    while (Wire.available()) (void)Wire.read();
    new_message = true;
    return;
  }

  if (cmd == CMD_EBENE) {
    if (count >= 2 && Wire.available() >= 1) {
      ebene_id_i2c = Wire.read();
    }
    while (Wire.available()) (void)Wire.read();
    new_message = true;
    return;
  }

  while (Wire.available()) (void)Wire.read();
  new_message = true;
}

// Status: [busy, sensor_flags, pos_low, pos_high, homing]
void onI2CRequest() {
  if (last_cmd == CMD_STATUS) {
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
    // bit5 reserved
    if (entladen_blocked) sensor_flags |= (1u << 6);

    long pos_steps = lift.currentPosition();
    long pos_mm_long = pos_steps / STEPS_PER_MM;
    if (pos_mm_long > 32767) pos_mm_long = 32767;
    if (pos_mm_long < -32768) pos_mm_long = -32768;
    int16_t pos_mm = (int16_t)pos_mm_long;

    out[0] = current_busy ? 1 : 0;
    out[1] = sensor_flags;
    out[2] = (uint8_t)(pos_mm & 0xFF);
    out[3] = (uint8_t)((pos_mm >> 8) & 0xFF);
    out[4] = is_homed ? 1 : 0;

    Wire.write(out, 5);
    return;
  }

  const uint8_t ack = 0x06;
  Wire.write(&ack, 1);
}

void setup() {
  Wire.begin(I2C_ADDR);
  Wire.onReceive(onI2CReceive);
  Wire.onRequest(onI2CRequest);

  SERIAL_PORT.begin(57600);
  SERIAL_PORT_2.begin(57600);
  SERIAL_PORT_3.begin(57600);

  pinMode(EN_PIN_NUM, OUTPUT);
  digitalWrite(EN_PIN_NUM, HIGH);

  PIN_INPUT(HOME);
  PIN_PULLUP_ON(HOME);
  PIN_INPUT(AUSSCHUB_HOME);
  PIN_PULLUP_ON(AUSSCHUB_HOME);

  PIN_OUTPUT(REGAL_US_TRIG);
  PIN_LOW(REGAL_US_TRIG);

  PIN_INPUT(SENS_LEVEL1_ECHO);
  PIN_INPUT(SENS_LEVEL2_ECHO);
  PIN_INPUT(SENS_LIFT_ECHO);
  PIN_INPUT(SENS_WAIT_START_ECHO);
  PIN_INPUT(SENS_WAIT_END_ECHO);

  PIN_PULLUP_OFF(SENS_LEVEL1_ECHO);
  PIN_PULLUP_OFF(SENS_LEVEL2_ECHO);
  PIN_PULLUP_OFF(SENS_LIFT_ECHO);
  PIN_PULLUP_OFF(SENS_WAIT_START_ECHO);
  PIN_PULLUP_OFF(SENS_WAIT_END_ECHO);

  is_homed = false;
  homing_active = false;

  for (int i = 0; i < 5; ++i) {
    driverCommonInit(*DRV[i], steps_u[i], current_mA[i], ihold_vals[i]);
    stepperCommonInit(*MOT[i], max_speed[i], accel_sps2[i]);
    MOT[i]->setSpeed(0);
    MOT[i]->moveTo(MOT[i]->currentPosition());
  }

  digitalWrite(EN_PIN_NUM, LOW);
  refreshSensors(true);
}

void loop() {
  refreshSensors();

  lift.run();
  ausschub.run();

  if (beladen_active) {
    bool lift_occ = sens_lift;
    bool level_occ = selectedLevelOccupied();

    if (!lift_occ) {
      runConveyor(lift_band, SPEED_LIFT_BAND, DIR_LIFT_FORWARD);
    } else {
      lift_band.setSpeed(0);
    }

    AccelStepper* lvl_motor = selectedLevelMotor();
    if (!level_occ) {
      runConveyor(*lvl_motor, SPEED_LEVEL_BAND, selected_level_forward);
    } else {
      lvl_motor->setSpeed(0);
    }

    if (selected_level == 2) {
      Ebene1.setSpeed(0);
    } else {
      Ebene2.setSpeed(0);
    }

    ausschub.setSpeed(0);

    if (lift_occ && level_occ) {
      beladen_active = false;
      busy = false;
      stopConveyors();
    }
  }

  if (entladen_active) {
    if (sens_wait_end) {
      entladen_blocked = true;
      entladen_active = false;
      entladen_started_ms = 0;
      busy = false;
      stopConveyors();
    } else {
      entladen_blocked = false;

      runConveyor(lift_band, SPEED_LIFT_BAND, DIR_LIFT_FORWARD);
      runConveyor(ausschub, SPEED_WAIT_BAND, DIR_WAIT_FORWARD);
      Ebene1.setSpeed(0);
      Ebene2.setSpeed(0);

      bool wait_clear = (!sens_wait_start && !sens_wait_end);
      bool min_runtime_elapsed = ((millis() - entladen_started_ms) >= ENTLADEN_MIN_RUNTIME_MS);
      if (wait_clear && min_runtime_elapsed) {
        entladen_active = false;
        entladen_started_ms = 0;
        busy = false;
        stopConveyors();
      }
    }
  }

  if (lift.distanceToGo() == 0 && ausschub.distanceToGo() == 0 && !beladen_active && !entladen_active) {
    busy = false;
  }

  if (new_message) {
    noInterrupts();
    uint8_t cmd = aufgabe_i2c;
    int16_t mm = par_generic;
    uint8_t ebene = ebene_id_i2c;
    new_message = false;
    interrupts();

    switch (cmd) {
      case CMD_LIFT:     fahren_mm(mm); break;
      case CMD_AUSSCHUB: ausschub_fahren_mm(mm); break;
      case CMD_AUSSCHUB_HOME: ausschub_home(); break;
      case CMD_HOME:     (void)home();  break;
      case CMD_STATUS:   break;
      case CMD_EBENE:    Ebene(ebene);  break;
      case CMD_ENTLADEN: entladen();    break;
      case CMD_BELADEN:  beladen();     break;
      default: break;
    }
  }
}
