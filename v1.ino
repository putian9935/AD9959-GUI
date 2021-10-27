#include <EEPROM.h>
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

void setup() {

//****************Initialization****************
//Open serial and SPI
  Serial.begin(115200);
  SPI.begin();
  SPI.beginTransaction(settings);
    
// Set pin mode
  pinMode(chip_select, OUTPUT); //Set mode of Arduino pin used for DDS chip select
  pinMode(io_update,OUTPUT); //Set mode of Arduino pin used for IO update
  pinMode(master_reset,OUTPUT); //Set mode of Arduino pin used for master reset

// Initialize pins
  digitalWrite(master_reset,HIGH); //Pulse high to reset all registers
  digitalWrite(master_reset,LOW); //Keep this low for the rest of the sequence
  digitalWrite(io_update,LOW); //Pulse high to update registers after all data is written
  digitalWrite(chip_select, HIGH); //Set low during SPI data transfer to select chip
}

//****************Write frequency tuning words****************
void write_DDS(){
  digitalWrite(chip_select, LOW); //Start SPI

  //Write function register
  SPI.transfer(function_register); //Initiate write to function register
  SPI.transfer(B11010000); //Write to function register. This sets clock multiplier to 20
  SPI.transfer16(0); //Pad remaining bits with zeros

  //Write frequencies stored in EEPROM to DDS
  for(byte ch=0; ch<=3; ch++){
    //Set channel select register
    SPI.transfer(channel_register); //Initialize write to channel select register
    byte channel_byte = round(pow(2,4+ch)+2); //Calculate byte for channel register
    SPI.transfer(channel_byte); //Write channel register
  
    //Write to frequency tuning word register
    SPI.transfer(frequency_register); //Initialize write to frequency tuning word register
    SPI.transfer(EEPROM.read(4*ch)); //Write EEPROM bytes to frequency tuning word register
    SPI.transfer(EEPROM.read(4*ch+1));
    SPI.transfer(EEPROM.read(4*ch+2));
    SPI.transfer(EEPROM.read(4*ch+3));

    //Write phase offset word register
    SPI.transfer(phase_register); //Initialize write to phase offset word register
    SPI.transfer(EEPROM.read(2*ch+16)); //Write EEPROM bytes to phase offset word register
    SPI.transfer(EEPROM.read(2*ch+17));
  }
  //Finish SPI communication
  digitalWrite(chip_select, HIGH); //Stop SPI
  digitalWrite(io_update,HIGH); //Transfer data to active registers
  digitalWrite(io_update,LOW);
}

//****************Read frequency tuning word****************
unsigned long read_frequency_register(byte ch){
  digitalWrite(chip_select, LOW); //Start SPI
  
  //Set channel select register
  SPI.transfer(channel_register); //Initialize write to channel select register
  byte channel_byte = round(pow(2,4+ch)+2); //Calculate byte for channel register
  SPI.transfer(channel_byte); //Write channel register

  //Read from frequency tuning word register
  SPI.transfer(B10000000 | frequency_register); //Initialize read from channel select register
  unsigned long n1 = SPI.transfer16(0); //Read first 16 bits of frequency tuning word
  unsigned long n2 = SPI.transfer16(0); //Read second 16 bits of frequency tuning word
  
  //Finish SPI communication
  digitalWrite(chip_select, HIGH);

  //Return frequency tuning word
  return (n1 << 16) | n2;

}

//****************Write EEPROM****************
void write_EEPROM(byte ch, float f, float phi){
  
  //Create frequency tuning word
  float fclk = 500000; //20 times 25000 kHz clock
  unsigned long FTW = round(4294967296.0*f/fclk); //Note: Larger variable types don't improve float math here

  //Store frequencies in EEPROM
  byte mask = B11111111;
  if(f >= 0 && f <= 250000){ //Only update if frequency is between 0 and 250 MHz
    EEPROM.write(4*ch,(FTW >> 24) & mask);
    EEPROM.write(4*ch+1,(FTW >> 16) & mask);
    EEPROM.write(4*ch+2,(FTW >> 8) & mask);
    EEPROM.write(4*ch+3,FTW & mask);
  }
  
  //Create phase offset word
  unsigned int POW = round(16384*phi/360);

  //Store phase in EEPROM
  if(phi >=0 && phi <= 360){ //Only update if phase is between 0 and 360 deg
    EEPROM.write(2*ch+16,(POW >> 8) & mask);
    EEPROM.write(2*ch+17,POW & mask);
  }
}

//****************Read frequency EEPROM****************
unsigned long read_EEPROM(byte ch){
  unsigned long n1 = EEPROM.read(4*ch); //Needs to be long for bit shifting
  unsigned long n2 = EEPROM.read(4*ch+1);
  unsigned long n3 = EEPROM.read(4*ch+2);
  unsigned long n4 = EEPROM.read(4*ch+3);

  //Return frequency tuning word stored in EEPROM
  return (n1 << 24) | (n2 << 16) | (n3 << 8) | n4;
}


//****************Read phase EEPROM****************
unsigned long read_EEPROM_phase(byte ch){
  unsigned int n1 = EEPROM.read(2*ch+16); //Needs to be long for bit shifting
  unsigned int n2 = EEPROM.read(2*ch+17);

  //Return phase tuning word stored in EEPROM
  return (n1 << 8) | n2;
}

void loop() {

  //Write frequency/phase values sent over serial to EEPROM
  if(Serial.available() > 0){
  
    //Wait for all serial data to be sent    
    int counter = 0;
    while(Serial.available() < 40){
      delay(1);
      counter++;
      // Break if too little data is sent
      if(counter > 1000){
        break;
      }
    }
    //Clear serial buffer if too much or too little serial data is sent
    if(Serial.available() != 40){
      while(Serial.available() > 0){
        char x = Serial.read();
      }
    }
    //Write EEPROM
    for(byte ch=0; ch<=3; ch++){
  
      //Read frequency (in kHz)
      float frequency = 0;
      for(int k=5; k>=0; k--){
        frequency += (Serial.read() - '0')*pow(10,k);
      }
  
      //Read phase in degrees
      float phase = 0;
      for(int k=2; k>=-1; k--){
        phase += (Serial.read() - '0')*pow(10,k);
      }
      
      //Update EEPROM
      write_EEPROM(ch,frequency,phase);
    }
  }

  //Check if DDS needs a write and then do so (if need be)
  boolean DDS_on = true;
  for(byte ch=0; ch<=3; ch++){
    if(read_frequency_register(ch) != read_EEPROM(ch)){
      DDS_on = false;
    }
  }
  if(DDS_on == false){
    write_DDS();
  }

  delay(1000);

}
