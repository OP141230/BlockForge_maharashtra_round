from typing import Any, Dict, List


def search_flights(origin: str, destination: str, date: str) -> List[Dict[str, Any]]:
    if origin == "Mumbai" and destination == "Delhi" and date == "2026-10-04":
        return [
            {
                "flight_id": "6E-203",
                "origin": "Mumbai",
                "destination": "Delhi",
                "date": "2026-10-04",
                "price": 4850,
                "arrival_time": "18:30",
            },
            {
                "flight_id": "AI-555",
                "origin": "Mumbai",
                "destination": "Delhi",
                "date": "2026-10-04",
                "price": 5900,
                "arrival_time": "19:10",
            },
            {
                "flight_id": "SG-118",
                "origin": "Mumbai",
                "destination": "Delhi",
                "date": "2026-10-04",
                "price": 7200,
                "arrival_time": "20:05",
            },
        ]

    return []


def search_hotels(city: str, checkin_date: str) -> List[Dict[str, Any]]:
    if city == "Delhi" and checkin_date == "2026-10-04":
        return [
            {
                "hotel_id": "H-101",
                "city": "Delhi",
                "checkin_date": "2026-10-04",
                "checkin_time": "13:00",
                "price": 1200,
            },
            {
                "hotel_id": "H-205",
                "city": "Delhi",
                "checkin_date": "2026-10-04",
                "checkin_time": "15:00",
                "price": 1400,
            },
            {
                "hotel_id": "H-310",
                "city": "Delhi",
                "checkin_date": "2026-10-04",
                "checkin_time": "16:30",
                "price": 1800,
            },
        ]

    return []