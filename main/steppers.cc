#include "arduino.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"


#include "FastAccelStepper.h"

static char* TAG = "steppers";

#define MAX_NUM_STEPPERS    2
#define NUM_STEPPERS        1
#define STEPS_PER_REV       (400 * 8) // Steppers are 0.9 degree 400 steps per rotation and using 8 microstepping.

#define STEP_DELAY          15

// Stepper config
#define DEG_PER_STEP 0.9
#define GEAR_RATIO 3
#define MICRO_STEPS 8

#define ROTATE_DEG_PER_STEP (DEG_PER_STEP / GEAR_RATIO / MICRO_STEPS)
#define TILT_DEG_PER_STEP (DEG_PER_STEP / GEAR_RATIO / MICRO_STEPS)
//PAN_RAD_PER_STEP = ROTATE_DEG_PER_STEP * M_PI / 180
//TILT_RAD_PER_STEP = TILT_DEG_PER_STEP * M_PI / 180

#define STEPS_PER_ROTATION ((360 / DEG_PER_STEP) * MICRO_STEPS * GEAR_RATIO)

#define ANGLE_TO_STEPS(angle) (angle / ROTATE_DEG_PER_STEP)
#define STEPS_TO_ANGLE(steps) (steps * ROTATE_DEG_PER_STEP)


static FastAccelStepperEngine engine = FastAccelStepperEngine();

typedef struct stepper_t {
    FastAccelStepper* stepper;
    int step_pin;
    int dir_pin; 
    int ena_pin;
} stepper_t;

static stepper_t rotate_stepper = { .stepper = NULL, .step_pin = 25, .dir_pin = 27, .ena_pin = 22 };
static stepper_t tilt_stepper = { .stepper = NULL, .step_pin = 15, .dir_pin = 14, .ena_pin = 5 };

extern "C" void steppers_init(void)
{
    engine.init();
    rotate_stepper.stepper = engine.stepperConnectToPin(rotate_stepper.step_pin);
    assert(rotate_stepper.stepper);
    tilt_stepper.stepper = engine.stepperConnectToPin(tilt_stepper.step_pin);
    assert(tilt_stepper.stepper);

    rotate_stepper.stepper->setDirectionPin(rotate_stepper.dir_pin);
    rotate_stepper.stepper->setEnablePin(rotate_stepper.ena_pin, false);
    rotate_stepper.stepper->setAutoEnable(false);
    rotate_stepper.stepper->enableOutputs();

    rotate_stepper.stepper->setSpeedInHz(STEPS_PER_ROTATION / 3);
    rotate_stepper.stepper->setAcceleration(300);

    tilt_stepper.stepper->setDirectionPin(tilt_stepper.dir_pin);
    tilt_stepper.stepper->setEnablePin(tilt_stepper.ena_pin, false);
    tilt_stepper.stepper->setAutoEnable(false);
    tilt_stepper.stepper->enableOutputs();

    tilt_stepper.stepper->setSpeedInHz(STEPS_PER_ROTATION / 3);
    tilt_stepper.stepper->setAcceleration(300);
}

extern "C" void steppers_go_to_azimuth_angle(int angle, bool blocking)
{
    if (blocking) {
        rotate_stepper.stepper->move(ANGLE_TO_STEPS(angle), false);
        tilt_stepper.stepper->move(ANGLE_TO_STEPS(angle), false);
        while (rotate_stepper.stepper->isRunning() || tilt_stepper.stepper->isRunning()) {
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    } else {
        rotate_stepper.stepper->move(ANGLE_TO_STEPS(angle), false);
        tilt_stepper.stepper->move(ANGLE_TO_STEPS(angle), false);
    }
}

extern "C" int32_t steppers_get_azimuth_angle(void)
{
    return STEPS_TO_ANGLE(rotate_stepper.stepper->getCurrentPosition());
}

extern "C" void steppers_go_to_tilt_angle(int angle, bool blocking) {
    tilt_stepper.stepper->move(ANGLE_TO_STEPS(angle), blocking);
}

extern "C" void steppers_set_enabled(bool enable) {
    if (enable) {
        tilt_stepper.stepper->enableOutputs();
        rotate_stepper.stepper->enableOutputs();
    } else {
        tilt_stepper.stepper->disableOutputs();
        rotate_stepper.stepper->disableOutputs();
    }
}
