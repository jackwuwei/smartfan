/*
 * 19" 2U smart temperature-controlled fan -- Arduino UNO R4 WiFi firmware
 * ---------------------------------------------------------------
 * Features:
 *   - 3x 80mm 4-pin PWM fans: 25kHz PWM speed control; PST daisy-chain (only the master fan reports TACH)
 *   - DS18B20 module for temperature (module has an onboard 4.7k pull-up)
 *   - Local closed-loop control (fan curve + slew limiting + failsafe), 4 modes; keeps running during provisioning
 *   - KY-040 rotary encoder: adjust setpoint / cycle pages / switch mode
 *   - 0.96" I2C OLED (SSD1306, 128x64) front-panel display; whole screen blinks on alarm
 *   - WiFi + MQTT to Home Assistant (auto-discovery); HA then bridges to HomeKit
 *   - Setpoint/mode stored in EEPROM, survives power loss
 *
 * Required libraries (install via Library Manager):
 *   ArduinoMqttClient, ArduinoJson, OneWire, DallasTemperature,
 *   Adafruit GFX Library, Adafruit SSD1306, QRCode (Richard Moore)
 *   (WiFiS3 / Wire / pwm.h (PwmOut) / EEPROM ship with the R4 core)
 *
 * Fan PWM: a single D9 line -> pin 4 of all 3 fans (4-wire fan PWM is a high-impedance input, so one line can be shared, per the Intel 4-wire spec).
 *   By default PwmOut (R4 core, per-pin hardware PWM) drives D9 (=GTIOC7A/GPT7) at a **true 25kHz (silent)**;
 *   only one timer is used, no pin guessing. If you hit problems, set USE_PWMOUT_25K to 0 to fall back to analogWrite (~490Hz, slight whine).
 *   TACH: with the PST daisy-chain only the master fan reports speed, on a single line to D2 (D7/D8 left unused).
 */

#include <WiFiS3.h>
#include <ArduinoMqttClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <EEPROM.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "qrcode.h"                          // provisioning QR code (Library Manager: "QRCode" by Richard Moore)

// ===================== User config =====================
// WiFi / MQTT / device ID are not hardcoded: on first boot (or after reset) the provisioning portal starts --
// the OLED shows a QR code, scan it to join the device's AP, fill in the web form and save (see provisioning section below).
const char* AP_SSID   = "RackFan-Setup";     // provisioning AP name (joined automatically via QR)
const char* AP_PASS   = "configme123";       // provisioning AP password (>=8 chars; embedded in the QR). Default -- change before flashing to keep the setup AP private (anyone nearby can join it during provisioning)
const char* DEVID_DEFAULT = "rackfan01";     // default device ID (editable in the portal)

// ---- Pins ----
const uint8_t FAN_PWM_PIN = 9;             // one PWM line -> pin 4 of all 3 fans (high-Z input, shareable; true 25kHz)
const uint8_t TACH_PIN = 2;                // PST daisy-chain: master fan TACH only (open-collector, internal pull-up); D7/D8 unused
const uint8_t ONEWIRE_PIN = 4;             // DS18B20
const uint8_t ENC_A = 3, ENC_B = 6, ENC_SW = 12;  // KY-040: CLK=D3 (interrupt-capable) / DT=D6 / SW=D12

// ---- Display: 0.96" I2C OLED (SSD1306, 128x64) ----
// Wired to the UNO R4 WiFi's dedicated SDA/SCL pins (onboard Wire); VCC=5V/3V3, GND. Address is usually 0x3C.
#define OLED_W      128
#define OLED_H      64
#define OLED_ADDR   0x3C

// ---- Bench debug switch ----
// 1 = verify the control logic without sensor/fans/encoder/OLED attached:
//     (1) opens 115200 serial, prints temp/duty/RPM/mode/alarm every second
//     (2) simulates temperature with a millis-driven triangle wave (20->65->20, ~60s) and RPM from duty
//        -- sweeps the curve floor / linear region / T_CRIT failsafe, without false stall alarms
// Note: the provisioning portal still runs (not skipped). After first boot/reset, join RackFan-Setup
//       with a phone and complete provisioning; serial output starts only after the reboot into the main loop. Set back to 0 for production.
#define DEBUG_NO_HW    0

// ---- Control parameters (defaults, may be overridden by EEPROM/HA) ----
#define USE_PWMOUT_25K 1                   // 1=PwmOut true 25kHz (default, silent); 0=analogWrite ~490Hz (fallback)
const float T_CRIT   = 60.0f;              // critical temperature -> force 100%
const uint8_t DUTY_FLOOR = 20;             // minimum duty % in auto mode
const uint8_t SILENT_CAP = 60;             // duty cap % in silent mode
const uint16_t STALL_RPM = 60;             // below this counts as stalled
const uint32_t WIFI_BEGIN_WAIT = 2000;     // max ms WiFi.begin() may block the loop (core default 10000)
const uint32_t WIFI_RETRY_MS   = 15000;    // WiFi re-begin interval (long enough for a join to finish in the background)
const uint32_t MQTT_RETRY_MS   = 5000;     // MQTT reconnect interval

enum Mode : uint8_t { AUTO=0, MANUAL=1, SILENT=2, TURBO=3 };
const char* MODE_NAME[4] = {"Auto", "Manual", "Silent", "Turbo"};

// Persistent config
struct Config {
  uint32_t magic;       // validity marker
  float    setpoint;    // target temperature °C (auto-curve midpoint)
  uint8_t  mode;        // Mode
  uint8_t  manualDuty;  // manual duty %
  bool     power;       // on/off
} cfg;
const uint32_t CFG_MAGIC = 0x52464E31;     // "RFN1"

// Network config (WiFi / MQTT / device ID), stored in EEPROM, written by the portal page
struct NetCfg {
  uint32_t magic;
  char ssid[33];      // WiFi SSID
  char pass[65];      // WiFi password
  char host[40];      // MQTT host
  uint16_t port;      // MQTT port
  char user[33];      // MQTT user (empty = anonymous)
  char mpass[33];     // MQTT password
  char devid[24];     // device ID
} netcfg;
const uint32_t NETCFG_MAGIC = 0x4E455431;  // "NET1"
const int      NETCFG_ADDR  = 512;         // EEPROM offset (clear of cfg@0)

// ===================== Global state =====================
WiFiClient   wifiClient;
MqttClient   mqtt(wifiClient);
OneWire      oneWire(ONEWIRE_PIN);
DallasTemperature ds18(&oneWire);
Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, -1);

float   g_temp = NAN;          // current temperature
uint8_t g_duty = 0;            // current duty %
uint16_t g_rpm = 0;            // master fan RPM (single PST line)
volatile uint32_t g_pulses = 0;
bool    g_alarm = false;
const char* g_alarmMsg = "";
uint8_t g_page = 0;            // encoder-selected item: 0 temp, 1 setpoint, 2 fan %, 3 mode (for the big-text edit hint)
uint32_t g_uiTouch = 0;        // time of last encoder action (edit hint display window)

// Task timers
uint32_t tSample=0, tDisplay=0, tMqtt=0, tReconnect=0;

// ===================== TACH interrupt =====================
void isr0(){ g_pulses++; }                 // single PST TACH (master fan)

// ===================== Fan PWM (single D9 line, split to 3 fans) =====================
#if USE_PWMOUT_25K
#include "pwm.h"                        // R4 core: per-pin hardware PWM (PwmOut -> D9=GTIOC7A/GPT7)
PwmOut fanPwm(FAN_PWM_PIN);
void pwmBegin() { fanPwm.begin(25000.0f, 0.0f); }                 // true 25kHz (silent), start at 0%
void pwmSet(uint8_t duty) { fanPwm.pulse_perc(constrain((float)duty, 0.0f, 100.0f)); }  // 0..100 %
#else
void pwmBegin() { pinMode(FAN_PWM_PIN, OUTPUT); analogWrite(FAN_PWM_PIN, 0); }  // fallback: analogWrite ~490Hz
void pwmSet(uint8_t duty) { analogWrite(FAN_PWM_PIN, map(constrain(duty,0,100), 0, 100, 0, 255)); }
#endif

// ===================== EEPROM =====================
void cfgLoad() {
  EEPROM.get(0, cfg);
  if (cfg.magic != CFG_MAGIC) {        // first boot: write defaults
    cfg.magic = CFG_MAGIC;
    cfg.setpoint = 35.0f; cfg.mode = AUTO; cfg.manualDuty = 50; cfg.power = true;
    EEPROM.put(0, cfg);
  }
  // Sanitize: a corrupt EEPROM must not index MODE_NAME out of range or yield a NaN setpoint
  if (cfg.mode > TURBO) cfg.mode = AUTO;
  if (isnan(cfg.setpoint) || cfg.setpoint < 25 || cfg.setpoint > 55) cfg.setpoint = 35.0f;
  if (cfg.manualDuty > 100) cfg.manualDuty = 50;
}
// Deferred save: knob detents / HA commands only mark the config dirty; it is written once,
// CFG_SAVE_DELAY ms after the last change (spinning the knob no longer writes EEPROM per detent).
const uint32_t CFG_SAVE_DELAY = 3000;
bool     g_cfgDirty = false;
uint32_t g_cfgDirtyAt = 0;
void cfgSave() { g_cfgDirty = true; g_cfgDirtyAt = millis(); }
void cfgSaveStep() {
  if (g_cfgDirty && millis() - g_cfgDirtyAt >= CFG_SAVE_DELAY) { EEPROM.put(0, cfg); g_cfgDirty = false; }
}

// ===================== Control core =====================
uint8_t curveDuty(float t) {           // fan curve: Tset-10 -> floor, Tset+6 -> 100
  float lo = cfg.setpoint - 10.0f, hi = cfg.setpoint + 6.0f;
  if (isnan(t))      return 100;       // sensor failure -> full speed
  if (t <= lo)       return DUTY_FLOOR;
  if (t >= hi)       return 100;
  return (uint8_t)(DUTY_FLOOR + (t - lo) * (100 - DUTY_FLOOR) / (hi - lo));
}

void controlStep() {
  // 1) Safety: critical temp / sensor failure -> force 100%
  bool overTemp = (!isnan(g_temp) && g_temp >= T_CRIT);
  bool sensorBad = isnan(g_temp) || g_temp < -50 || g_temp > 125;

  uint8_t target;
  if (!cfg.power) {
    target = 0;
  } else if (overTemp || sensorBad) {
    target = 100;
  } else {
    switch (cfg.mode) {
      case MANUAL: target = cfg.manualDuty; break;
      case TURBO:  target = 100; break;
      case SILENT: { uint8_t c = curveDuty(g_temp); target = (c < SILENT_CAP) ? c : SILENT_CAP; break; }
      case AUTO:
      default:     target = curveDuty(g_temp); break;
    }
  }

  // 2) Slew-rate limit (max 5% per step) to avoid duty jumps; the curve slope itself provides hysteresis
  const int step = 5;
  if (target > g_duty)      g_duty += (target - g_duty > step) ? step : (target - g_duty);
  else if (target < g_duty) g_duty -= (g_duty - target > step) ? step : (g_duty - target);
  pwmSet(g_duty);

  // 3) Alarms: over-temp / sensor failure / stall (driven but no RPM)
  bool stall = false;
  if (cfg.power && g_duty > 25) {
    if (g_rpm < STALL_RPM) stall = true;     // PST: only the master fan is measurable; the other two have no own TACH
  }
  g_alarm = overTemp || sensorBad || stall;
  g_alarmMsg = overTemp ? "OVERTEMP" : sensorBad ? "SENSOR" : stall ? "STALL" : "";
}

// ===================== Bench debug (no peripherals) =====================
#if DEBUG_NO_HW
// Triangle-wave temperature: 20->65->20, ~60s period. Covers the curve floor (<=Tset-10) / linear region /
// full-speed region (>=Tset+6) / failsafe (>=T_CRIT=60). RPM simulated from duty, >STALL_RPM to avoid false stall alarms.
void simSensors() {
  const float TMIN = 20.0f, TMAX = 65.0f, PERIOD = 60000.0f;
  float ph  = fmod((float)millis(), PERIOD) / PERIOD;            // 0..1
  float tri = (ph < 0.5f) ? (ph * 2.0f) : (2.0f - ph * 2.0f);    // 0..1..0
  g_temp = TMIN + (TMAX - TMIN) * tri;
  g_rpm = (g_duty > 0) ? (uint16_t)(g_duty * 18) : 0;           // 0..1800 rpm
}
void dbgPrint() {
  Serial.print("T=");      Serial.print(g_temp, 1);
  Serial.print("C  duty="); Serial.print(g_duty);
  Serial.print("%  rpm=");  Serial.print(g_rpm);
  Serial.print("  mode=");  Serial.print(MODE_NAME[cfg.mode]);
  Serial.print("  power="); Serial.print(cfg.power ? "ON" : "OFF");
  Serial.print("  alarm="); Serial.println(g_alarm ? g_alarmMsg : "none");
}
#endif

// ===================== Sampling =====================
void sampleStep() {
  // Temperature
  ds18.requestTemperatures();
  float t = ds18.getTempCByIndex(0);
  g_temp = (t == DEVICE_DISCONNECTED_C) ? NAN : t;
  // RPM: pulses/s -> RPM (2 pulses/rev); with PST only the master fan has TACH
  noInterrupts();
  uint32_t p = g_pulses; g_pulses = 0;
  interrupts();
  g_rpm = (uint16_t)(p * 30);   // /2*60
#if DEBUG_NO_HW
  simSensors();                            // no peripherals: overwrite real readings with simulated values
#endif
}

// ===================== Display (0.96" OLED, SSD1306) =====================
// Product-style layout: top = WiFi signal + mode, middle = large temperature (thermometer icon), bottom = master fan RPM (fan icon).
// For 2.5s after an encoder action, the big middle text temporarily shows the edited item (setpoint/fan %/mode) as "blind-adjust" feedback.
static void drawThermo(int x, int y) {            // small thermometer icon (tube top at y)
  oled.drawRect(x - 2, y, 5, 13, SSD1306_WHITE);        // tube
  oled.fillRect(x - 1, y + 6, 3, 9, SSD1306_WHITE);     // mercury
  oled.fillCircle(x, y + 15, 4, SSD1306_WHITE);         // bulb
}
static void drawFanIcon(int cx, int cy) {         // small fan icon (center, radius 5)
  oled.drawCircle(cx, cy, 5, SSD1306_WHITE);
  oled.fillCircle(cx, cy, 1, SSD1306_WHITE);
  oled.drawLine(cx, cy, cx + 3, cy - 3, SSD1306_WHITE);
  oled.drawLine(cx, cy, cx - 3, cy + 3, SSD1306_WHITE);
  oled.drawLine(cx, cy, cx + 3, cy + 2, SSD1306_WHITE);
}
static void drawDeg(int x, int y) { oled.drawCircle(x, y, 2, SSD1306_WHITE); }   // degree symbol

void drawSplash(const char* s) {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(2);
  oled.setCursor(0, 24);
  oled.print(s);
  oled.display();
}
void displayStep() {
  static bool blink = false; blink = !blink;
  oled.clearDisplay();
  if (g_alarm && blink) { oled.display(); return; }   // alarm: blink whole screen
  oled.setTextColor(SSD1306_WHITE);

  // ---- Top bar: WiFi signal (left) + alarm badge + mode (right) ----
  bool wok = (WiFi.status() == WL_CONNECTED);
  int rssi = wok ? WiFi.RSSI() : -127;
  int nb = !wok ? 0 : rssi >= -55 ? 4 : rssi >= -67 ? 3 : rssi >= -78 ? 2 : 1;
  for (int i = 0; i < 4; i++) {
    int bx = 2 + i * 4, bh = 3 + i * 2, by = 12 - bh;
    if (i < nb) oled.fillRect(bx, by, 3, bh, SSD1306_WHITE);
    else        oled.drawRect(bx, by, 3, bh, SSD1306_WHITE);
  }
  oled.setTextSize(1);
  if (!wok)    { oled.setCursor(21, 4); oled.print("x"); }       // not connected
  if (g_alarm) { oled.setCursor(40, 4); oled.print("ALM"); }
  const char* mn = MODE_NAME[cfg.mode];
  oled.setCursor(128 - (int)strlen(mn) * 6, 4); oled.print(mn);
  oled.drawFastHLine(0, 15, 128, SSD1306_WHITE);

  // ---- Middle big text: default = current temp; for 2.5s after an encoder action = edited item ----
  bool editing = g_uiTouch && (millis() - g_uiTouch < 2500) && g_page != 0;
  if (editing) {
    // Edit hint sits upper-middle in 2x font, **without crowding the bottom status row** (RPM/% stay visible)
    const char* tag = (g_page == 1) ? "SET" : (g_page == 2) ? "FAN" : "MODE";
    oled.setTextSize(1); oled.setCursor(6, 17); oled.print(tag);
    oled.setTextSize(2);
    if (g_page == 3) {                                           // mode name
      oled.setCursor(6, 27); oled.print(MODE_NAME[cfg.mode]);
    } else if (g_page == 1) {                                    // setpoint
      int v = (int)round(cfg.setpoint);
      oled.setCursor(6, 27); oled.print(v);
      int ex = 6 + (v >= 100 ? 3 : v >= 10 ? 2 : 1) * 12;
      drawDeg(ex + 2, 29); oled.setCursor(ex + 6, 27); oled.print("C");
    } else {                                                     // fan %
      oled.setCursor(6, 27); oled.print(g_duty);
      int ex = 6 + (g_duty >= 100 ? 3 : g_duty >= 10 ? 2 : 1) * 12;
      oled.setCursor(ex + 2, 27); oled.print("%");
    }
  } else {
    drawThermo(8, 22);
    oled.setTextSize(3); oled.setCursor(22, 22);
    if (isnan(g_temp)) { oled.print("--"); }
    else {
      oled.print(g_temp, 1);                                      // one decimal, e.g. 26.8
      int digits = (g_temp >= 100) ? 5 : (g_temp >= 10) ? 4 : 3; // char count incl. decimal point
      int ex = 22 + digits * 18;
      drawDeg(ex + 3, 25);
      oled.setTextSize(2); oled.setCursor(ex + 8, 28); oled.print("C");
    }
  }

  // ---- Bottom: master fan RPM (fan icon, left) + current duty (right) ----
  drawFanIcon(8, 56);
  int rpm = g_rpm;
  oled.setTextSize(1); oled.setCursor(20, 53); oled.print(rpm); oled.print(" RPM");
  char ds[8]; snprintf(ds, sizeof(ds), "%d%%", g_duty);
  oled.setCursor(128 - (int)strlen(ds) * 6, 53); oled.print(ds);

  oled.display();
}

// ===================== KY-040 encoder =====================
// CLK on D3 (on the R4 WiFi only D2/D3 officially support external interrupts; D2 is taken by TACH, so the encoder uses D3).
// The ISR reads DT on the CLK falling edge to get direction -- unaffected by OLED/MQTT time spent in loop, no missed steps, correct direction.
// (Previously CLK on D5 with attachInterrupt never fired; polling instead missed steps -- hence the move to D3 with an interrupt.)
volatile int8_t g_encDelta = 0;
void encISR() {                       // on CLK falling edge read DT for direction (swap +1/-1 if reversed)
  static uint32_t lastMs = 0;
  uint32_t now = millis();
  if (now - lastMs < 5) return;       // debounce: ignore bounce edges within 5ms (one count per detent)
  lastMs = now;
  g_encDelta += (digitalRead(ENC_B) ? +1 : -1);
}
void encoderStep() {
  // Rotate: manual mode -> adjust fan % (±5); other modes -> adjust setpoint (±1)
  if (g_encDelta != 0) {
    noInterrupts(); int8_t d = g_encDelta; g_encDelta = 0; interrupts();
    if (cfg.mode == MANUAL) {
      cfg.manualDuty = constrain(cfg.manualDuty + d * 5, 0, 100);
      g_page = 2;                       // jump to "fan %" page
    } else {
      cfg.setpoint = constrain((int)cfg.setpoint + d, 25, 55);
      g_page = 1;                       // jump to "setpoint" page
    }
    g_uiTouch = millis();               // trigger edit hint (big text temporarily shows edited item)
    cfgSave(); mqttPublishState();
  }
  // Button: short press cycles page; long press switches mode
  static bool last = HIGH; static uint32_t tDown=0; static bool longDone=false;
  bool now = digitalRead(ENC_SW);
  if (last==HIGH && now==LOW) { tDown=millis(); longDone=false; }
  if (now==LOW && !longDone && millis()-tDown>800) {   // long press -> switch mode
    cfg.mode = (cfg.mode + 1) & 3; longDone=true; cfgSave(); g_page=3; g_uiTouch=millis(); mqttPublishState();
  }
  if (last==LOW && now==HIGH) {                          // release -> short press cycles page
    if (!longDone) { g_page = (g_page + 1) & 3; g_uiTouch = millis(); }
  }
  last = now;
}

// ===================== MQTT (Home Assistant auto-discovery) =====================
String baseT() { return String("rackfan/") + netcfg.devid; }   // state/command topic prefix

void mqttDiscovery() {
  String b = baseT();
  StaticJsonDocument<512> dev;            // shared device block
  dev["ids"][0] = netcfg.devid; dev["name"]="Smart Rack Fan"; dev["mf"]="DIY"; dev["mdl"]="UNO R4 WiFi";
  auto pub = [&](const char* comp, const char* obj, JsonDocument& d){
    String topic = String("homeassistant/")+comp+"/"+netcfg.devid+"/"+obj+"/config";
    d["dev"]=dev;
    String out; serializeJson(d, out);
    mqtt.beginMessage(topic, true); mqtt.print(out); mqtt.endMessage();   // retained
  };
  { StaticJsonDocument<512> d; d["name"]="Rack Fan"; d["uniq_id"]=String(netcfg.devid)+"_fan";
    d["stat_t"]=b+"/power/state"; d["cmd_t"]=b+"/power/set";
    d["pct_stat_t"]=b+"/pct/state"; d["pct_cmd_t"]=b+"/pct/set";
    pub("fan","fan",d); }
  // climate entity (shown as a thermostat in Apple Home: adjustable setpoint + on/off + mode presets)
  { StaticJsonDocument<1536> d; d["name"]="Rack Fan"; d["uniq_id"]=String(netcfg.devid)+"_clim";
    JsonArray md=d.createNestedArray("modes"); md.add("off"); md.add("cool");
    d["mode_state_topic"]=b+"/hvac/mode/state"; d["mode_command_topic"]=b+"/hvac/mode/set";
    d["temperature_state_topic"]=b+"/set/state"; d["temperature_command_topic"]=b+"/set/set";
    d["current_temperature_topic"]=b+"/temp/state";
    d["min_temp"]=25; d["max_temp"]=55; d["temp_step"]=1;
    JsonArray pr=d.createNestedArray("preset_modes"); for(auto&m:MODE_NAME) pr.add(m);
    d["preset_mode_state_topic"]=b+"/mode/state"; d["preset_mode_command_topic"]=b+"/mode/set";
    d["action_topic"]=b+"/action/state";
    pub("climate","climate",d); }
  { StaticJsonDocument<384> d; d["name"]="Temp"; d["uniq_id"]=String(netcfg.devid)+"_temp";
    d["stat_t"]=b+"/temp/state"; d["unit_of_meas"]="°C"; d["dev_cla"]="temperature";
    pub("sensor","temp",d); }
  { StaticJsonDocument<384> d; d["name"]="Fan RPM"; d["uniq_id"]=String(netcfg.devid)+"_rpm";
    d["stat_t"]=b+"/rpm/state"; d["unit_of_meas"]="rpm";      // PST: single RPM reading (master fan)
    pub("sensor","rpm",d); }
  { StaticJsonDocument<384> d; d["name"]="Alarm"; d["uniq_id"]=String(netcfg.devid)+"_alarm";
    d["stat_t"]=b+"/alarm/state"; d["dev_cla"]="problem";
    pub("binary_sensor","alarm",d); }
}

void mqttPublishState() {
  String b = baseT();
  auto p=[&](const String& t, const String& v){ mqtt.beginMessage(t,true); mqtt.print(v); mqtt.endMessage(); };
  p(b+"/power/state", cfg.power ? "ON":"OFF");
  p(b+"/pct/state",   String(g_duty));
  p(b+"/set/state",   String((int)round(cfg.setpoint)));
  p(b+"/mode/state",  MODE_NAME[cfg.mode]);
  p(b+"/hvac/mode/state", cfg.power ? "cool" : "off");
  p(b+"/action/state",   !cfg.power ? "off" : (g_duty > 0 ? "cooling" : "idle"));
  p(b+"/temp/state",  isnan(g_temp)? "unknown" : String(g_temp,1));
  p(b+"/rpm/state", String(g_rpm));
  p(b+"/alarm/state", g_alarm ? "ON":"OFF");
}

void mqttOnMessage(int len) {
  String topic = mqtt.messageTopic();
  String payload; while (mqtt.available()) payload += (char)mqtt.read();
  String b = baseT();
  if (topic == b+"/power/set")      cfg.power = (payload=="ON");
  else if (topic == b+"/pct/set") { cfg.manualDuty = constrain(payload.toInt(),0,100); cfg.mode=MANUAL; }
  else if (topic == b+"/set/set")   cfg.setpoint = constrain(payload.toInt(),25,55);
  else if (topic == b+"/mode/set") { for(int i=0;i<4;i++) if(payload==MODE_NAME[i]) cfg.mode=i; }   // braces required: otherwise the next else binds to the inner if
  else if (topic == b+"/hvac/mode/set") cfg.power = (payload=="cool");   // climate on/off
  cfgSave(); controlStep(); mqttPublishState();
}

bool mqttConnect() {
  if (WiFi.status()!=WL_CONNECTED) return false;
  mqtt.setId(netcfg.devid);
  mqtt.setConnectionTimeout(3000);      // default 30s CONNACK wait would stall sampling/control that long
  mqtt.setTxPayloadSize(1024);          // default is only 256B, which truncates the larger discovery JSON (climate/fan) -> HA drops the entity
  if (netcfg.user[0]) mqtt.setUsernamePassword(netcfg.user, netcfg.mpass);   // empty = anonymous
  if (!mqtt.connect(netcfg.host, netcfg.port)) return false;
  String b = baseT();
  mqtt.subscribe(b+"/power/set"); mqtt.subscribe(b+"/pct/set");
  mqtt.subscribe(b+"/set/set");   mqtt.subscribe(b+"/mode/set");
  mqtt.subscribe(b+"/hvac/mode/set");
  mqtt.onMessage(mqttOnMessage);
  mqttDiscovery();
  mqttPublishState();
  return true;
}

// ===================== Provisioning portal (first boot/reset: AP + web page + OLED QR) ===========
WiFiServer portal(80);
WiFiUDP    dnsUdp;                       // captive DNS: resolve every domain to this device -> phone auto-opens the config page
const IPAddress AP_IP(192, 168, 4, 1);  // default AP address used by beginAP

bool netLoad() {
  EEPROM.get(NETCFG_ADDR, netcfg);
  netcfg.ssid[sizeof(netcfg.ssid)-1] = netcfg.pass[sizeof(netcfg.pass)-1] = netcfg.host[sizeof(netcfg.host)-1] = 0;   // never trust EEPROM strings
  netcfg.user[sizeof(netcfg.user)-1] = netcfg.mpass[sizeof(netcfg.mpass)-1] = netcfg.devid[sizeof(netcfg.devid)-1] = 0;
  return netcfg.magic == NETCFG_MAGIC;
}
void netSave() { netcfg.magic = NETCFG_MAGIC; EEPROM.put(NETCFG_ADDR, netcfg); }
void netClear(){ netcfg.magic = 0; EEPROM.put(NETCFG_ADDR, netcfg); }

static String urlDecode(const String& s) {
  String o; auto hx=[](char h)->int{ return (h>='0'&&h<='9')?h-'0':((h|0x20)>='a'&&(h|0x20)<='f')?(h|0x20)-'a'+10:-1; };
  for (unsigned i=0;i<s.length();i++) {
    char c=s[i];
    if (c=='+') o+=' ';
    else if (c=='%' && i+2<s.length() && hx(s[i+1])>=0 && hx(s[i+2])>=0) { o+=(char)(hx(s[i+1])*16+hx(s[i+2])); i+=2; }
    else o+=c;                         // malformed escape: keep literally
  }
  return o;
}
static String qval(const String& q, const char* key) {     // get value of key=value from the query string
  String k=String(key)+"="; int i=-1;
  for (int f=q.indexOf(k); f>=0; f=q.indexOf(k, f+1))   // match only at a parameter boundary ("pass=" must not hit "mpass=")
    if (f==0 || q[f-1]=='&') { i=f; break; }
  if (i<0) return "";
  i+=k.length(); int e=q.indexOf('&', i);
  return urlDecode(q.substring(i, e<0?q.length():e));
}

String g_netOpts;     // scanned 2.4GHz networks as <option>s (fed into the datalist, no typing the SSID)

static String htmlEsc(const String& s) {
  String o;
  for (unsigned i=0;i<s.length();i++) { char c=s[i];
    if (c=='&') o+="&amp;"; else if (c=='<') o+="&lt;";
    else if (c=='>') o+="&gt;"; else if (c=='"') o+="&quot;"; else o+=c; }
  return o;
}
void scanNets() {                              // scan before starting the AP (still in STA mode)
  int n = WiFi.scanNetworks();                 // the R4 radio is 2.4GHz only -> every scanned network is 2.4G
  g_netOpts = ""; String seen = "\n";
  for (int i=0; i<n && i<15; i++) {
    String ss = String(WiFi.SSID(i));
    if (!ss.length()) continue;                // skip hidden networks
    if (seen.indexOf("\n"+ss+"\n") >= 0) continue;   // dedupe (multiple APs with the same name)
    seen += ss+"\n";
    g_netOpts += "<option value=\""+htmlEsc(ss)+"\">";
  }
}
String portalPage() {                          // dynamic: inject scanned networks into the dropdown
  return String(
    "<!doctype html><meta charset=utf-8><meta name=viewport content=\"width=device-width,initial-scale=1\">"
    "<title>Rack Fan Setup</title><style>body{font-family:sans-serif;max-width:420px;margin:auto;padding:16px}"
    "input{width:100%;padding:8px;margin:4px 0;box-sizing:border-box}label{font-weight:600}"
    "small{color:#666;display:block;margin-bottom:10px}button{width:100%;padding:12px;font-size:16px;margin-top:10px}"
    "</style><h2>2U Fan · Setup</h2><form action=/save>"
    "<label>WiFi SSID (2.4GHz only)</label><input name=ssid list=nets required autocomplete=off>"
    "<datalist id=nets>") + g_netOpts + String(
    "</datalist><small>⚠ <b>2.4GHz</b> only. Tap the field to pick a scanned network, or type one (hidden network). "
    "Don't see yours? It's probably 5GHz -- use the 2.4GHz network with the same name.</small>"
    "<label>WiFi password</label><input name=pass type=password>"
    "<label>MQTT host</label><input name=host value=homeassistant.local>"
    "<small>The MQTT broker (HA's Mosquitto add-on), <b>not</b> the web UI address. "
    "Default homeassistant.local; if it can't connect (the R4 may not resolve .local), use HA's IP, e.g. 192.168.1.10.</small>"
    "<label>MQTT port</label><input name=port value=1883>"
    "<small>Broker port, default 1883; <b>not</b> the web UI's 8123.</small>"
    "<label>MQTT user (empty = anonymous)</label><input name=user>"
    "<label>MQTT password</label><input name=mpass type=password>"
    "<label>Device ID</label><input name=devid value=rackfan01>"
    "<button>Save &amp; reboot</button></form>");
}

void portalSend(WiFiClient& c, const char* body) {
  c.print("HTTP/1.1 200 OK\r\nContent-Type:text/html;charset=utf-8\r\nConnection:close\r\n\r\n");
  c.print(body);
}
void portalDrawQR() {
  // QR = WiFi join string (scan to auto-join the AP); the OLED must draw "light background + dark modules" to be scannable
  String j = String("WIFI:T:WPA;S:")+AP_SSID+";P:"+AP_PASS+";;";
  QRCode qr; uint8_t buf[qrcode_getBufferSize(3)];
  qrcode_initText(&qr, buf, 3, ECC_LOW, j.c_str());
  oled.clearDisplay();
  int s=qr.size, sc=2, ox=2, oy=3;                                  // 29x2 = 58px
  oled.fillRect(0, oy-2, s*sc+3, s*sc+4, SSD1306_WHITE);            // white background + quiet zone
  for (int y=0;y<s;y++) for (int x=0;x<s;x++)
    if (qrcode_getModule(&qr,x,y)) oled.fillRect(ox+x*sc, oy+y*sc, sc, sc, SSD1306_BLACK);
  oled.setTextColor(SSD1306_WHITE); oled.setTextSize(1);
  oled.setCursor(63, 4);  oled.print("WiFi SET");
  oled.setCursor(63, 18); oled.print("scan QR");
  oled.setCursor(63, 30); oled.print("-> auto");
  oled.setCursor(63, 42); oled.print("or open:");
  oled.setCursor(62, 54); oled.print("192.168.4.1");
  oled.display();
}
// Minimal captive DNS: answer every query with an A record = AP_IP (same as the ESP8266 DNSServer "*" behavior).
// After joining the AP the phone runs its connectivity check (apple/google/microsoft probe domains) -> redirected here -> OS auto-opens the portal.
void dnsHandle() {
  int n = dnsUdp.parsePacket();
  if (n <= 0) return;
  uint8_t buf[300];
  int len = dnsUdp.read(buf, sizeof(buf));
  if (len < 12) return;                          // not a valid DNS header
  if ((buf[2] & 0x80) || buf[4] != 0 || buf[5] != 1) return;   // only plain queries with exactly 1 question
  int qe = 12;                                   // walk the QNAME labels to find the end of the question
  while (qe < len && buf[qe] != 0) {
    if (buf[qe] & 0xC0) return;                  // compression pointer inside a query: unexpected, ignore
    qe += buf[qe] + 1;
  }
  qe += 1 + 4;                                   // zero label + QTYPE + QCLASS
  if (qe > len) return;                          // truncated question
  len = qe;                                      // drop anything after the question (e.g. an EDNS0 OPT record)
  buf[2] = 0x81; buf[3] = 0x80;                  // QR=response, RD/RA=1, RCODE=0
  buf[6] = 0; buf[7] = 1;                        // ANCOUNT = 1
  buf[8] = buf[9] = buf[10] = buf[11] = 0;       // NSCOUNT/ARCOUNT = 0 (QDCOUNT stays 1)
  const uint8_t ans[] = {
    0xC0, 0x0C,                                  // NAME: pointer to the question name at offset 12
    0x00, 0x01, 0x00, 0x01,                      // TYPE=A, CLASS=IN
    0x00, 0x00, 0x00, 0x3C,                      // TTL=60s
    0x00, 0x04,                                  // RDLENGTH=4
    (uint8_t)AP_IP[0], (uint8_t)AP_IP[1], (uint8_t)AP_IP[2], (uint8_t)AP_IP[3]
  };
  if (len + (int)sizeof(ans) > (int)sizeof(buf)) return;
  memcpy(buf + len, ans, sizeof(ans));
  dnsUdp.beginPacket(dnsUdp.remoteIP(), dnsUdp.remotePort());
  dnsUdp.write(buf, len + sizeof(ans));
  dnsUdp.endPacket();
}

void runPortal() {
  // Temperature control keeps running inside the portal loop (sample + control every 1s), so the cabinet
  // stays cooled and the failsafe stays armed while waiting for provisioning. The OLED keeps showing the QR.
  sampleStep(); controlStep();
  oled.clearDisplay(); oled.setTextColor(SSD1306_WHITE); oled.setTextSize(1);
  oled.setCursor(0, 28); oled.print("Scanning WiFi..."); oled.display();
  scanNets();                                  // scan first (STA mode) -> list goes into the portal page
  WiFi.beginAP(AP_SSID, AP_PASS);              // then start the AP
  delay(1000);
  portal.begin();
  dnsUdp.begin(53);                            // captive DNS: hijack all domains -> portal auto-opens
  portalDrawQR();
  uint32_t tCtl = millis();
  for (;;) {
    if (millis() - tCtl >= 1000) { tCtl = millis(); sampleStep(); controlStep(); }
    dnsHandle();                               // handle DNS probes first, to trigger the auto-popup
    WiFiClient c = portal.available();
    if (!c) { delay(2); continue; }
    delay(20);                                 // wait for request headers to arrive
    String req = c.readStringUntil('\r');       // "GET /path?query HTTP/1.1"
    while (c.available()) c.read();
    int p1=req.indexOf(' '), p2=req.indexOf(' ', p1+1);
    String url = (p1>=0&&p2>p1) ? req.substring(p1+1, p2) : "/";
    if (url.startsWith("/save?")) {
      String q = url.substring(6);
      qval(q,"ssid").toCharArray(netcfg.ssid,  sizeof(netcfg.ssid));
      qval(q,"pass").toCharArray(netcfg.pass,  sizeof(netcfg.pass));
      qval(q,"host").toCharArray(netcfg.host,  sizeof(netcfg.host));
      netcfg.port = (uint16_t)qval(q,"port").toInt(); if(!netcfg.port) netcfg.port=1883;
      qval(q,"user").toCharArray(netcfg.user,  sizeof(netcfg.user));
      qval(q,"mpass").toCharArray(netcfg.mpass, sizeof(netcfg.mpass));
      String id=qval(q,"devid"); if(!id.length()) id=DEVID_DEFAULT;
      id.toCharArray(netcfg.devid, sizeof(netcfg.devid));
      netSave();
      portalSend(c, "<meta charset=utf-8><h2>Saved, rebooting...</h2>");
      c.flush(); delay(300); c.stop();
      oled.clearDisplay(); oled.setTextColor(SSD1306_WHITE); oled.setTextSize(2);
      oled.setCursor(0,24); oled.print("SAVED"); oled.display(); delay(900);
      NVIC_SystemReset();
    } else {
      c.print("HTTP/1.1 200 OK\r\nContent-Type:text/html;charset=utf-8\r\nConnection:close\r\n\r\n");
      c.print(portalPage());                   // dynamic page (scanned-network dropdown + 2.4GHz hint)
    }
    c.flush(); c.stop();
  }
}

// ===================== setup / loop =====================
void setup() {
#if DEBUG_NO_HW
  Serial.begin(115200);
#endif
  pinMode(ENC_A, INPUT_PULLUP); pinMode(ENC_B, INPUT_PULLUP); pinMode(ENC_SW, INPUT_PULLUP);
  pinMode(TACH_PIN, INPUT_PULLUP);          // single PST TACH, internal pull-up (no external resistor)

  pwmBegin();
  Wire.begin();
  oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  oled.clearDisplay(); oled.display();

  // Provisioning reset: hold the encoder button ~2s at power-on -> clear saved WiFi/MQTT, force the portal
  if (digitalRead(ENC_SW) == LOW) {
    uint32_t t0 = millis();
    while (digitalRead(ENC_SW) == LOW && millis() - t0 < 2000) {}
    if (millis() - t0 >= 2000) netClear();
  }
  ds18.begin();
  ds18.requestTemperatures();               // first conversion is blocking (~750ms): otherwise the first non-blocking read
  ds18.setWaitForConversion(false);         // returns the DS18B20 power-on value 85°C -> false forced 100% + alarm
  cfgLoad();

  attachInterrupt(digitalPinToInterrupt(TACH_PIN), isr0, FALLING);   // single PST TACH (D2 supports interrupts); before the portal, which also runs control

  // Not provisioned (first boot / just reset) -> portal: OLED shows QR, phone scans to join AP and configure, reboots when done
  if (!netLoad()) runPortal();

  attachInterrupt(digitalPinToInterrupt(ENC_A), encISR, FALLING);    // encoder CLK (D3 supports interrupts)

  WiFi.setHostname(netcfg.devid);           // hostname shown in router/DHCP = device ID (default rackfan01), instead of esp32s3-xxxx
  WiFi.setTimeout(WIFI_BEGIN_WAIT);         // WiFi.begin() blocks until connected or this timeout; keep it short --
  WiFi.begin(netcfg.ssid, netcfg.pass);     // the bridge keeps joining in the background and loop() polls the status
  tReconnect = millis();
  drawSplash("UP");
}

void loop() {
  uint32_t now = millis();

  encoderStep();                         // encoder (handled every iteration for responsiveness)

  if (now - tSample >= 1000) {           // sample + control at 1Hz
    tSample = now;
    sampleStep();
    controlStep();
#if DEBUG_NO_HW
    dbgPrint();
#endif
  }
  if (now - tDisplay >= 250) {           // display at 4Hz
    tDisplay = now;
    displayStep();
  }
  if (now - tMqtt >= 2000) {             // MQTT state at 0.5Hz
    tMqtt = now;
    if (mqtt.connected()) mqttPublishState();
  }
  cfgSaveStep();                         // deferred EEPROM write
  // Reconnect: check WiFi status directly (don't wait for the MQTT keepalive timeout). WiFi is re-begun every
  // WIFI_RETRY_MS so a join in progress isn't restarted; MQTT is retried every MQTT_RETRY_MS once WiFi is up.
  bool wifiUp = (WiFi.status() == WL_CONNECTED);
  if ((!wifiUp || !mqtt.connected()) && now - tReconnect >= (wifiUp ? MQTT_RETRY_MS : WIFI_RETRY_MS)) {
    tReconnect = now;
    if (!wifiUp) {
      WiFi.setHostname(netcfg.devid);        // keep the custom hostname on reconnect too
      WiFi.begin(netcfg.ssid, netcfg.pass);  // WiFi dropped -> reconnect; rejoins automatically once the network is back (temperature control unaffected throughout)
    } else {
      mqttConnect();                          // WiFi up, only MQTT down -> reconnect MQTT (and resend auto-discovery)
    }
  }
  if (mqtt.connected()) mqtt.poll();     // process subscribed messages
}
