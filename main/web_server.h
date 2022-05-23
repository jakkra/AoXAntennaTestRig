#pragma once

#include "stdint.h"
#include "esp_err.h"

typedef enum websocket_event_t
{
    WEBSOCKET_EVENT_CONNECTED,
    WEBSOCKET_EVENT_DISCONNECTED,
    WEBSOCKET_EVENT_DATA
} websocket_event_t;

typedef void(websocket_callback(websocket_event_t status, uint8_t* data, uint32_t len));

void webserver_init(websocket_callback* ws_cb);
void webserver_start(void);
esp_err_t webserver_ws_send(uint8_t* payload, uint32_t len);

