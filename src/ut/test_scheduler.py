# test_scheduler_pytest.py

import pytest
from datetime import time

from scheduler import EmployeeSchedule, API_URL

MOCK_API_DATA = {
    "days": [
        {"id": 1, "date": "2024-10-10", "start": "09:00", "end": "18:00"},
        {"id": 2, "date": "2024-10-11", "start": "08:00", "end": "17:00"},
    ],
    "timeslots": [
        {"id": 1, "day_id": 1, "start": "11:00", "end": "12:00"},
        {"id": 2, "day_id": 1, "start": "15:00", "end": "15:30"},
        {"id": 3, "day_id": 2, "start": "09:30", "end": "16:00"},
    ],
}


@pytest.fixture()
def scheduler_instance(mocker):
    mock_get = mocker.patch("scheduler.requests.get")

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = MOCK_API_DATA

    return EmployeeSchedule(API_URL)


def test_get_busy_slots(scheduler_instance):
    date = "2024-10-10"
    expected = [(time(11, 0), time(12, 0)), (time(15, 0), time(15, 30))]
    assert scheduler_instance.get_busy_slots(date) == expected


def test_get_busy_slots_non_working_day(scheduler_instance):
    date = "2024-10-12"
    assert scheduler_instance.get_busy_slots(date) == []


def test_get_free_slots(scheduler_instance):
    date = "2024-10-10"
    expected = [
        (time(9, 0), time(11, 0)),
        (time(12, 0), time(15, 0)),
        (time(15, 30), time(18, 0)),
    ]
    assert scheduler_instance.get_free_slots(date) == expected


def test_get_free_slots_fully_busy(scheduler_instance):
    date = "2024-10-11"
    expected = [(time(8, 0), time(9, 30)), (time(16, 0), time(17, 0))]
    assert scheduler_instance.get_free_slots(date) == expected


def test_is_slot_available_true(scheduler_instance):
    assert scheduler_instance.is_slot_available("2024-10-10", "10:00", "10:45")
    assert scheduler_instance.is_slot_available("2024-10-10", "16:00", "17:00")


def test_is_slot_available_false_overlapping(scheduler_instance):
    assert not scheduler_instance.is_slot_available("2024-10-10", "11:30", "12:30")
    assert not scheduler_instance.is_slot_available("2024-10-10", "10:00", "12:00")


def test_is_slot_available_false_outside_work_hours(scheduler_instance):
    assert not scheduler_instance.is_slot_available("2024-10-10", "08:00", "09:00")
    assert not scheduler_instance.is_slot_available("2024-10-10", "18:00", "19:00")


def test_find_available_slots_for_duration(scheduler_instance):
    duration = 60
    expected = {
        "2024-10-10": [
            (time(9, 0), time(11, 0)),
            (time(12, 0), time(15, 0)),
            (time(15, 30), time(18, 0)),
        ],
        "2024-10-11": [(time(8, 0), time(9, 30)), (time(16, 0), time(17, 0))],
    }
    assert scheduler_instance.find_available_slots_for_duration(duration) == expected


def test_find_available_slots_for_duration_not_found(scheduler_instance):
    duration = 181
    assert scheduler_instance.find_available_slots_for_duration(duration) == {}


def test_invalid_date_format(scheduler_instance):
    with pytest.raises(ValueError, match="Invalid date format"):
        scheduler_instance.get_free_slots("2024/10/10")


def test_invalid_time_format(scheduler_instance):
    with pytest.raises(ValueError, match="Invalid time format"):
        scheduler_instance.is_slot_available("2024-10-10", "9-00", "10-00")


def test_start_time_after_end_time(scheduler_instance):
    with pytest.raises(ValueError, match="Start time must be earlier than end time"):
        scheduler_instance.is_slot_available("2024-10-10", "11:00", "10:00")


def test_negative_duration(scheduler_instance):
    with pytest.raises(ValueError, match="Duration must be a positive number"):
        scheduler_instance.find_available_slots_for_duration(-10)
