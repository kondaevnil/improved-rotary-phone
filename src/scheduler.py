import requests
from datetime import datetime, time, timedelta
from typing import List, Dict, Tuple, Optional, Any

API_URL = "https://ofc-test-01.tspb.su/test-task/"

TimeTuple = Tuple[time, time]
ScheduleData = Dict[str, Any]


class EmployeeSchedule:
    def __init__(self, url: str):
        self.schedule: Dict[str, ScheduleData] = self._fetch_and_process_data(url)

    def _parse_time(self, time_str: str) -> time:
        return datetime.strptime(time_str, "%H:%M").time()

    def _fetch_and_process_data(self, url: str) -> Dict[str, ScheduleData]:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Fetch or process error: {e}")
            raise

        processed_schedule: Dict[str, ScheduleData] = {}
        days_by_id = {day["id"]: day for day in data.get("days", [])}

        for day_id, day_info in days_by_id.items():
            date_str = day_info["date"]
            processed_schedule[date_str] = {
                "work_hours": (
                    self._parse_time(day_info["start"]),
                    self._parse_time(day_info["end"]),
                ),
                "busy_slots": [],
            }

        for slot in data.get("timeslots", []):
            day_id = slot["day_id"]
            if day_id in days_by_id:
                date_str = days_by_id[day_id]["date"]
                busy_slot = (
                    self._parse_time(slot["start"]),
                    self._parse_time(slot["end"]),
                )
                processed_schedule[date_str]["busy_slots"].append(busy_slot)

        for date_str in processed_schedule:
            processed_schedule[date_str]["busy_slots"].sort(key=lambda x: x[0])

        return processed_schedule

    def _get_day_schedule(self, date_str: str) -> Optional[ScheduleData]:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: '{date_str}'. Use 'YYYY-MM-DD'.")

        return self.schedule.get(date_str)

    def get_busy_slots(self, date_str: str) -> List[TimeTuple]:
        day_schedule = self._get_day_schedule(date_str)
        if not day_schedule:
            return []
        return day_schedule["busy_slots"]

    def get_free_slots(self, date_str: str) -> List[TimeTuple]:
        day_schedule = self._get_day_schedule(date_str)
        if not day_schedule:
            return []

        work_start, work_end = day_schedule["work_hours"]
        busy_slots = day_schedule["busy_slots"]
        free_slots = []

        current_time = work_start

        for busy_start, busy_end in busy_slots:
            if current_time < busy_start:
                free_slots.append((current_time, busy_start))
            current_time = max(current_time, busy_end)

        if current_time < work_end:
            free_slots.append((current_time, work_end))

        return free_slots

    def is_slot_available(self, date_str: str, start_str: str, end_str: str) -> bool:
        try:
            check_start = self._parse_time(start_str)
            check_end = self._parse_time(end_str)
        except ValueError:
            raise ValueError("Invalid time format. Use 'HH:MM'.")

        if check_start >= check_end:
            raise ValueError("Start time must be earlier than end time.")

        day_schedule = self._get_day_schedule(date_str)
        if not day_schedule:
            return False

        work_start, work_end = day_schedule["work_hours"]
        if not (work_start <= check_start and check_end <= work_end):
            return False

        for busy_start, busy_end in day_schedule["busy_slots"]:
            if max(check_start, busy_start) < min(check_end, busy_end):
                return False

        return True

    def find_available_slots_for_duration(
        self, duration_minutes: int
    ) -> Dict[str, List[TimeTuple]]:
        if duration_minutes <= 0:
            raise ValueError("Duration must be a positive number.")

        required_duration = timedelta(minutes=duration_minutes)
        suitable_slots = {}

        dummy_date = datetime(2000, 1, 1).date()

        for date_str in sorted(self.schedule.keys()):
            free_slots_on_day = self.get_free_slots(date_str)
            for free_start, free_end in free_slots_on_day:
                free_duration = datetime.combine(
                    dummy_date, free_end
                ) - datetime.combine(dummy_date, free_start)
                if free_duration >= required_duration:
                    if date_str not in suitable_slots:
                        suitable_slots[date_str] = []
                    suitable_slots[date_str].append((free_start, free_end))

        return suitable_slots


if __name__ == "__main__":
    try:
        print("Generating schedule manager...")
        schedule_manager = EmployeeSchedule(API_URL)
        print("Schedule successfully loaded.\n")

        test_date = "2025-02-18"
        busy = schedule_manager.get_busy_slots(test_date)
        print(f"1. Busy slots on {test_date}:")
        if busy:
            for start, end in busy:
                print(f"   - from {start.strftime('%H:%M')} to {end.strftime('%H:%M')}")
        else:
            print("   - No busy slots.")
        print("-" * 30)

        free = schedule_manager.get_free_slots(test_date)
        print(f"2. Free slots on {test_date}:")
        if free:
            for start, end in free:
                print(f"   - from {start.strftime('%H:%M')} to {end.strftime('%H:%M')}")
        else:
            print("   - No free slots.")
        print("-" * 30)

        is_avail = schedule_manager.is_slot_available(test_date, "10:00", "11:00")
        print(
            f"3. Is slot {test_date} from 10:00 to 11:00 available? -> {'Yes' if is_avail else 'No'}"
        )

        is_avail_busy = schedule_manager.is_slot_available(test_date, "11:30", "12:30")
        print(
            f"   Is slot {test_date} from 11:30 to 12:30 available? -> {'Yes' if is_avail_busy else 'No'}"
        )
        print("-" * 30)

        duration = 90
        available_for_duration = schedule_manager.find_available_slots_for_duration(
            duration
        )
        print(f"4. Finding free slots for a request lasting {duration} minutes:")
        if available_for_duration:
            for date, slots in available_for_duration.items():
                print(f"   Date: {date}")
                for start, end in slots:
                    print(
                        f"     - Available slot from {start.strftime('%H:%M')} to {end.strftime('%H:%M')}"
                    )
        else:
            print(f"   - No suitable slots found for {duration} minutes.")
        print("-" * 30)

        try:
            schedule_manager.get_free_slots("2025-01-01")
            schedule_manager.get_free_slots("invalid-date")
        except ValueError as e:
            print(f"Example error handling: {e}")

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"\nFailed to execute the program due to an error: {e}")
