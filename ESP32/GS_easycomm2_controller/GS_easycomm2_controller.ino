/*
This script is currently setup to use an ESP32 with a GY-ADS1115 ADC with 16-bit resulution.
The ESP32 controls a YAESU G-5500 rotor - therefore the script is set up with specific control parameters
===== Communication =====
ESP32 <-> GY-ADS1115 is fascilitated via the I2C protocol using built-in I2C pins on the ESP32 (GPIO22 = SCL, GPIO21 = SDA)
ESP32 <-> Raspberry Pi (or other GS controller) is fascilitated via the built-in Serial Connection pins (TX and RX)

RPI <-> ESP32 uses the easycomm2 standard for communication (see https://jensd.dk/doc/yaesu/ for explanation).
The following commands are implemented:
Command           Meaning                     Parameters
-------           --------                    --------
AT                AutoTrack (AAU GS only)     satID - int of length 5 eg.32788 AKA AAUSAT II
SAT               Stop Auto Tracking (only works when AT has been called)

AZ                Azimuth                     number - 1 decimal place (XXX.X)
EL                Elevation                   number - 1 decimal place (YYY.Y)

ML                Move left                   
MR                Move right
MU                Move up
MD                Move down
SA                Stop azimuth
SE                Stop elevation

VE                Request version
AC                Automaticaly Calibrate min. and max. voltage values read from AZ and EL potentiometers on motors
PP                Print Position of antenna in AZ and EL
*/


#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Sgp4.h>
#include <time.h>
#include <Adafruit_ADS1X15.h>

String software_version = String("1.3.1");

// ========== variables and constants - AUTOTRACK (SGP4) related ==========

// WiFi related
const char* ssid = "EtWifi";      // Replace with your Wi-Fi credentials
const char* password = "EnKode1234";

// TLE API related
const char* baseURL = "https://tle.ivanstanojevic.me/api/tle/";
char satname[60];     // adjust size if not enough. Some satnames are longer than others
char tle_line1[130];
char tle_line2[130];

// GS and satellite related
Sgp4 sat;
double GS_lat = 57.013913;                          //set site (GS) latitude[°], longitude[°] and altitude[m]
double GS_lon = 9.987546;                           //AAU values
double GS_alt = 21; 

// NTP (Network Time Protocol) server for getting epochtime
const char* ntpServer = "pool.ntp.org";
// Variable to save current epoch time / unixtime
unsigned long unixtime;


// ========== variables and constants - Motor related ==========

// define motor control pins. When set HIGH, a transistor switches movement on.
#define AZ_CCW 0        //Transistor lets current flow between PIN4 to PIN8 on control wire
#define AZ_CW 16        //Transistor lets current flow between PIN2 to PIN8 on control wire

#define EL_UP 18        //Transistor lets current flow between PIN3 to PIN8 on control wire
#define EL_DOWN 19      //Transistor lets current flow between PIN5 to PIN8 on control wire

Adafruit_ADS1115 ads;   /* Use this for the 16-bit version */
#define AZ_ADC_PIN 0    //Connect PIN6 from motor control wire to pin A0 of ADC
#define EL_ADC_PIN 3    //Connect PIN1 from motor control wire to pin A3 of ADC

// minimum azimuth rotation
float AzMinDegs = 0.0;
// maximum azimuth rotation
float AzMaxDegs = 450.0;
// Lowest possiple voltage-reading from Azimuth potentiometer
float AzMinVolt = 0.01;    // all potentiometer max and min values where made manually with a multimeter
// Highest possiple voltage-reading from Azimuth potentiometer
float AzMaxVolt = 3.85;

float AzDegRange = AzMaxDegs - AzMinDegs;
float AzVoltRange = AzMaxVolt - AzMinVolt;

// minimum elevation rotation
float ElMinDegs = 0.0;
// maximum elevation rotation
float ElMaxDegs = 200.0;
// Lowest possiple voltage-reading from elevation potentiometer
float ElMinVolt = 0.26;
// Highest possiple voltage-reading from elevation potentiometer
float ElMaxVolt = 3.86;

float ElDegRange = ElMaxDegs - ElMinDegs;
float ElVoltRange = ElMaxVolt - ElMinVolt;

//allow some degrees of wiggleroom in both Az and El simultaneously
float threshold = 1.0;
//maximum angle in pos. and neg. direction where link budget is still secured. If antenna angle > abs(sat angle +- max_angle_for_radio)
//then shut of TX or RX until within acceptable range
float max_angle_for_radio = 13.9;

String OK_msg = String("OK");
String WAIT_msg = String("WAIT");
String ERROR_msg = String("ERROR");


// ========== ADC functions =========
/*
Function for setting gain of the ADC
*/
void set_ADC_gain() {
  // ads.setGain(GAIN_TWOTHIRDS);    // 2/3x gain +/- 6.144V  1 bit = 0.1875mV (default)
  ads.setGain(GAIN_ONE);          // 1x gain   +/- 4.096V  1 bit = 0.125mV
  // ads.setGain(GAIN_TWO);          // 2x gain   +/- 2.048V  1 bit = 0.0625mV
  if (!ads.begin())
  {
    Serial.println("Failed to initialize ADC. Reboot ESP32");
    while (1);
  }
}

/*
converts from voltage to degrees Az for comparison when rotating.
*/
float AzVoltageToDeg(float AzVoltage) {
  // determine Azimuth degrees based on adjusted voltage * degrees per Volt.
  float AzDeg = AzMinDegs + (AzVoltage - AzMinVolt) * (AzDegRange / AzVoltRange);
  if (AzDeg < AzMinDegs) {
    AzDeg = AzMinDegs;
  }
  else if (AzDeg > AzMaxDegs) {
    AzDeg = AzMaxDegs;
  }
  return AzDeg;
}

/*
converts from voltage to degrees El for comparison when rotating.
*/
float ElVoltageToDeg(float ElVoltage) {
  // determine Elevation degrees based on adjusted voltage * degrees per Volt.
  float ElDeg = ElMinDegs + (ElVoltage - ElMinVolt) * (ElDegRange / ElVoltRange);
  if (ElDeg < ElMinDegs) {
    ElDeg = ElMinDegs;
  }
  else if (ElDeg > ElMaxDegs) {
    ElDeg = ElMaxDegs;
  }
  return ElDeg;
}


// ========== General movement functions =========
/*
Function for moving LEFT - meaning making the azimuth motor rotate CCW (counterclockwise)
*/
void MovL() {
  digitalWrite(AZ_CW, LOW);     //Pull opposite movement low to keep motor safe
  delay(50);
  digitalWrite(AZ_CCW, HIGH);
}

/*
Function for moving RIGHT - meaning making the azimuth motor rotate CW (clockwise)
*/
void MovR() {
  digitalWrite(AZ_CCW, LOW);    //Pull opposite movement low to keep motor safe
  delay(50);
  digitalWrite(AZ_CW, HIGH);
}

/*
Function for moving UP - meaning making the elevation motor rotate UP
*/
void MovU() {
  digitalWrite(EL_DOWN, LOW);    //Pull opposite movement low to keep motor safe
  delay(50);
  digitalWrite(EL_UP, HIGH);
}

/*
Function for moving DOWN - meaning making the elevation motor rotate DOWN
*/
void MovD() {
  digitalWrite(EL_UP, LOW);    //Pull opposite movement low to keep motor safe
  delay(50);
  digitalWrite(EL_DOWN, HIGH);
}

/*
Function for stopping azimuth movement
*/
void SA() {
  digitalWrite(AZ_CCW, LOW);
  digitalWrite(AZ_CW, LOW);
}

/*
Function for stopping elevation movement
*/
void SE() {
  digitalWrite(EL_UP, LOW);
  digitalWrite(EL_DOWN, LOW);
}


// ========== MANUAL movement functions =========
/*
Function for moving to XXX.X degrees azimuth
*/
int AZ(String command) {

  String AZstr = command.substring(2, 7); // Get the decimal degree substring from the command
  float AZdegs = AZstr.toFloat();

  // check if command is within min and max degs rotation
  if (AZdegs < AzMinDegs || AZdegs > AzMaxDegs) {
    Serial.println(command + String("_") + ERROR_msg + String("_REQUESTED-MOVEMENT-OUT-OF-BOUNDS"));
    return -1;
  }
  bool moving = false;
  while (true) {

    // use ADC library to read digital value from conversion
    int16_t AzDigital = ads.readADC_SingleEnded(AZ_ADC_PIN);
    delay(2);
    // use ADC library to convert from digital to voltage value
    float AzVoltage = ads.computeVolts(AzDigital);

    // convert from Voltage to rotational degrees
    float AzAntenna = AzVoltageToDeg(AzVoltage);
    float AzDiff = AzAntenna - AZdegs;

    //check if antenna is locked on to sat in azimuth plane
    if (abs(AzDiff) <= threshold) {
      SA();   // stop AZ movement
      return 1;
    }

    if (!moving) {
      moving = true;
      // Moving in the Az plane
      if (AzDiff > threshold) {         // if AzDiff is larger than the threshold, antenna must move CCW as antenna AZ is larger than command AZ
        MovL();
      }
      else if (AzDiff < -threshold) {   // if AzDiff is smaller than the neg. threshold, antenna must move CW as antenna AZ is smaller than command AZ
        MovR();
      }
    }
  }
}

/*
Function for moving to YYY.Y degrees elevation
*/
int EL(String command) {

  String ELstr = command.substring(2, 7); // Get the decimal degree substring from the command
  float ELdegs = ELstr.toFloat();

  // check if command is within min and max degs rotation
  if (ELdegs < ElMinDegs || ELdegs > ElMaxDegs) {
    Serial.println(command + String("_") + ERROR_msg + String("_REQUESTED-MOVEMENT-OUT-OF-BOUNDS"));
    return -1;
  }
  bool moving = false;
  while (true) {
    // use ADC library to read digital value from conversion
    int16_t ElDigital = ads.readADC_SingleEnded(EL_ADC_PIN);
    delay(2);
    // use ADC library to convert from digital to voltage value
    float ElVoltage = ads.computeVolts(ElDigital);

    // convert from Voltage to rotational degrees
    float ElAntenna = ElVoltageToDeg(ElVoltage);
    float ElDiff = ElAntenna - ELdegs;

    //check if antenna is locked on to sat in elevation plane
    if (abs(ElDiff) <= threshold) {
      SE();     // stop EL movement
      return 1;
    }

    if (!moving) {
      moving = true;
      // Moving in the El plane
      if (ElDiff > threshold) {         // if ElDiff is larger than the threshold, antenna must move 'DOWN' as antenna EL is larger than command EL
        MovD();
      }
      else if (ElDiff < -threshold) {   // if ElDiff is smaller than the neg. threshold, antenna must move 'UP' as antenna EL is smaller than command EL
        MovU();
      }
    }
  }
}


// ========== AUTOTRACK movement functions =========
/*
Function for connecting the ESP32 to Wi-Fi using specified credentials from the top of the file
*/
void conn_WiFi() {
  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(2000);
    Serial.print(".");
  }
  Serial.println("Connected to WiFi");
}

/* 
Function for posting http GET request at TLE API for getting latest TLE data on satellite with ID = satID from RPI
*/
JsonObject fetchTLEData(int satID) {
  String url = baseURL + String(satID);
  HTTPClient http;
  JsonObject tleData;  // JsonObject to store TLE data

  http.begin(url.c_str());

  int httpCode = http.GET();

  if (httpCode > 0) {
    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      // Serial.println("TLE Data:");
      // Serial.println(payload);

      // Parse the JSON data into the JsonObject
      DynamicJsonDocument jsonDoc(1024); // Adjust the size as needed
      DeserializationError error = deserializeJson(jsonDoc, payload);

      if (!error) {
        // Extract the "line1" and "line2" values
        Serial.println("Extracting TLE data to Json object");
        tleData = jsonDoc.as<JsonObject>();
      } else {
        Serial.println("JSON parsing error: " + String(error.c_str()));
      }
    } else {
      Serial.println("Failed to fetch TLE data");
    }
  } else {
    Serial.println("HTTP request failed");
  }

  http.end();
  return tleData;
}

/*
Function that gets current epoch time
*/
unsigned long getTime() {
  time_t now;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    //Serial.println("Failed to obtain time");
    return(0);
  }
  time(&now);
  return now;
}

/*
Function for setting up all SGP4 and movement related dependencies for AUTOTRACK
*/
void AT_setup(String satID_str) {
  // Connect to Wi-Fi using ssid and password from the top of the file
  conn_WiFi();

  // Get TLE data using API call to https://tle.ivanstanojevic.me/api/tle/{satID}
  int satID = satID_str.toInt();  // converts to Int.
  JsonObject tleData = fetchTLEData(satID);
  const char* line1 = tleData["line1"];
  const char* line2 = tleData["line2"];
  const char* name = tleData["name"];

  // Copy string contents. Done because sat.init() will not take const char, but only char
  strcpy(satname, name);      // copy name into satname
  strcpy(tle_line1, line1);   // copy line1 into tle_line1
  strcpy(tle_line2, line2);   // copy line2 into tle_line2

  // ===== remove later =====
  Serial.println(satname);
  Serial.println(tle_line1);
  Serial.println(tle_line2);

  // Initialize satellite parameters and GS location (site)
  sat.site(GS_lat, GS_lon, GS_alt); //set site (GS) latitude[°], longitude[°] and altitude[m]
  sat.init(satname, tle_line1, tle_line2);

  // Setup the time library. GMT time offset = 0, daylight saving = 0 due to getting epoch being independent of these two.
  configTime(0, 0, ntpServer);
}

/*
Moves antenna to point at satelite
*/
void TrackSat () {
  bool Az_lock_on = false;  // whether or not antenna is locked on satellite (pointing at it within reason)
  bool El_lock_on = false;

  bool LOS = false;         // for telling RPI when to TX or RX

  // move antenna while it is not yet locked onto the target satellite
  while ((Az_lock_on == false) || (El_lock_on == false)) {

    // use ADC library to read digital value from conversion
    int16_t AzDigital = ads.readADC_SingleEnded(AZ_ADC_PIN);
    delay(2);
    int16_t ElDigital = ads.readADC_SingleEnded(EL_ADC_PIN);
    delay(2);
    // use ADC library to convert from digital to voltage value
    float AzVoltage = ads.computeVolts(AzDigital);
    float ElVoltage = ads.computeVolts(ElDigital);

    // convert from Voltage to rotational degrees
    float AzAntenna = AzVoltageToDeg(AzVoltage);
    float ElAntenna = ElVoltageToDeg(ElVoltage);

    // locate satellite relative to GS
    unixtime = getTime();
    sat.findsat(unixtime);
    delay(10);

    float AzDiff = AzAntenna - sat.satAz;
    float ElDiff;
    if (sat.satEl < 0) {
      ElDiff = ElAntenna;   // make EL go to 0.0 degs.
      Serial.println("SATELLITE-BELOW-HORIZON");
      delay(5000);    // wait 5 seconds and break out of loop.
      break;
    }
    else {
      ElDiff = ElAntenna - sat.satEl;
    }
    // Serial.println(String("sat.satAZ: ") + String(sat.satAz));
    // Serial.println(String("AzDiff: ") + String(AzDiff));
    // Serial.println(String("sat.satEl: ") + String(sat.satEl));
    // Serial.println(String("ElDiff: ") + String(ElDiff));
    //check if antenna is outside of its maximum range according to link budget. If so, tell RPI that it should pause its TX or RX. 
    if (LOS && (abs(AzDiff) > max_angle_for_radio || abs(ElDiff) > max_angle_for_radio)) {
      LOS = false;
      Serial.println("OK - LOCK_ON: " + String(LOS));
    }
    else if (!LOS) {
      LOS = true;
      Serial.println("OK - LOCK_ON: " + String(LOS));
    }

    //check if antenna is locked on to sat in azimuth plane
    if (abs(AzDiff) <= threshold) {
      SA();                   //making sure both Az pins are pulled low
      Az_lock_on = true;
    }
    else if (AzDiff > threshold) {
      MovL();                 // if AzDiff is larger than the threshold, antenna must move CCW as antenna AZ is larger than satAZ
      Az_lock_on = false;     // make sure that azimuth movement is still required if AzDiff is outside of the threshold range
    }
    else {
      MovR();                 // if AzDiff is smaller than the neg. threshold, antenna must move CW as antenna AZ is larger than satAZ
      Az_lock_on = false;     // make sure that azimuth movement is still required if AzDiff is outside of the threshold range
    }

    //check if antenna is locked on to sat in elevation plane
    if (abs(ElDiff) <= threshold) {
      SE();                   //making sure both El pins are pulled low
      El_lock_on = true;
    }
    else if (ElDiff > threshold) {      
      MovD();                 // if ElDiff is larger than the threshold, antenna must move 'DOWN' as antenna EL is larger than satEl
      El_lock_on = false;     // make sure that elevation movement is still required if ElDiff is outside of the threshold range
    }
    else {
      MovU();                 // if ElDiff is smaller than the neg. threshold, antenna must move 'UP' as antenna EL is larger than satEl
      El_lock_on = false;     // make sure that elevation movement is still required if ElDiff is outside of the threshold range
    }
  }
}

/*
Function to run when the ESP32 should automatically control the motors to point towards a satellite
*/
void AT(String satID_str) {
  // make the ESP32 ready for automatically tracking the given satellite
  AT_setup(satID_str);

  while (true) {
    // locate satellite and move to point antenna towards it.
    String stop_command = Serial.readStringUntil('\n');   // check if user tries to abort AT
    stop_command.trim();  // removes newline characters (\n) and whitespaces
    if (stop_command == String("SAT")) {
      Serial.println(String("SAT_") + OK_msg);
      break;
    }
    else {
      TrackSat();
    }
  }
}


// ========== Misc. functions =========

/*
Function for printing software version
*/
void VE(String command) {
  Serial.println(command + String("_") + String(software_version));
}


/*
Function for finding a stable value for the digital reading from the ADC
*/
int16_t CalDigReading(int ADC_PIN) {
  int16_t OldVal = 0.0;     // compare new to old val
  int16_t NewVal;
  float threshold = 33;     // +- value on digital read from 0 to 32768 (2^16 ADC ranging from - to + voltage). 33 is aprox. +- 0,1%
  int safety = 0;     // safety is incremented every time NewVal stays relatively close to OldVal. If that fails. reset safety to 0.

  while (true) {
    NewVal = ads.readADC_SingleEnded(ADC_PIN);
    // Serial.println("Reading: " + String(NewVal));
    // NewVal must be within +- threshold of OldVal for safety to be incremented
    if ((NewVal + threshold > OldVal) && (NewVal - threshold < OldVal)) {
      safety ++;
      // Serial.println("safety: " + String(safety));
    }
    else {
      OldVal = NewVal;    // ints are stored on the stack, so a deep copy is made.
      safety = 0;         // reset safety counter
      // Serial.println("OldVal: " + String(OldVal) + String(". NewVal: ") + String(NewVal));
    }
    if (safety >= 30) {
      return OldVal;      // Return OldVal as it has been approved 10 times by NewVal
    }
    delay(100);           // wait a bit to let motors move. Best case: safety is incremented 10 times in a row ~= 1 sec of waiting time
  }
}

/*
Function for automaticaly calibrating the min. and max. readings from the potentiometers on the AZ and EL motors
*/
void AC(float& AzMaxVolt, float& AzMinVolt, float& ElMaxVolt, float& ElMinVolt) {   // passing references to the global vars
  // Start moving in both planes
  MovR();
  MovU();
  // Read stable values for each of the voltages, starting with Max values and ending at 0.0 degs AZ and 0.0 degs EL
  AzMaxVolt = ads.computeVolts(CalDigReading(AZ_ADC_PIN));
  MovL();   // Go to lowest azimuth
  ElMaxVolt = ads.computeVolts(CalDigReading(EL_ADC_PIN));
  MovD();   // Go to lowest elevation
  AzMinVolt = ads.computeVolts(CalDigReading(AZ_ADC_PIN));
  ElMinVolt = ads.computeVolts(CalDigReading(EL_ADC_PIN));
  // All four global vars are now updated by reference
  SA();
  SE();
}

/*
Function for printing antenna position (AZ, EL)
*/
void PP() {    
  int16_t AzDigital = ads.readADC_SingleEnded(AZ_ADC_PIN);
  delay(2);
  float AzVoltage = ads.computeVolts(AzDigital);
  float AzAntenna = AzVoltageToDeg(AzVoltage);
  delay(2);

  int16_t ElDigital = ads.readADC_SingleEnded(EL_ADC_PIN);
  delay(2);
  float ElVoltage = ads.computeVolts(ElDigital);
  float ElAntenna = ElVoltageToDeg(ElVoltage);
  delay(2);

  Serial.println(String("{'azimuth': ") + String(AzAntenna) + String(", 'elevation': ") + String(ElAntenna) + String("}"));
}


void setup() {
  Serial.begin(115200);
  pinMode(AZ_CCW, OUTPUT);
  pinMode(AZ_CW, OUTPUT);
  pinMode(EL_UP, OUTPUT);
  pinMode(EL_DOWN, OUTPUT);
  SA();         // pull all movement pins LOW as some pins have a tendancy to float or start HIGH after reboot
  SE();
  delay(1000);
  
  // Init ADC and set its gain
  set_ADC_gain();

  Serial.println("ESP32-READY_OK");     // Tell RPI that ESP32 is ready
}

void loop() {

  int status = 0; // status for errorhandling from movement functions
  while (!Serial.available()) {
    // Wait for RPI command
  }

  String command = Serial.readStringUntil('\n');
  command.trim();  // removes newline characters (\n) and whitespaces
  Serial.println(command + "_" + WAIT_msg);  //Tell RPI that task is received

  if (command == String("ML")) {
    MovL();
  }
  else if (command == String("MR")) {
    MovR();
  }
  else if (command == String("MU")) {
    MovU();
  }
  else if (command == String("MD")) {
    MovD();
  }
  else if (command == String("SA")) {
    SA();
  }
  else if (command == String("SE")) {
    SE();
  }
  else if (command == String("PP")) {
    PP();
  }
  else if (command.substring(0, 2) == String("AZ")) {   // Check start of command and sep. from input XXX.X and YYY.Y for EL().
    status = AZ(command);
  }
  else if (command.substring(0, 2) == String("EL")) {
    status = EL(command);
  }
  else if (command == String("VE")) {
    VE(command);
  }
  else if (command == String("AC")) {
    AC(AzMaxVolt, AzMinVolt, ElMaxVolt, ElMinVolt);
    // Serial.println("AC_Done. Values are: ");
    // Serial.println("AzMaxVolt: " + String(AzMaxVolt));
    // Serial.println("ElMaxVolt: " + String(ElMaxVolt));
    // Serial.println("AzMinVolt: " + String(AzMinVolt));
    // Serial.println("ElMinVolt: " + String(ElMinVolt));
  }
  else if (command.substring(0,2) == String("AT")) {
    AT(command.substring(2,7));      // the satID which comes after AT is passed to the AT() function
  }
  else if (command == String("SAT")) {
    Serial.println(command + String("_") + ERROR_msg + String("_CALL-ATXXXXX-BEFORE-CALLING-SAT"));
  }
  else {
    Serial.println(command + String("_") + ERROR_msg + String("_COMMAND-NOT-FOUND"));
  }

  if (status == -1) {
    /* If a function has returned -1 it has already printed an error message. This if-statement makes sure that the ESP32 does not tell the RPI
    that the command was OK */
  }
  else {
    // Tell RPI when done with command
    Serial.println(command + String("_") + OK_msg);  // Tell RPI that task is completed
  }
}

