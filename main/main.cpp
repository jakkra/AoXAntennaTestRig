#include "Arduino.h"
#include "Adafruit_MotorShield.h"

Adafruit_MotorShield AFMSbot(0x61); // Rightmost jumper closed
Adafruit_MotorShield AFMStop(0x60); // Default address, no jumpers

// On the top shield, connect two steppers, each with 200 steps
Adafruit_StepperMotor *myStepper2 = AFMStop.getStepper(200, 1);
Adafruit_StepperMotor *myStepper3 = AFMStop.getStepper(200, 2);

// On the bottom shield connect a stepper to port M3/M4 with 200 steps
Adafruit_StepperMotor *myStepper1 = AFMSbot.getStepper(200, 2);
// And a DC Motor to port M1
Adafruit_DCMotor *myMotor1 = AFMSbot.getMotor(1);

static void initSteppers(void) {
    AFMSbot.begin(); // Start the bottom shield
    AFMStop.begin(); // Start the top shield

    // turn on the DC motor
    myMotor1->setSpeed(200);
    myMotor1->run(RELEASE);
}

extern "C" void app_main()
{
    int i;
    initArduino();
    pinMode(4, OUTPUT);
    digitalWrite(4, HIGH);
    // Do your own thing
    initSteppers();

    while(1) {
        myMotor1->run(FORWARD);

        for (i=0; i<255; i++) {
            myMotor1->setSpeed(i);
            myStepper1->onestep(FORWARD, INTERLEAVE);
            myStepper2->onestep(BACKWARD, DOUBLE);
            myStepper3->onestep(FORWARD, MICROSTEP);
            delay(3);
        }

        for (i=255; i!=0; i--) {
            myMotor1->setSpeed(i);
            myStepper1->onestep(BACKWARD, INTERLEAVE);
            myStepper2->onestep(FORWARD, DOUBLE);
            myStepper3->onestep(BACKWARD, MICROSTEP);
            delay(3);
        }

        myMotor1->run(BACKWARD);

        for (i=0; i<255; i++) {
            myMotor1->setSpeed(i);
            myStepper1->onestep(FORWARD, DOUBLE);
            myStepper2->onestep(BACKWARD, INTERLEAVE);
            myStepper3->onestep(FORWARD, MICROSTEP);
            delay(3);
        }

        for (i=255; i!=0; i--) {
            myMotor1->setSpeed(i);
            myStepper1->onestep(BACKWARD, DOUBLE);
            myStepper2->onestep(FORWARD, INTERLEAVE);
            myStepper3->onestep(BACKWARD, MICROSTEP);
            delay(3);
        }
    }
}
