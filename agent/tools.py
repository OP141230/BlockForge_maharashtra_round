import hashlib
import random
from typing import Any, Dict, List

def _seeded_rng(*args: Any) -> random.Random:
    """Generates a deterministic RNG based on input arguments."""
    h = hashlib.md5("".join(str(a) for a in args).encode()).hexdigest()
    return random.Random(int(h, 16))

def search_flights(origin: str, destination: str, date: str) -> List[Dict[str, Any]]:
    rng = _seeded_rng(origin, destination, date)
    flights = []
    # Generate 5 deterministic flights
    for i in range(5):
        flights.append({
            "flight_id": f"FL-{hashlib.md5(f'{origin}{destination}{i}{date}'.encode()).hexdigest()[:6].upper()}",
            "origin": origin,
            "destination": destination,
            "date": date,
            "price": rng.randint(3500, 12000),
            "arrival_time": f"{rng.randint(6, 22):02d}:{rng.choice(['00', '15', '30', '45'])}"
        })
    return flights

def search_hotels(city: str, checkin_date: str) -> List[Dict[str, Any]]:
    rng = _seeded_rng(city, checkin_date)
    hotels = []
    # Generate 5 deterministic hotels
    for i in range(5):
        hotels.append({
            "hotel_id": f"HT-{hashlib.md5(f'{city}{i}{checkin_date}'.encode()).hexdigest()[:6].upper()}",
            "city": city,
            "checkin_date": checkin_date,
            "checkin_time": f"{rng.randint(10, 18):02d}:00",
            "price_per_night": rng.randint(2000, 8000)
        })
    return hotels