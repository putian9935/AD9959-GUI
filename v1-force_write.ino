#include <SPI.h>

//****************Settings and definitions****************
SPISettings settings(2000000, MSBFIRST, SPI_MODE3);

// Digital output aliases
const int chip_select = 10;
const int io_update = 3;
const int master_reset = 4;

// DDS register aliases
byte channel_register = 0x00;
byte function_register = 0x01;
byte frequency_register = 0x04;
byte phase_register = 0x05;
byte amplitude_register = 0x06;

#define FREQUENCY_WORD_LENGTH 4
#define PHASE_WORD_LENGTH 2

// see page 33
#define SERIAL_IO_3_WIRE_MODE 1

void setup()
{

  //****************Initialization****************
  //Open serial and SPI
  Serial.begin(115200); // we can be faster, no necessarily 9600; as long as both ends match
  Serial.setTimeout(10);

  SPI.begin();
  SPI.beginTransaction(settings);

  // Set pin mode
  pinMode(chip_select, OUTPUT);  //Set mode of Arduino pin used for DDS chip select
  pinMode(io_update, OUTPUT);    //Set mode of Arduino pin used for IO update
  pinMode(master_reset, OUTPUT); //Set mode of Arduino pin used for master reset

  // Initialize pins
  digitalWrite(master_reset, HIGH); //Pulse high to reset all registers
  digitalWrite(master_reset, LOW);  //Keep this low for the rest of the sequence
  digitalWrite(io_update, LOW);     //Pulse high to update registers after all data is written
  digitalWrite(chip_select, HIGH);  //Set low during SPI data transfer to select chip

  Serial.println("Arduino setup finished!"); // handshake, typical of force write

  delay(500);
  char buffer[6];
  if(Serial.available()) {
    Serial.readBytes(buffer, 6);
    buffer[5] = '\0';
    if(!strcmp(buffer,"hello")) 
      Serial.println("Arduino ready!");
  }
}

//****************Write frequency tuning words****************
void write_DDS(byte *bytes)
{
  digitalWrite(chip_select, LOW); // Start SPI

  //Write function register
  SPI.transfer(function_register); // Initiate write to function register
  SPI.transfer(B11010000);         // Write to function register. This sets clock multiplier to 20
  SPI.transfer16(0);               // Pad remaining bits with zeros

  --bytes; // needed for concise increment
  //Write frequencies stored in EEPROM to DDS
  for (int ch = 0; ch < 4; ++ch)
  {
    //Set channel select register
    SPI.transfer(channel_register);                               //Initialize write to channel select register
    byte channel_byte = (16 << ch) | (SERIAL_IO_3_WIRE_MODE << 1); // Calculate byte for channel register
    SPI.transfer(channel_byte);                                   // Write channel register

    //Write to frequency tuning word register
    SPI.transfer(frequency_register); //Initialize write to frequency tuning word register
    for (int i = 0; i < FREQUENCY_WORD_LENGTH; ++i) 
      SPI.transfer(*++bytes); //Write EEPROM bytes to frequency tuning word register

    //Write phase offset word register
    SPI.transfer(phase_register); //Initialize write to phase offset word register
    for (int i = 0; i < PHASE_WORD_LENGTH; ++i) 
      SPI.transfer(*++bytes); //Write EEPROM bytes to phase offset word register
  }
  //Finish SPI communication
  digitalWrite(chip_select, HIGH); // Stop SPI

  // Below I do not understand
  digitalWrite(io_update, HIGH); // Transfer data to active registers
  digitalWrite(io_update, LOW);
}

void loop()
{
  /***
  * 4 channel x 6 bytes
  * High 4 bytes: frequency; low 2 bytes: phase
  */
  byte bytes[24];

  //Write frequency/phase values sent over serial to EEPROM
  if (Serial.available())
  {
    Serial.readBytes(bytes, 24);
    write_DDS(bytes);
    Serial.println("Just updated");
  }
}
