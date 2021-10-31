"""Script for exporting a KUL public SAP schedule to an ICS calender file
Maxime Feyerick - 10/2021

If you are a TA for a course, there is no easy way to sync the course events to
your calendar. This script scrapes the public schedule which is available 
trough the 'onderwijsaanbod' site. It then saves the events to an ICS-file, 
which you can easily import into any calendar.

While this does not offer automatic syncing, it does solve other issues. Most
notably:
-  Not having to manually copy any event.
-  Avoiding human error in doing this.
"""

from typing import Any, List, Tuple

from arrow.arrow import Arrow
import bs4
from bs4.element import NavigableString
import requests                         # HTML requests
from bs4 import BeautifulSoup as Bsp    # HTML parser
import re                               # regex matching/parsing of strings
from ics import Calendar, Event         # creating ics exports
import arrow                            # For time stamps

# user defined
import calevent     # event data structure and conversion to ics formats

# Constants
# ----------

# URL of the semester-view schedule
URL_SCHEDULE=r'https://webwsp.aps.kuleuven.be/sap(bD1ubCZjPTIwMA==)/public/bsp/sap/z_mijnuurrstrs/uurrooster_sem_lijst.htm?sap-params=dGl0ZWxsaWpzdD1TY2hlZHVsZSZvdHlwZT1EJm9iamlkPTUwNDQ4MTYxJmJlZ2lud2VlazE9MjAyMTQ0JmVpbmRld2VlazE9MjAyMTQ4JmJlZ2lud2VlazI9Mjk5OTAxJmVpbmRld2VlazI9MjAwMDAxJnNjX29iamlkPTAwMDAwMDAwJnNlc3Npb25pZD0wMDUwNTY5NEM4QzMxRUVDOEVDQUIzOEFEOTRBMkU1QSZ0eXBlX2dyb2VwPQ%3d%3d'
#TODO: seems to be valid only for short time??

# Time range regex (both NL and EN compatible)
REGEXPR_TIME_RANGE = r"(\d+:\d+)\s*\w+\s*(\d+:\d+)"

# Destination ics filename
ICS_FILENAME = "./schedule.ics"

def main():
    page = requests.get(URL_SCHEDULE)
    parsed = Bsp(page.content, "html.parser")

    # structure of schedule is a bunch of one-row tables in a body > center element
    # extract all tables into a list (= all tables child of content element)
    # each event exists of one-row tables containing the information. 
    #   1) If different day, or first event: a week number row
    #   2) If different day, or first event: a row with the name of the day
    #   3) Event info, except for dates
    #   4) the dates
    #       * This table has a second row, containing a a line seperating 
    #         the events
    # The first two are optional, depending on the weekday of the preceding event

    center_el = parsed.body.center
    tables_lst = [el for el in center_el.children if el.name == 'table']
    # the order of in above list matches the order in the HTML source
    # the last element is the table with the building codes

    # store all found events here
    event_list : List[calevent.CalEvent] = []

    # start from first event in list of tables
    cur_ind = find_week_row(tables_lst) + 2
    stop_ind = len(tables_lst) - 1
 
    while cur_ind < stop_ind:
        if is_week_row(tables_lst[cur_ind]):
            cur_ind += 2
            
        event_list += process_event_rows(tables_lst, cur_ind)
        cur_ind += 2
    
    print_list(event_list)

    with open(ICS_FILENAME, 'w') as ics_file:
        ics_file.writelines(calevent.conv_to_ics_calendar(event_list))


def process_event_rows(table_lst: List[bs4.element.Tag], pos: int) -> List[calevent.CalEvent]:
    """Process a set of one-row table elements representing a course event.
    
    The table_lst is a list of HTML elements scrabed from the semester-view
    schedule. The event starts at pos."""

    event_detail_row = table_lst[pos].tr.find_all('td', recursive=False)
    event_dates_row    = table_lst[pos + 1].tr.find_all('td', recursive=False)

    time_range_str  = sanitize_string(event_detail_row[1].string)
    room_str        = sanitize_string(event_detail_row[2].string)
    course_code_str = sanitize_string(event_detail_row[3].a.string)
    course_descr_str= sanitize_string(event_detail_row[4].string)

    # date strings from date row
    #date_strings_it = filter(lambda s: s is not None,[el.string for el in event_dates_row])
    date_strings_it = [el.string for el in event_dates_row if el.string is not None]

    # parse time_range
    m = re.match(REGEXPR_TIME_RANGE, time_range_str)
    time_start_str  = m[1]
    time_stop_str   = m[2]

    return [ calevent.CalEvent(f"{course_descr_str} ({course_code_str})", room_str,
                construct_timestamp(date, time_start_str),
                construct_timestamp(date, time_stop_str) ) 
            for date in date_strings_it ]

    # print(f""" Event found
    #     Code:\t{course_code_str}
    #     Description:\t{course_descr_str}
    #     Room:\t{room_str}
    #     Dates:\t{", ".join(date_strings_it)}
    #    """)

# processing of parsed data
# --------------------------

def sanitize_string(str_in: str) -> str:
    # parsed HTML contains lots of \r\n apparently
    return str_in.strip()

def construct_timestamp(date: str, time: str) -> arrow.Arrow:
    """Convert scraped date and time into an arrow time stamp.
    date and time are in same format as in schedule."""

    # format of date: DD.MM 
    REGEXPR_Date = r"(\d+)\.(\d+)"
    m = re.match(REGEXPR_Date, date) 
    # We assume that the year is the current year. Otherwise need to scrape elsewhere on page
    date_str = f"{arrow.get().year}-{m[2].zfill(2)}-{m[1].zfill(2)}"
    return arrow.get( date_str + " " + time)

# Aux for finding event in the table list
# ----------------------------------------

def find_week_row(table_lst, pos: int = 0) -> int:
    """Find next row in table list containing 'week' text.
    Every new day in the semester view start with a week header"""

    for i in range(pos,len(table_lst)):
        if is_week_row(table_lst[i]):
            return i
    
    return None

def is_week_row(tb_el: bs4.element.Tag) -> bool:
    """Check if tb_el tag from semester view page is a week row"""

    if tb_el.name.lower() != 'table':
        return False
    
    if tb_el.tr is None:
        return False
    
    td_el = tb_el.tr.contents[0]
    if td_el.string == '\n':
        td_el =tb_el.tr.contents[1]
    if not isinstance(td_el, str) and td_el.font is not None:
        if sanitize_string(td_el.font.string) == 'Week':
            return True

# for debugging
# -----------------
def print_list(lst: List[Any]):
    print('[')
    for el in lst:
        print(str(el) + "\t,")
    print(']')

# this at the bottom
if __name__ == "__main__":
    main()
