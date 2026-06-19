import re

DAY_MAP = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}


def parse_service_days(value: object) -> list[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    days: list[str] = []
    for char in text:
        if char.isdigit():
            day_num = int(char)
            if day_num in DAY_MAP:
                days.append(DAY_MAP[day_num])
    return days


def parse_frequency_weeks(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text or text == "nan":
        return None
    if text == "1xn":
        return 1
    match = re.fullmatch(r"1x(\d+)n", text)
    if match:
        return int(match.group(1))
    return None
