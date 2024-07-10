"""Services registry for APM CrewConnect."""

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
import homeassistant.helpers.config_validation as cv
from homeassistant.util.json import JsonObjectType

from .const import (
    ACFT_TYPES,
    ATTR_ACFT_TYPE,
    ATTR_END_DATE,
    ATTR_ROLE,
    ATTR_START_DATE,
    DOMAIN,
    ROLES,
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Handle registering APM services."""

    data = hass.data[DOMAIN]

    def find_unstaffed_flights(service: ServiceCall) -> JsonObjectType:
        """Find flights with missing crew members."""
        if ATTR_END_DATE in service.data:
            flights = data.apm.get_flight_schedule(
                service.data[ATTR_START_DATE], service.data[ATTR_END_DATE]
            )
        else:
            flights = data.apm.get_flight_schedule(service.data[ATTR_START_DATE])

        flights_with_missing_crew_members = [
            flight
            for flight in flights
            if (
                service.data.get(ATTR_ACFT_TYPE) is None
                or flight.aircraft_type == service.data.get(ATTR_ACFT_TYPE)
            )
            and (
                (
                    service.data.get(ATTR_ROLE) is None
                    and flight.is_missing_crew_members()
                )
                or flight.is_missing_crew_members(service.data.get(ATTR_ROLE))
            )
        ]

        flights_with_missing_crew_members.sort(
            key=lambda flight: flight.departure_time.isoformat()
        )

        return {
            "count": len(flights_with_missing_crew_members),
            "data": flights_with_missing_crew_members,
        }

    hass.services.async_register(
        DOMAIN,
        "find_unstaffed_flights",
        find_unstaffed_flights,
        schema=vol.Schema(
            {
                vol.Required(ATTR_START_DATE): cv.date,
                vol.Optional(ATTR_END_DATE): cv.date,
                vol.Optional(ATTR_ACFT_TYPE): vol.In(ACFT_TYPES),
                vol.Optional(ATTR_ROLE): vol.In(ROLES),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
