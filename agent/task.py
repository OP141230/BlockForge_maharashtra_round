from typing import Any, Dict

def sampleTask() -> Dict[str, Any]:
    return {
        "task_id": "task_001",
        "type": "travel_booking",
        "instruction": (
            "Book the cheapest flight from Mumbai to Delhi tomorrow "
            "under 6000 and book a hotel with check-in after 14:00."
        ),
        "origin": "Mumbai",
        "destination": "Delhi",
        "date": "2026-10-04",
        "current_date": "2026-10-03",
        "budget": 6000,
        "hotel_checkin_after": "14:00",
    }