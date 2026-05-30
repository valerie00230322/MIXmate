#include "pins.h"
#include <TMCStepper.h>
#include <AccelStepper.h>
#include <Wire.h>
#include <stdint.h>
#include <math.h>


//         Konfiguration

// Master sendet PLF-Positionen in mm (int16)
static const long STEPS_PER_MM = 17;
volatile bool busy = false;
volatile bool band_belegt_flag = false;

volatile bool is_homed = false;

const unsigned long BAND_TIMEOUT_MS = 10000UL;
const long CONTINUOUS_STEPS = 100000000L;


//   Empfehlung für 7/9 Schlauch
// AccelStepper setSpeed() ist STEPS pro Sekunde (STEP-Pulse/s).
// Für 7/9 Silikon (relativ hart + hohe Quetschkraft) konservativ:
static const float PUMP_SPEED_79_SPS = 1000.0f;   // <- empfohlen niedrig
// Falls du später erhöhen willst: 700..1000 ist oft noch ok.

//         Motor Parameter
// max_speed[] wird für setMaxSpeed genutzt (Limit).
// Für Pumpen setzen wir den MaxSpeed gleich der gewünschten Pump-Speed.
float max_speed[12] = {
  3000.0f,             // PLF
  1500.0f,             // BAND
  PUMP_SPEED_79_SPS,   // P1
  PUMP_SPEED_79_SPS,   // P2
  PUMP_SPEED_79_SPS,   // P3
  PUMP_SPEED_79_SPS,   // P4
  PUMP_SPEED_79_SPS,   // P5
  PUMP_SPEED_79_SPS,   // P6
  PUMP_SPEED_79_SPS,   // P7
  PUMP_SPEED_79_SPS,   // P8
  PUMP_SPEED_79_SPS,   // P9
  PUMP_SPEED_79_SPS    // P10
};

// steps/s^2 (für run() relevant; Pumpen nutzen runSpeedToPosition ohne Rampen)
// Wir lassen die Werte drin, schaden nicht.
float accel_sps2[12] = {
  1000.0f,  // PLF
  1000.0f, // BAND
  1000.0f, // P1
  1000.0f, // P2
  1000.0f, // P3
  1000.0f, // P4
  1000.0f, // P5
  1000.0f, // P6
  1000.0f, // P7
  1000.0f, // P8
  1000.0f, // P9
  1000.0f  // P10
};

// IHOLD 0..31
uint8_t ihold_vals[12] = {
  15,  // PLF
  10,  // BAND
  1,   // P1
  1,   // P2
  1,   // P3
  1,   // P4
  1,   // P5
  1,   // P6
  1,   // P7
  1,   // P8
  1,   // P9
  1    // P10
};

// Microsteps
const int steps_u[12] = {
  4,   // PLF
  4,  // BAND
  2,   // P1
  2,   // P2
  2,   // P3
  2,   // P4
  2,   // P5
  2,   // P6
  2,   // P7
  2,   // P8
  2,   // P9
  2    // P10
};

// RMS current mA
const int current_mA[12] = {
  1200,  // PLF
  1200,  // BAND
  2000,  // P1
  2000,  // P2
  2000,  // P3
  2000,  // P4
  2000,  // P5
  2000,  // P6
  2000,  // P7
  2000,  // P8
  2000,  // P9
  2000   // P10
};


//         Befehls-Codes
enum : uint8_t {
  CMD_FAHR     = 0,
  CMD_HOME     = 1,
  CMD_STATUS   = 2,
  CMD_PUMPE    = 3,
  CMD_BELADEN  = 4,
  CMD_ENTLADEN = 5,
  CMD_STOP     = 6
};


//         Hardware-Setup

#define SERIAL_PORT    Serial1
#define SERIAL_PORT_2  Serial2
#define SERIAL_PORT_3  Serial3
#define R_SENSE        0.11f
#define I2C_ADDR       0x13

// UART-Adressen
#define ADDR_PLF       0b00
#define ADDR_BAND      0b01
#define ADDR_PUMPE1    0b10
#define ADDR_PUMPE2    0b11
#define ADDR_PUMPE3    0b00
#define ADDR_PUMPE4    0b01
#define ADDR_PUMPE5    0b10
#define ADDR_PUMPE6    0b11
#define ADDR_PUMPE7    0b00
#define ADDR_PUMPE8    0b01
#define ADDR_PUMPE9    0b10
#define ADDR_PUMPE10   0b11


// Motor STEP/DIR Pins

static const uint8_t STEP_PIN_PLF = 11;
static const uint8_t DIR_PIN_PLF  = 22;

static const uint8_t STEP_PIN_BAND = 12;
static const uint8_t DIR_PIN_BAND  = 23;

static const uint8_t STEP_PIN_PUMPE1 = 13;
static const uint8_t DIR_PIN_PUMPE1  = 24;

static const uint8_t STEP_PIN_PUMPE2 = 0;
static const uint8_t DIR_PIN_PUMPE2  = 25;

static const uint8_t STEP_PIN_PUMPE3 = 1;
static const uint8_t DIR_PIN_PUMPE3  = 26;

static const uint8_t STEP_PIN_PUMPE4 = 5;
static const uint8_t DIR_PIN_PUMPE4  = 27;

static const uint8_t STEP_PIN_PUMPE5 = 6;
static const uint8_t DIR_PIN_PUMPE5  = 28;

static const uint8_t STEP_PIN_PUMPE6 = 7;
static const uint8_t DIR_PIN_PUMPE6  = 29;

static const uint8_t STEP_PIN_PUMPE7 = 8;
static const uint8_t DIR_PIN_PUMPE7  = 37;

static const uint8_t STEP_PIN_PUMPE8 = 46;
static const uint8_t DIR_PIN_PUMPE8  = 36;

static const uint8_t STEP_PIN_PUMPE9 = 45;
static const uint8_t DIR_PIN_PUMPE9  = 35;

static const uint8_t STEP_PIN_PUMPE10 = 44;
static const uint8_t DIR_PIN_PUMPE10  = 34;

static const uint8_t EN_PIN_NUM = 43;


//         Objekte

TMC2209Stepper driver_plf     (&SERIAL_PORT,   R_SENSE, ADDR_PLF);
TMC2209Stepper driver_band    (&SERIAL_PORT,   R_SENSE, ADDR_BAND);
TMC2209Stepper driver_pumpe1  (&SERIAL_PORT,   R_SENSE, ADDR_PUMPE1);
TMC2209Stepper driver_pumpe2  (&SERIAL_PORT,   R_SENSE, ADDR_PUMPE2);
TMC2209Stepper driver_pumpe3  (&SERIAL_PORT_2, R_SENSE, ADDR_PUMPE3);
TMC2209Stepper driver_pumpe4  (&SERIAL_PORT_2, R_SENSE, ADDR_PUMPE4);
TMC2209Stepper driver_pumpe5  (&SERIAL_PORT_2, R_SENSE, ADDR_PUMPE5);
TMC2209Stepper driver_pumpe6  (&SERIAL_PORT_2, R_SENSE, ADDR_PUMPE6);
TMC2209Stepper driver_pumpe7  (&SERIAL_PORT_3, R_SENSE, ADDR_PUMPE7);
TMC2209Stepper driver_pumpe8  (&SERIAL_PORT_3, R_SENSE, ADDR_PUMPE8);
TMC2209Stepper driver_pumpe9  (&SERIAL_PORT_3, R_SENSE, ADDR_PUMPE9);
TMC2209Stepper driver_pumpe10 (&SERIAL_PORT_3, R_SENSE, ADDR_PUMPE10);

AccelStepper PLF     (AccelStepper::DRIVER, STEP_PIN_PLF,     DIR_PIN_PLF);
AccelStepper BAND    (AccelStepper::DRIVER, STEP_PIN_BAND,    DIR_PIN_BAND);
AccelStepper PUMPE1  (AccelStepper::DRIVER, STEP_PIN_PUMPE1,  DIR_PIN_PUMPE1);
AccelStepper PUMPE2  (AccelStepper::DRIVER, STEP_PIN_PUMPE2,  DIR_PIN_PUMPE2);
AccelStepper PUMPE3  (AccelStepper::DRIVER, STEP_PIN_PUMPE3,  DIR_PIN_PUMPE3);
AccelStepper PUMPE4  (AccelStepper::DRIVER, STEP_PIN_PUMPE4,  DIR_PIN_PUMPE4);
AccelStepper PUMPE5  (AccelStepper::DRIVER, STEP_PIN_PUMPE5,  DIR_PIN_PUMPE5);
AccelStepper PUMPE6  (AccelStepper::DRIVER, STEP_PIN_PUMPE6,  DIR_PIN_PUMPE6);
AccelStepper PUMPE7  (AccelStepper::DRIVER, STEP_PIN_PUMPE7,  DIR_PIN_PUMPE7);
AccelStepper PUMPE8  (AccelStepper::DRIVER, STEP_PIN_PUMPE8,  DIR_PIN_PUMPE8);
AccelStepper PUMPE9  (AccelStepper::DRIVER, STEP_PIN_PUMPE9,  DIR_PIN_PUMPE9);
AccelStepper PUMPE10 (AccelStepper::DRIVER, STEP_PIN_PUMPE10, DIR_PIN_PUMPE10);


//       Arrays

AccelStepper* MOT[] = {
  &PLF, &BAND,
  &PUMPE1, &PUMPE2, &PUMPE3, &PUMPE4,
  &PUMPE5, &PUMPE6, &PUMPE7, &PUMPE8, &PUMPE9, &PUMPE10
};

TMC2209Stepper* DRV[] = {
  &driver_plf, &driver_band,
  &driver_pumpe1, &driver_pumpe2,
  &driver_pumpe3, &driver_pumpe4,
  &driver_pumpe5, &driver_pumpe6,
  &driver_pumpe7, &driver_pumpe8,
  &driver_pumpe9, &driver_pumpe10
};


//   Task Status

// Pumpe: laeuft schrittbasiert fuer die berechnete Laufzeit.
struct PumpTask {
  AccelStepper* motor;
  bool active;
};
PumpTask activePump = { nullptr, false };

struct BandTask {
  AccelStepper* motor;
  unsigned long stopTime; // >0 Timer (Entladen), 0 Sensor (Beladen)
  bool stopping;
};
BandTask activeBandTask = { nullptr, 0, false };


//         I2C-Variablen

volatile uint8_t  aufgabe_i2c  = 0;
volatile int16_t  par_generic  = 0;     // bei FAHR: mm
volatile uint8_t  pumpe_id_i2c = 0;
volatile uint8_t  zeit_sek_i2c = 0;
volatile bool     new_message  = false;
volatile uint8_t  last_cmd     = 0;


//         Helper
// Rechnet die vom Master gesendete Position in Millimetern auf Steps um.
inline long mmToSteps(int mm) {
  return (long)mm * (long)STEPS_PER_MM;
}

// Einheitliche Initialisierung fuer alle TMC2209-Treiber.
void driverCommonInit(TMC2209Stepper& d, int microsteps, int current_mA, uint8_t ihold_val) {
  d.begin();
  d.pdn_disable(true);
  d.mstep_reg_select(true);
  d.toff(8);
  d.microsteps(microsteps);
  d.en_spreadCycle(true);
  d.pwm_autoscale(true);
  d.I_scale_analog(false);
  d.vsense(true);
  d.rms_current(current_mA);
  d.ihold(ihold_val);
  d.iholddelay(0);
}

// Einheitliche Initialisierung fuer alle Stepper-Objekte.
void stepperCommonInit(AccelStepper& s, float vmax, float a) {
  s.setMaxSpeed(vmax);
  s.setAcceleration(a);
  s.setMinPulseWidth(5);
}

// Liest den Glas-Sensor.
static inline bool glassDetected() {
  // IR-Sensor liefert LOW, wenn ein Glas erkannt wurde.
  return !PIN_READ(IR_BELEGT);
}

// Startet eine lange Bewegung, bis spaeter aktiv gestoppt wird.
void startContinuousMove(AccelStepper& m, bool forward) {
  long target = m.currentPosition() + (forward ? CONTINUOUS_STEPS : -CONTINUOUS_STEPS);
  m.moveTo(target);
}

// Verwirft eventuell noch uebrige Bytes aus dem I2C-Empfangspuffer.
void discardRemainingI2CBytes() {
  while (Wire.available()) {
    (void)Wire.read();
  }
}

// Stoppt eine laufende Pumpe sauber.
void stopActivePump() {
  if (activePump.active && activePump.motor) {
    activePump.motor->setSpeed(0);
    activePump.active = false;
    activePump.motor = nullptr;
  }
}

// Fordert einen laufenden Band-Task zum Anhalten auf.
void stopBandTaskIfRunning() {
  if (activeBandTask.motor != nullptr) {
    activeBandTask.motor->stop();
    activeBandTask.stopping = true;
  }
}

// Stoppt alle laufenden Bewegungen und Aufgaben sofort.
void stopAllMotion() {
  stopActivePump();

  if (activeBandTask.motor != nullptr) {
    activeBandTask.motor->setSpeed(0);
    activeBandTask.motor->moveTo(activeBandTask.motor->currentPosition());
  }
  activeBandTask.motor = nullptr;
  activeBandTask.stopTime = 0;
  activeBandTask.stopping = false;

  PLF.setSpeed(0);
  PLF.moveTo(PLF.currentPosition());

  BAND.setSpeed(0);
  BAND.moveTo(BAND.currentPosition());

  for (int i = 2; i < 12; ++i) {
    MOT[i]->setSpeed(0);
    MOT[i]->moveTo(MOT[i]->currentPosition());
  }

  busy = false;
}

// Startet einen neuen Band-Task im Sensor- oder Timer-Modus.
void startBandTask(bool forward, unsigned long stopTimeMs) {
  startContinuousMove(BAND, forward);

  activeBandTask.motor = &BAND;
  activeBandTask.stopTime = stopTimeMs;
  activeBandTask.stopping = false;
  band_belegt_flag = false;
}

// Aktualisiert das busy-Flag anhand der aktuell laufenden Aufgaben.
void updateBusyState() {
  if (PLF.distanceToGo() == 0 && activeBandTask.motor == nullptr && !activePump.active) {
    busy = false;
  }
}

// Liest den Glas-Sensor in festem Abstand ein.
void updateGlassSensor() {
  static unsigned long lastOccupancyMeasureMs = 0;
  const unsigned long OCCUPANCY_MEASURE_INTERVAL_MS = 100;

  if (millis() - lastOccupancyMeasureMs >= OCCUPANCY_MEASURE_INTERVAL_MS) {
    lastOccupancyMeasureMs = millis();
    band_belegt_flag = glassDetected();
  }
}

// Arbeitet einen laufenden Band-Task weiter ab.
void updateBandTask() {
  if (activeBandTask.motor == nullptr) {
    return;
  }

  activeBandTask.motor->run();

  if (activeBandTask.stopTime > 0) {
    // Timer-Modus: Band laeuft bis die feste Zeit abgelaufen ist.
    if (!activeBandTask.stopping && millis() >= activeBandTask.stopTime) {
      activeBandTask.motor->stop();
      activeBandTask.stopping = true;
    }

    if (activeBandTask.stopping && activeBandTask.motor->distanceToGo() == 0) {
      activeBandTask.motor = nullptr;
      activeBandTask.stopTime = 0;
      activeBandTask.stopping = false;
      busy = false;
    }
    return;
  }

  // Sensor-Modus: Band stoppt, sobald ein Glas erkannt wird.
  static unsigned long lastMeasureMs = 0;
  const unsigned long MEASURE_INTERVAL_MS = 100;

  if (!activeBandTask.stopping && (millis() - lastMeasureMs >= MEASURE_INTERVAL_MS)) {
    lastMeasureMs = millis();
    if (glassDetected()) {
      band_belegt_flag = true;
      activeBandTask.motor->stop();
      activeBandTask.stopping = true;
    }
  }

  if (activeBandTask.stopping && activeBandTask.motor->distanceToGo() == 0) {
    activeBandTask.motor = nullptr;
    activeBandTask.stopTime = 0;
    activeBandTask.stopping = false;
    busy = false;
  }
}

// Arbeitet einen laufenden Pumpen-Task weiter ab.
void updatePumpTask() {
  if (!activePump.active || activePump.motor == nullptr) {
    return;
  }

  // Die Pumpe laeuft mit konstanter Geschwindigkeit bis zur Zielposition.
  activePump.motor->runSpeedToPosition();

  if (activePump.motor->distanceToGo() == 0) {
    activePump.motor->setSpeed(0);
    activePump.active = false;
    activePump.motor = nullptr;
    busy = false;
  }
}

// Baut das 5-Byte-Statuspaket und sendet es an den Master.
void writeStatusPacket() {
  uint8_t out[5];

  bool current_busy = busy;
  if (!current_busy) {
    current_busy =
      (PLF.distanceToGo() != 0) ||
      (activeBandTask.motor != nullptr) ||
      (activePump.active);
  }

  long pos_steps = PLF.currentPosition();
  long pos_mm_long = pos_steps / STEPS_PER_MM;

  if (pos_mm_long > 32767) pos_mm_long = 32767;
  if (pos_mm_long < -32768) pos_mm_long = -32768;
  int16_t pos_mm = (int16_t)pos_mm_long;

  out[0] = current_busy ? 1 : 0;
  out[1] = band_belegt_flag ? 1 : 0;
  out[2] = (uint8_t)(pos_mm & 0xFF);
  out[3] = (uint8_t)((pos_mm >> 8) & 0xFF);
  out[4] = is_homed ? 1 : 0;

  Wire.write(out, 5);
}

// Fuehrt ein zuvor empfangenes I2C-Kommando im loop() aus.
void handlePendingCommand() {
  if (!new_message) {
    return;
  }

  noInterrupts();
  uint8_t cmd = aufgabe_i2c;
  int16_t mm = par_generic;
  new_message = false;
  interrupts();

  switch (cmd) {
    case CMD_FAHR:     fahren_mm(mm); break;
    case CMD_HOME:     (void)home();  break;
    case CMD_STATUS:   break;
    case CMD_PUMPE:    pumpe();       break;
    case CMD_ENTLADEN: entladen();    break;
    case CMD_BELADEN:  beladen();     break;
    case CMD_STOP:     stopAllMotion(); break;
    default: break;
  }
}


//         Funktionen
// Faehrt den Schlitten auf die angeforderte Position.
void fahren_mm(int16_t mm) {
  busy = true;
  PLF.moveTo(mmToSteps((int)mm));
}

// Startet das Entladen in Richtung Ausgang.
void entladen() {
  stopActivePump();
  stopBandTaskIfRunning();
  startBandTask(false, millis() + BAND_TIMEOUT_MS);

  PLF.stop();
  busy = true;
}

// Startet das Beladen bis ein Glas erkannt wird.
void beladen() {
  stopActivePump();
  stopBandTaskIfRunning();
  startBandTask(true, 0);

  PLF.stop();
  busy = true;
}

// Referenziert den Schlitten am Home-Sensor.
bool home() {
  busy = true;
  is_homed = false;

  const float HOME_SPEED = -800.0f;
  const unsigned long TIMEOUT_MS = 200000;

  float oldMax = PLF.maxSpeed();
  float oldAcc = PLF.acceleration();

  PLF.setMaxSpeed(fabsf(HOME_SPEED));
  PLF.setAcceleration(accel_sps2[0]);
  PLF.setSpeed(HOME_SPEED);

  unsigned long t0 = millis();

  while (PIN_READ(HOME)) {
    PLF.runSpeed();
    if (millis() - t0 > TIMEOUT_MS) {
      PLF.setMaxSpeed(oldMax);
      PLF.setAcceleration(oldAcc);
      busy = false;
      is_homed = false;
      return false;
    }
  }

  PLF.setSpeed(0);
  PLF.moveTo(PLF.currentPosition());
  PLF.setCurrentPosition(0);

  PLF.setMaxSpeed(oldMax);
  PLF.setAcceleration(oldAcc);

  busy = false;
  is_homed = true;
  return true;
}

// Pumpen: Zeit kommt vom Master (Sekunden)
// Wir rechnen Zeit -> Steps um (Steps = speed[steps/s] * duration[s])
// Dann fahren wir schrittbasiert bis Zielposition (runSpeedToPosition()).
// Ergebnis: Wenn Master 10s schickt, läuft sie ~10s (bei eingestellter speed).
void pumpe() {
  busy = true;

  uint8_t pump_id = pumpe_id_i2c;
  uint8_t duration_s = zeit_sek_i2c;

  if (!(pump_id >= 1 && pump_id <= 10)) {
    busy = false;
    return;
  }

  int motor_array_index = (int)pump_id + 1; // 1->2 (=P1) ... 10->11 (=P10)
  AccelStepper* motor = MOT[motor_array_index];

  // Falls andere Pumpe aktiv: sofort stoppen
  if (activePump.active && activePump.motor && activePump.motor != motor) {
    activePump.motor->setSpeed(0);
    activePump.active = false;
    activePump.motor = nullptr;
  }

  if (duration_s == 0) {
    // Stop-Befehl
    motor->setSpeed(0);
    motor->moveTo(motor->currentPosition());
    if (activePump.motor == motor) {
      activePump.active = false;
      activePump.motor = nullptr;
    }
    busy = false;
    return;
  }

  // Geschwindigkeit aus Konfiguration (steps/s)
  // (Wenn du rückwärts pumpen willst: speed = -speed;)
  float speed = motor->maxSpeed();

  // Dynamisch: Steps = Zeit * Speed
  // (Runden damit 10 Sekunden möglichst exakt werden)
  long steps_to_run = (long)lroundf((float)duration_s * fabsf(speed));

  long target = motor->currentPosition() + (speed >= 0 ? steps_to_run : -steps_to_run);

  motor->moveTo(target);
  motor->setSpeed(speed);

  activePump.motor = motor;
  activePump.active = true;
}

//         I2C
void onI2CReceive(int count) {
  if (count <= 0) {
    discardRemainingI2CBytes();
    return;
  }

  uint8_t cmd = Wire.read();
  aufgabe_i2c = cmd;
  last_cmd = cmd;

  if (cmd == CMD_FAHR) {
    if (count >= 3 && Wire.available() >= 2) {
      uint8_t low  = Wire.read();
      uint8_t high = Wire.read();
      par_generic = (int16_t)((uint16_t)low | ((uint16_t)high << 8)); // mm
    }
    discardRemainingI2CBytes();
    new_message = true;
    return;
  }

  if (cmd == CMD_PUMPE) {
    if (count >= 3 && Wire.available() >= 2) {
      pumpe_id_i2c = Wire.read();
      zeit_sek_i2c = Wire.read(); // Sekunden 0..255
    }
    discardRemainingI2CBytes();
    new_message = true;
    return;
  }

  discardRemainingI2CBytes();
  new_message = true;
}

// Status: [busy, band, pos_low, pos_high, homing]
void onI2CRequest() {
  if (last_cmd == CMD_STATUS) {
    writeStatusPacket();
    return;
  }

  const uint8_t ack = 0x06;
  Wire.write(&ack, 1);
}


//         Setup / Loop
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
  digitalWrite(EN_PIN_NUM, HIGH); // deaktiviert

  is_homed = false;

  // Home-Sensor vorbereiten.
  PIN_INPUT(HOME);
  PIN_PULLUP_ON(HOME);

  // Glas-Sensor vorbereiten.
  PIN_INPUT(IR_BELEGT);

  // Alle Treiber und Stepper mit den Tabellenwerten initialisieren.
  for (int i = 0; i < 12; ++i) {
    driverCommonInit(*DRV[i], steps_u[i], current_mA[i], ihold_vals[i]);
    stepperCommonInit(*MOT[i], max_speed[i], accel_sps2[i]);
    MOT[i]->setSpeed(0);
    MOT[i]->moveTo(MOT[i]->currentPosition());
  }

  // Treiber aktiv schalten.
  digitalWrite(EN_PIN_NUM, LOW); // aktiv
}

void loop() {
  // Sensoren und laufende Bewegungen zyklisch aktualisieren.
  updateGlassSensor();
  PLF.run();

  // busy automatisch zurücksetzen, wenn wirklich nichts aktiv
  updateBusyState();

  updateBandTask();

  updatePumpTask();

  // I2C Kommandos ausführen
  updateBusyState();

  // Neue I2C-Kommandos werden immer erst hier im loop() ausgefuehrt.
  handlePendingCommand();
}
 
