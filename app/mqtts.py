# SUBSCRIBE:

# topic(s) to receive when a scan is overdue, for each checkpoint A, B, C, D
CHKS_OVERDUE = "sentry-platform/checkpoints/+/overdue-scan"

# topic to receive a scan to validate
SENTRY_SCAN = "sentry-platform/checkpoints/sentry-scan-info"

# topic to receive connected message from circuit handler
CONNECTED = "sentry-platform/+/connected"

# topic to receive alerts from the circuit handler
ALERTS = "sentry-platform/circuit-handler/alerts"

# topic to receive message if the shift is done
DONE = "sentry-platform/circuit-handler/circuit-complete"

# PUBLISH

# topic to publish the shift started/over message
SHIFT_ON_OFF = "sentry-platform/backend-server/shift-status"

# topic to publish alarm/no alarm
ALARM = "sentry-platform/backend-server/alarm"

# CONNECTION FLAGS

# web app connected to broker
APP_CONNECTED = False
# circuit handler connected to broker
HANDLER_CONNECTED = False
# checkpoint A connected to broker
CHK_A_CONNECTED = False
# checkpoint B connected to broker
CHK_B_CONNECTED = False
# checkpoint C connected to broker
CHK_C_CONNECTED = False
# checkpoint D connected to broker
CHK_D_CONNECTED = False
