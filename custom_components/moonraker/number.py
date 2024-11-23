"""Number platform for Moonraker integration."""
import logging
from dataclasses import dataclass

from homeassistant.components.number import (NumberEntity,
                                             NumberEntityDescription,
                                             NumberMode)
from homeassistant.core import callback

from .const import DOMAIN, METHODS, OBJ
from .entity import BaseMoonrakerEntity


@dataclass
class MoonrakerNumberSensorDescription(NumberEntityDescription):
    """Class describing Mookraker binary_sensor entities."""

    sensor_name: str | None = None
    icon: str | None = None
    subscriptions: list | None = None


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    await async_setup_output_pin(coordinator, entry, async_add_devices)
    await async_setup_temperature_sensors(coordinator, entry, async_add_devices)


async def async_setup_output_pin(coordinator, entry, async_add_entities):
    """Set optional binary sensor platform."""

    object_list = await coordinator.async_fetch_data(METHODS.PRINTER_OBJECTS_LIST)

    query_obj = {OBJ: {"configfile": ["settings"]}}
    settings = await coordinator.async_fetch_data(
        METHODS.PRINTER_OBJECTS_QUERY, query_obj, quiet=True
    )

    numbers = []
    for obj in object_list["objects"]:
        if "output_pin" not in obj:
            continue

        if not settings["status"]["configfile"]["settings"][obj.lower()]["pwm"]:
            continue

        desc = MoonrakerNumberSensorDescription(
            key=obj,
            sensor_name=obj,
            name=obj.replace("_", " ").title(),
            icon="mdi:switch",
            subscriptions=[(obj, "value")],
        )
        numbers.append(desc)

    coordinator.load_sensor_data(numbers)
    await coordinator.async_refresh()
    async_add_entities(
        [MoonrakerPWMOutputPin(coordinator, entry, desc) for desc in numbers]
    )

async def async_setup_temperature_sensors(coordinator, entry, async_add_entities):
    """Set up temperature sensors for bed and nozzle temperatures."""
    
    # Fetch the list of objects from the printer
    object_list = await coordinator.async_fetch_data(METHODS.PRINTER_OBJECTS_LIST)

    # Query for specific temperature data
    query_obj = {"heater_bed": ["temperature"], "extruder": ["temperature"]}
    temperature_data = await coordinator.async_fetch_data(
        METHODS.PRINTER_OBJECTS_QUERY, query_obj, quiet=True
    )

    # Prepare lists for bed and nozzle temperature descriptions
    bed_description = MoonrakerNumberSensorDescription(
        key="heater_bed",
        sensor_name="heater_bed",
        name="Heated Bed Temperature",
        icon="mdi:thermometer",
        subscriptions=[("heater_bed", "temperature")],
    )
    nozzle_description = MoonrakerNumberSensorDescription(
        key="extruder",
        sensor_name="extruder",
        name="Extruder Nozzle Temperature",
        icon="mdi:thermometer",
        subscriptions=[("extruder", "temperature")],
    )

    # Initialize sensor entities based on the fetched object list
    temperature_sensors = []
    if "heater_bed" in object_list["objects"]:
        temperature_sensors.append(MoonrakerBedTemperature(coordinator, entry, bed_description))
    if "extruder" in object_list["objects"]:
        temperature_sensors.append(MoonrakerNozzleTemperature(coordinator, entry, nozzle_description))

    # Add the sensor entities to Home Assistant
    async_add_entities(temperature_sensors)
    
    # Load sensor data into the coordinator
    coordinator.load_sensor_data([bed_description, nozzle_description])
    await coordinator.async_refresh()

_LOGGER = logging.getLogger(__name__)


class MoonrakerPWMOutputPin(BaseMoonrakerEntity, NumberEntity):
    """Moonraker PWM output pin class."""

    def __init__(
        self,
        coordinator,
        entry,
        description,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, entry)
        self.pin = description.sensor_name.replace("output_pin ", "")
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_value = (
            coordinator.data["status"][description.sensor_name]["value"] * 100
        )
        self.entity_description = description
        self.sensor_name = description.sensor_name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.name
        self._attr_has_entity_name = True
        self._attr_icon = description.icon

    async def async_set_native_value(self, value: float) -> None:
        """Set native Value."""
        await self.coordinator.async_send_data(
            METHODS.PRINTER_GCODE_SCRIPT,
            {"script": f"SET_PIN PIN={self.pin} VALUE={round(value/100, 2)}"},
        )
        self._attr_native_value = value
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = (
            self.coordinator.data["status"][self.sensor_name]["value"] * 100
        )
        self.async_write_ha_state()

class MoonrakerBedTemperature(BaseMoonrakerEntity, NumberEntity):
    """Moonraker set bed temperatures class."""

    def __init__(
        self,
        coordinator,
        entry,
        description,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, entry)
        self.pin = description.sensor_name.replace("output_pin ", "")
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_value = (
            coordinator.data["status"][description.sensor_name]["value"] * 100
        )
        self.entity_description = description
        self.sensor_name = description.sensor_name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.name
        self._attr_has_entity_name = True
        self._attr_icon = description.icon

    async def async_set_bed_temp(self, temp: float) -> None:
        """Set native Value."""
        await self.coordinator.async_send_data(
            METHODS.PRINTER_GCODE_SCRIPT,
            {"script": f"M140 S{temp}"},
        )
        self._attr_native_value = temp
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = (
            self.coordinator.data["status"][self.sensor_name]["value"] * 100
        )
        self.async_write_ha_state()

class MoonrakerNozzleTemperature(BaseMoonrakerEntity, NumberEntity):
    """Moonraker set nozzle temperatures class."""

    def __init__(
        self,
        coordinator,
        entry,
        description,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, entry)
        self.pin = description.sensor_name.replace("output_pin ", "")
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_value = (
            coordinator.data["status"][description.sensor_name]["value"] * 100
        )
        self.entity_description = description
        self.sensor_name = description.sensor_name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.name
        self._attr_has_entity_name = True
        self._attr_icon = description.icon

    async def async_set_nozzle_temp(self, temp: float) -> None:
        """Set native Value."""
        await self.coordinator.async_send_data(
            METHODS.PRINTER_GCODE_SCRIPT,
            {"script": f"M104 S{temp}"},
        )
        self._attr_native_value = temp
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = (
            self.coordinator.data["status"][self.sensor_name]["value"] * 100
        )
        self.async_write_ha_state()