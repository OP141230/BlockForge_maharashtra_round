"""TravelPlanner AI Agent implementation instrumented with BLACKBOX Flight Recorder."""
import time
from typing import Any, Dict, Optional
from agent.tools import search_flights, search_hotels
from recorder.recorder import FlightRecorder


class TravelPlannerAgent:
    """Demo AI Agent capable of planning itineraries with full flight recording."""

    def __init__(self, recorder: Optional[FlightRecorder] = None):
        self.recorder = recorder or FlightRecorder("TravelPlanner", "Flight and Hotel Itinerary")

    def run_task(self, task: Dict[str, Any], inject_bug: bool = True) -> Dict[str, Any]:
        """Execute travel planning workflow."""
        run_id = self.recorder.start_run(
            task_description=task.get("instruction", "Book trip"),
            metadata=task,
        )

        try:
            # Step 1: Parse requirements
            t0 = time.time()
            origin = task.get("origin", "Mumbai")
            dest = task.get("destination", "Delhi")
            date = task.get("date", "2026-10-04")
            budget = task.get("budget", 6000)
            req_out = {
                "origin": origin,
                "destination": dest,
                "date": date,
                "budget": budget,
                "hotel_checkin_after": task.get("hotel_checkin_after", "14:00"),
            }
            s0 = self.recorder.record_step(
                step_name="Parse Requirements",
                tool_name="parse_requirements",
                input_data=task,
                output_data=req_out,
                duration_ms=(time.time() - t0) * 1000 + 35.0,
            )

            # Step 2: Search flights
            t0 = time.time()
            flights = search_flights(origin, dest, date)
            selected_flight = min(flights, key=lambda f: f["price"]) if flights else None
            flight_out = {"flights_found": len(flights), "selected_flight": selected_flight}
            s1 = self.recorder.record_step(
                step_name="Search Flights",
                tool_name="search_flights",
                input_data={"origin": origin, "destination": dest, "date": date},
                output_data=flight_out,
                duration_ms=(time.time() - t0) * 1000 + 290.0,
                dependencies=[s0],
            )

            # Step 3: Search hotels
            t0 = time.time()
            hotels = search_hotels(dest, date)
            valid_hotels = [
                h for h in hotels
                if h["checkin_time"] >= task.get("hotel_checkin_after", "14:00")
            ]
            selected_hotel = min(valid_hotels, key=lambda h: h["price"]) if valid_hotels else None
            hotel_out = {"hotels_found": len(hotels), "selected_hotel": selected_hotel}
            s2 = self.recorder.record_step(
                step_name="Search Hotels",
                tool_name="search_hotels",
                input_data={"city": dest, "checkin_date": date},
                output_data=hotel_out,
                duration_ms=(time.time() - t0) * 1000 + 275.0,
                dependencies=[s0],
            )

            # Step 4: Budget Calculation
            t0 = time.time()
            flight_price = selected_flight["price"] if selected_flight else 0
            hotel_price = selected_hotel["price"] if selected_hotel else 0
            
            if inject_bug:
                # Buggy calculation: hotel price added twice
                total = flight_price + hotel_price + hotel_price
                breakdown = [
                    {"category": "Flight", "amount": flight_price},
                    {"category": "Hotel", "amount": hotel_price},
                    {"category": "Hotel", "amount": hotel_price},
                ]
            else:
                total = flight_price + hotel_price
                breakdown = [
                    {"category": "Flight", "amount": flight_price},
                    {"category": "Hotel", "amount": hotel_price},
                ]

            calc_out = {
                "total_cost": total,
                "budget_limit": budget,
                "breakdown": breakdown,
                "is_over_budget": total > budget,
            }
            s3 = self.recorder.record_step(
                step_name="Budget Calculation",
                tool_name="budget_calculation",
                input_data={"flight_cost": flight_price, "hotel_cost": hotel_price, "budget": budget},
                output_data=calc_out,
                duration_ms=(time.time() - t0) * 1000 + 45.0,
                dependencies=[s1, s2],
            )

            # Step 5: Final Validation & Booking
            t0 = time.time()
            if total > budget:
                err_msg = f"BudgetExceededError: Calculated total {total} exceeds limit {budget}"
                self.recorder.record_step(
                    step_name="Finalize Booking",
                    tool_name="finalize_booking",
                    input_data={"total": total, "budget": budget},
                    output_data={"error": err_msg},
                    duration_ms=(time.time() - t0) * 1000 + 50.0,
                    status="FAILED",
                    error_text=err_msg,
                    side_effect_flag=True,
                    dependencies=[s3],
                )
                self.recorder.finish_run(status="FAILED", error_message=err_msg)
                return {"status": "FAILED", "error": err_msg, "run_id": run_id}

            # Success path
            book_out = {
                "booking_id": "BKG-MUM-DEL-01",
                "status": "CONFIRMED",
                "total_paid": total,
            }
            self.recorder.record_step(
                step_name="Finalize Booking",
                tool_name="finalize_booking",
                input_data={"flight": selected_flight, "hotel": selected_hotel},
                output_data=book_out,
                duration_ms=(time.time() - t0) * 1000 + 120.0,
                status="SUCCESS",
                side_effect_flag=True,
                dependencies=[s3],
            )
            self.recorder.finish_run(status="SUCCESS")
            return {"status": "SUCCESS", "booking": book_out, "run_id": run_id}

        except Exception as exc:
            self.recorder.finish_run(status="FAILED", error_message=str(exc))
            return {"status": "FAILED", "error": str(exc), "run_id": run_id}
