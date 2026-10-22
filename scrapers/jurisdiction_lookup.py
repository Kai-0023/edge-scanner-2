"""One-time state lookup for an optional device-location suggestion.

The dashboard never persists the submitted coordinates. The public U.S. Census
geocoder receives an approximate coordinate only after a user requests a state
suggestion in their browser.
"""

from collections.abc import Mapping
from typing import Any

import httpx


_CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"

# FIPS state identifiers returned by the Census Geocoder, mapped to the same
# postal abbreviations used by the dashboard's jurisdiction selector.
_STATE_CODES: dict[str, tuple[str, str]] = {
    "01": ("AL", "Alabama"), "02": ("AK", "Alaska"), "04": ("AZ", "Arizona"),
    "05": ("AR", "Arkansas"), "06": ("CA", "California"), "08": ("CO", "Colorado"),
    "09": ("CT", "Connecticut"), "10": ("DE", "Delaware"), "11": ("DC", "District of Columbia"),
    "12": ("FL", "Florida"), "13": ("GA", "Georgia"), "15": ("HI", "Hawaii"),
    "16": ("ID", "Idaho"), "17": ("IL", "Illinois"), "18": ("IN", "Indiana"),
    "19": ("IA", "Iowa"), "20": ("KS", "Kansas"), "21": ("KY", "Kentucky"),
    "22": ("LA", "Louisiana"), "23": ("ME", "Maine"), "24": ("MD", "Maryland"),
    "25": ("MA", "Massachusetts"), "26": ("MI", "Michigan"), "27": ("MN", "Minnesota"),
    "28": ("MS", "Mississippi"), "29": ("MO", "Missouri"), "30": ("MT", "Montana"),
    "31": ("NE", "Nebraska"), "32": ("NV", "Nevada"), "33": ("NH", "New Hampshire"),
    "34": ("NJ", "New Jersey"), "35": ("NM", "New Mexico"), "36": ("NY", "New York"),
    "37": ("NC", "North Carolina"), "38": ("ND", "North Dakota"), "39": ("OH", "Ohio"),
    "40": ("OK", "Oklahoma"), "41": ("OR", "Oregon"), "42": ("PA", "Pennsylvania"),
    "44": ("RI", "Rhode Island"), "45": ("SC", "South Carolina"), "46": ("SD", "South Dakota"),
    "47": ("TN", "Tennessee"), "48": ("TX", "Texas"), "49": ("UT", "Utah"),
    "50": ("VT", "Vermont"), "51": ("VA", "Virginia"), "53": ("WA", "Washington"),
    "54": ("WV", "West Virginia"), "55": ("WI", "Wisconsin"), "56": ("WY", "Wyoming"),
}


class DeviceJurisdictionUnavailable(RuntimeError):
    """Raised when a device-location state cannot be determined safely."""


def state_from_census_response(payload: Mapping[str, Any]) -> dict[str, str] | None:
    """Extract a selectable state from a Census geocoder response."""

    result = payload.get("result")
    if not isinstance(result, Mapping):
        return None
    geographies = result.get("geographies")
    if not isinstance(geographies, Mapping):
        return None
    states = geographies.get("States")
    if not isinstance(states, list):
        return None

    for state in states:
        if not isinstance(state, Mapping):
            continue
        fips = str(state.get("STATE", "")).zfill(2)
        selected = _STATE_CODES.get(fips)
        if selected:
            code, name = selected
            return {"code": code, "name": name}
    return None


async def lookup_device_jurisdiction(latitude: float, longitude: float) -> dict[str, str]:
    """Look up a U.S. state without retaining the location in the application."""

    params = {
        # State suggestion does not need full device precision. It is not a
        # location-verification service and users can always choose manually.
        "x": f"{longitude:.3f}",
        "y": f"{latitude:.3f}",
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(_CENSUS_GEOCODER_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DeviceJurisdictionUnavailable("The state lookup service is unavailable.") from exc

    state = state_from_census_response(response.json())
    if not state:
        raise DeviceJurisdictionUnavailable(
            "A U.S. state could not be determined from this device location. Choose a state manually."
        )
    return state
