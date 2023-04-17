# SUBSCRIBE:

# topic(s) to receive when a scan is overdue, for each checkpoint A, B, C, D
CHKS_OVERDUE = "sentry-platform/checkpoints/overdue-scan"

# topic to receive a scan to validate
SENTRY_SCAN_INFO = "sentry-platform/checkpoints/sentry-scan-info"

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

# topic to send the generated sentry circuit to the circuit handler
MONITOR_SENTRY_CIRCUIT = "sentry-platform/backend-server/sentry-circuit"
