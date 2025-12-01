"""PyIt500 library for Salus iT500 API."""
from .auth import Auth
from .pyit500 import PyIt500
from .device import Device, SystemAttribute, SystemType
from .zone import Prefix, ZoneAttribute, ScheduleType, OnOffStatus, ActiveStatus
from .heatingzone import HeatingZone, ConsolidatedMode, AutoTempHoldMode
from .hotwaterzone import HotWaterZone, Mode as HotWaterMode, RunningMode as HotWaterRunningMode
from .devicelistitem import DeviceListItem
from .user import User

__all__ = [
    "Auth",
    "PyIt500",
    "Device",
    "SystemAttribute",
    "SystemType",
    "Prefix",
    "ZoneAttribute",
    "ScheduleType",
    "OnOffStatus",
    "ActiveStatus",
    "HeatingZone",
    "ConsolidatedMode",
    "AutoTempHoldMode",
    "HotWaterZone",
    "HotWaterMode",
    "HotWaterRunningMode",
    "DeviceListItem",
    "User",
]
