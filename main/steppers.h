#pragma once
#ifdef __cplusplus
extern "C" {
#endif

void steppers_init(void);
void steppers_go_to_azimuth_angle(int angle, bool blocking);
void steppers_go_to_tilt_angle(int angle, bool blocking);
int32_t steppers_get_azimuth_angle(void);
void steppers_set_enabled(bool enable);
#ifdef __cplusplus
}
#endif
