"""Constants for the Salus iT500 integration."""
from datetime import timedelta

DOMAIN = "salusfy"

# Update interval for polling
# Set to 30 seconds as a balance between responsiveness and API load
# Salus API can be slow to update (10-30 seconds), but with immediate 
# refresh after changes, this interval is mainly for detecting external changes
UPDATE_INTERVAL = timedelta(seconds=30)

# Minimum time between API requests to avoid overwhelming the server
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)
