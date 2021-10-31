from typing import List
import arrow
import ics
from dataclasses import dataclass

@dataclass
class CalEvent:
    """Struct containing info of a single calender event"""
    description: str
    location: str
    dt_start: arrow.Arrow
    dt_stop: arrow.Arrow

    def __str__(self) -> str:
        return f"""Event
        Description:\t{self.description}
        Location:\t{self.location}
        Start:\t{self.dt_start}
        End:\t{self.dt_stop}"""


def conv_to_ics_event(event: CalEvent) -> ics.Event:
    """Convert CalEvent to ics Event"""

    e = ics.Event()
    e.name = event.description
    e.begin = event.dt_start
    e.end   = event.dt_stop
    e.location = event.location
    
    return e

def conv_to_ics_calendar(e_lst: List[CalEvent]) -> ics.Calendar:
    """Convert a list of CalEvent to an ics Calendar"""
    c = ics.Calendar()
    for e in e_lst:
        c.events.add(conv_to_ics_event(e))
    return c

