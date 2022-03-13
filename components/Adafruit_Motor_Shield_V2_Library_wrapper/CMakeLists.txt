idf_component_register(
    SRCS "Adafruit_Motor_Shield_V2_Library/Adafruit_MotorShield.cpp" "Adafruit_Motor_Shield_V2_Library/utility/Adafruit_MS_PWMServoDriver.cpp"
    INCLUDE_DIRS "Adafruit_Motor_Shield_V2_Library" Adafruit_Motor_Shield_V2_Library/utility
    REQUIRES "arduino Adafruit_BusIO")
