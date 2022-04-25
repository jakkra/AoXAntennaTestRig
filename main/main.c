#include "Arduino.h"
#include "esp_log.h"

#include <esp_wifi.h>
#include <esp_netif.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "mdns.h"
#include "lwip/apps/netbiosns.h"
#include "driver/uart.h"

#include "wifi_manager.h"
#include "web_server.h"
#include "steppers.h"

const char* TAG = "main"; 

#define MAX_WS_CMD_LEN  100
#define UART_BUF_SIZE (1024)


typedef void(command_output_func(char* data));
typedef void(cmd_callback(uint8_t* data, uint32_t len, command_output_func* write_func));

typedef struct command_t {
    char*           cmd;
    uint32_t        cmd_len;
    cmd_callback*   callback;
} command_t;

static void handle_enable_cmd(uint8_t* data, uint32_t len, command_output_func* write_func);
static void handle_set_azimuth_cmd(uint8_t* data, uint32_t len, command_output_func* write_func);
static void handle_set_tilt_cmd(uint8_t* data, uint32_t len, command_output_func* write_func);
static void handle_get_angle_cmd(uint8_t* data, uint32_t len, command_output_func* write_func);
static void websocket_cmd_output(char* data);
static void uart_cmd_output(char* data);
static void parse_command(uint8_t* input, uint32_t len, command_output_func* write_func);


#define CREATE_CMD(cmd_str, handler) { .cmd = cmd_str, .cmd_len = sizeof(cmd_str) - 1, .callback = handler }

static command_t commands[] = {
    CREATE_CMD("ENABLE=", handle_enable_cmd),
    CREATE_CMD("AZIMUTH=", handle_set_azimuth_cmd),
    CREATE_CMD("TILT=", handle_set_tilt_cmd),
    CREATE_CMD("GET_ANGLE", handle_get_angle_cmd),
};

static bool websocket_connected = false;
static char command_buffer[MAX_WS_CMD_LEN];
char* ok_reply = "OK";
char* fail_reply = "ERROR";

/**
 * @brief this is an exemple of a callback that you can setup in your own app to get notified of wifi manager event.
 */
void cb_connection_ok(void *pvParameter){
    ip_event_got_ip_t* param = (ip_event_got_ip_t*)pvParameter;

    /* transform IP to human readable string */
    char str_ip[16];
    esp_ip4addr_ntoa(&param->ip_info.ip, str_ip, IP4ADDR_STRLEN_MAX);

    ESP_LOGI(TAG, "I have a connection and my IP is %s!", str_ip);
}

static void initialise_mdns(void)
{
    ESP_ERROR_CHECK(mdns_init());
    ESP_ERROR_CHECK(mdns_hostname_set("AoX-tester"));
    ESP_ERROR_CHECK(mdns_instance_name_set("AoX-tester-instance"));

    //structure with TXT records
    mdns_txt_item_t serviceTxtData[2] = {
        {"board","esp32"},
        {"path", "/"}
    };

    ESP_ERROR_CHECK(mdns_service_add("AoX-tester", "_http", "_tcp", 80, serviceTxtData, sizeof(serviceTxtData) / sizeof(serviceTxtData[0])));
    netbiosns_init();
    netbiosns_set_name("AoX-tester");
}


static void handle_websocket_event(websocket_event_t event, uint8_t* data, uint32_t len) {
    if (event == WEBSOCKET_EVENT_CONNECTED) {
        websocket_connected = true;
    } else if (event == WEBSOCKET_EVENT_DISCONNECTED) {
        websocket_connected = false;
    } else if (event == WEBSOCKET_EVENT_DATA) {
        memset(command_buffer, 0, MAX_WS_CMD_LEN);
        snprintf(command_buffer, MAX_WS_CMD_LEN - 1, "%s", data);
        parse_command(data, len, websocket_cmd_output);
    } else {
        assert(false); // Unhandled
    }
}

static void init_wifi(void)
{
    /* start the wifi manager */
    wifi_manager_start();

    /* register a callback as an example to how you can integrate your code with the wifi manager */
    wifi_manager_set_callback(WM_EVENT_STA_GOT_IP, &cb_connection_ok);
    webserver_init(&handle_websocket_event);
    webserver_start();
    //initialise_mdns();
}

static void handle_enable_cmd(uint8_t* data, uint32_t len, command_output_func* write_func) {
    char * end_ptr;
    int32_t enable;

    enable = strtol((char*)data, &end_ptr, 10);
    ESP_LOGW(TAG, "handle_enable_cmd %d", enable);
    steppers_set_enabled(enable);
    write_func(ok_reply);
}

static void handle_set_azimuth_cmd(uint8_t* data, uint32_t len, command_output_func* write_func)
{
    char* end_ptr;
    int32_t azimuth;

    azimuth = strtol((char*)data, &end_ptr, 10);

    ESP_LOGW(TAG, "handle_set_azimuth_cmd %d", azimuth);
    steppers_go_to_azimuth_angle(azimuth, true);

    write_func(ok_reply);
}

static void handle_set_tilt_cmd(uint8_t* data, uint32_t len, command_output_func* write_func)
{
    char* end_ptr;
    int32_t tilt;

    tilt = strtol((char*)data, &end_ptr, 10);
    
    ESP_LOGW(TAG, "handle_set_tilt_cmd %d", tilt);
    steppers_go_to_tilt_angle(tilt, true);

    write_func(ok_reply);
}

static void handle_get_angle_cmd(uint8_t* data, uint32_t len, command_output_func* write_func)
{
    char buf[100];
    memset(buf, 0, sizeof(buf));
    snprintf(buf, sizeof(buf), "%d\nOK", steppers_get_azimuth_angle());
    write_func(buf);
}

static void websocket_cmd_output(char* data)
{
    webserver_ws_send((uint8_t*)data, strlen(data));
}

static void uart_cmd_output(char* data)
{
    uart_write_bytes(UART_NUM_1, "\r\n", 2);
    uart_write_bytes(UART_NUM_1, (const char *)data, strlen(data));
    uart_write_bytes(UART_NUM_1, "\r\n", 2);
}

static void echo_task(void *arg)
{
    /* Configure parameters of an UART driver,
     * communication pins and install the driver */
    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    int intr_alloc_flags = 0;

#if CONFIG_UART_ISR_IN_IRAM
    intr_alloc_flags = ESP_INTR_FLAG_IRAM;
#endif

    ESP_ERROR_CHECK(uart_driver_install(UART_NUM_1, UART_BUF_SIZE * 2, 0, 0, NULL, intr_alloc_flags));
    ESP_ERROR_CHECK(uart_param_config(UART_NUM_1, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(UART_NUM_1, GPIO_NUM_12, GPIO_NUM_13, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

    // Configure a temporary buffer for the incoming data
    uint8_t *data = (uint8_t *) malloc(UART_BUF_SIZE);

    while (1) {
        // Read data from the UART
        int len = uart_read_bytes(UART_NUM_1, data, (UART_BUF_SIZE - 1), 20 / portTICK_PERIOD_MS);
        // Write data back to the UART
        uart_write_bytes(UART_NUM_1, (const char *) data, len);
        if (len) {
            data[len] = '\0';
            ESP_LOGI(TAG, "Recv str: %s", (char *) data);
        }
        parse_command(data, len, uart_cmd_output);
    }
}

static void parse_command(uint8_t* input, uint32_t len, command_output_func* write_func)
{
    for (int i = 0; i < (sizeof(commands) / sizeof(commands[0])); i++) {
        if (len >= commands[i].cmd_len && strncmp((char*)input, commands[i].cmd, commands[i].cmd_len) == 0) {
            commands[i].callback(input + commands[i].cmd_len, len - commands[i].cmd_len, write_func);
            break;
        }
    }
}

void app_main()
{
    initArduino();
    steppers_init();
    init_wifi();
    xTaskCreate(echo_task, "uart_rx_task", 2048, NULL, 10, NULL);
}
