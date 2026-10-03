import time
from copy import deepcopy
from typing import Any, Dict, Optional

from .tools import search_flights, search_hotels
from .faults import FaultInjector


class TravelAgent:
    """
    Deterministic travel-booking agent with fault injection support.

    Phase 1 version recorded clean traces.
    Phase 2 version supports labeled failure injection.
    """

    def __init__(
        self,
        task: Dict[str, Any],
        recorder: Any,
        fault_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.task = task
        self.recorder = recorder
        self.fault_injector = FaultInjector(fault_config)
        self.state: Dict[str, Any] = {}

    def run(self) -> Dict[str, Any]:
        """
        Runs the full agent pipeline and saves the final trace.
        """
        # Save initial checkpoint before any step executes.
        self.recorder.save_checkpoint(
            state=self.state,
            step_id=0,
            name="initial",
        )

        # Step 1: Parse user request.
        self._execute_step(
            name="parse_request",
            step_type="planner",
            step_fn=self._parse_request,
            input_payload=lambda: {"instruction": self.task.get("instruction")},
            confidence=0.98,
        )

        # Step 2: Extract task constraints.
        self._execute_step(
            name="extract_constraints",
            step_type="planner",
            step_fn=self._extract_constraints,
            input_payload=lambda: {"parsed_request": self.state.get("parsed_request")},
            confidence=0.97,
        )

        # Step 3: Search flights.
        self._execute_step(
            name="search_flights",
            step_type="tool_call",
            step_fn=self._search_flights,
            input_payload=lambda: {
                "origin": self.state.get("constraints", {}).get("origin"),
                "destination": self.state.get("constraints", {}).get("destination"),
                "date": self.state.get("constraints", {}).get("date"),
            },
            confidence=0.95,
        )

        # Step 4: Filter flights by budget.
        self._execute_step(
            name="filter_flights_by_budget",
            step_type="transform",
            step_fn=self._filter_flights_by_budget,
            input_payload=lambda: {
                "flights": self.state.get("flights"),
                "budget": self.state.get("constraints", {}).get("flight_price_max"),
            },
            confidence=0.96,
        )

        # Step 5: Select cheapest flight.
        self._execute_step(
            name="select_cheapest_flight",
            step_type="decision",
            step_fn=self._select_cheapest_flight,
            input_payload=lambda: {
                "filtered_flights": self.state.get("filtered_flights"),
            },
            confidence=0.94,
        )

        # Step 6: Search hotels.
        self._execute_step(
            name="search_hotels",
            step_type="tool_call",
            step_fn=self._search_hotels,
            input_payload=lambda: {
                "city": self.state.get("constraints", {}).get("destination"),
                "checkin_date": self.state.get("constraints", {}).get("date"),
            },
            confidence=0.95,
        )

        # Step 7: Filter hotels by check-in constraint.
        self._execute_step(
            name="filter_hotels_by_checkin",
            step_type="transform",
            step_fn=self._filter_hotels_by_checkin,
            input_payload=lambda: {
                "hotels": self.state.get("hotels"),
                "hotel_checkin_after": self.state.get("constraints", {}).get(
                    "hotel_checkin_after"
                ),
            },
            confidence=0.96,
        )

        # Step 8: Select hotel.
        self._execute_step(
            name="select_hotel",
            step_type="decision",
            step_fn=self._select_hotel,
            input_payload=lambda: {
                "filtered_hotels": self.state.get("filtered_hotels"),
            },
            confidence=0.94,
        )

        # Step 9: Create booking.
        self._execute_step(
            name="create_booking",
            step_type="tool_call",
            step_fn=self._create_booking,
            input_payload=lambda: {
                "selected_flight": self.state.get("selected_flight"),
                "selected_hotel": self.state.get("selected_hotel"),
            },
            confidence=0.93,
        )

        # Step 10: Validate final result.
        self._execute_step(
            name="validate_final_result",
            step_type="validator",
            step_fn=self._validate_final_result,
            input_payload=lambda: {
                "booking": self.state.get("booking"),
                "constraints": self.state.get("constraints"),
            },
            confidence=0.99,
        )

        # Step 11: Send confirmation.
        self._execute_step(
            name="send_confirmation",
            step_type="output",
            step_fn=self._send_confirmation,
            input_payload=lambda: {
                "final_validation": self.state.get("final_validation"),
                "booking": self.state.get("booking"),
            },
            confidence=0.99,
        )

        final_validation = self.state.get("final_validation", {})
        status = "success" if final_validation.get("success") else "failed"

        return self.recorder.finish(
            final_state=deepcopy(self.state),
            status=status,
        )

    def _execute_step(
        self,
        name: str,
        step_type: str,
        step_fn: Any,
        input_payload: Any,
        confidence: float,
    ) -> Dict[str, Any]:
        """
        Executes one agent step and records it.

        Fault injection hooks are applied immediately before and after
        the step executes.
        """
        step_id = len(self.recorder.trace["steps"]) + 1
        state_before = deepcopy(self.state)

        # Apply fault before the step executes.
        self.fault_injector.before_step(name, self.state)

        # Build input after fault injection so recorded input is accurate.
        input_data = input_payload() if callable(input_payload) else input_payload

        start_time = time.perf_counter()
        error = None
        output: Dict[str, Any] = {}

        try:
            output = step_fn(self.state)
        except Exception as exc:
            error = str(exc)

        # Apply fault after the step executes, unless the step crashed.
        if error is None:
            output = self.fault_injector.after_step(name, self.state, output)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        state_after = deepcopy(self.state)

        self.recorder.record_step(
            step_id=step_id,
            name=name,
            step_type=step_type,
            input_payload=input_data,
            output=output,
            state_before=state_before,
            state_after=state_after,
            confidence=confidence,
            latency_ms=latency_ms,
            error=error,
        )

        return output

    def _parse_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the user's task into structured fields.
        """
        fields = [
            "origin",
            "destination",
            "date",
            "budget",
            "hotel_checkin_after",
        ]

        parsed_request = {field: self.task.get(field) for field in fields}
        parsed_request["instruction"] = self.task.get("instruction")

        state["parsed_request"] = parsed_request
        return parsed_request

    def _extract_constraints(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts parsed request into explicit constraints.
        """
        parsed_request = state.get("parsed_request", {})

        constraints = {
            "origin": parsed_request.get("origin"),
            "destination": parsed_request.get("destination"),
            "date": parsed_request.get("date"),
            "flight_price_max": parsed_request.get("budget"),
            "hotel_checkin_after": parsed_request.get("hotel_checkin_after"),
        }

        state["constraints"] = constraints
        return constraints

    def _search_flights(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls the deterministic flight search tool.
        """
        if state.get("_force_empty_flights"):
            flights = []
        else:
            constraints = state.get("constraints", {})
            flights = search_flights(
                origin=constraints.get("origin"),
                destination=constraints.get("destination"),
                date=constraints.get("date"),
            )

        state["flights"] = flights
        return {"flights": flights}

    def _filter_flights_by_budget(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filters flights using the budget constraint.
        """
        flights = state.get("flights", [])
        constraints = state.get("constraints", {})
        budget = constraints.get("flight_price_max", 0)

        filtered_flights = [
            flight
            for flight in flights
            if flight.get("price", float("inf")) <= budget
        ]

        state["filtered_flights"] = filtered_flights
        return {"filtered_flights": filtered_flights}

    def _select_cheapest_flight(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Selects the cheapest flight from the filtered flights.
        """
        filtered_flights = state.get("filtered_flights", [])

        selected_flight = None
        if filtered_flights:
            selected_flight = min(
                filtered_flights,
                key=lambda flight: flight.get("price", float("inf")),
            )

        state["selected_flight"] = selected_flight
        return {"selected_flight": selected_flight}

    def _search_hotels(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls the deterministic hotel search tool.
        """
        constraints = state.get("constraints", {})

        hotels = search_hotels(
            city=constraints.get("destination"),
            checkin_date=constraints.get("date"),
        )

        state["hotels"] = hotels
        return {"hotels": hotels}

    def _filter_hotels_by_checkin(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filters hotels by required check-in time.
        """
        hotels = state.get("hotels", [])
        constraints = state.get("constraints", {})
        hotel_checkin_after = constraints.get("hotel_checkin_after", "00:00")

        filtered_hotels = [
            hotel
            for hotel in hotels
            if hotel.get("checkin_time", "00:00") >= hotel_checkin_after
        ]

        state["filtered_hotels"] = filtered_hotels
        return {"filtered_hotels": filtered_hotels}

    def _select_hotel(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Selects the first valid hotel.
        """
        filtered_hotels = state.get("filtered_hotels", [])

        selected_hotel = None
        if filtered_hotels:
            selected_hotel = filtered_hotels[0]

        state["selected_hotel"] = selected_hotel
        return {"selected_hotel": selected_hotel}

    def _create_booking(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a booking if both flight and hotel are available.
        """
        selected_flight = state.get("selected_flight")
        selected_hotel = state.get("selected_hotel")

        booking = None

        if selected_flight and selected_hotel:
            booking = {
                "booking_id": "BK-1000",
                "flight": selected_flight,
                "hotel": selected_hotel,
                "total_price": selected_flight.get("price", 0)
                + selected_hotel.get("price", 0),
            }

        state["booking"] = booking
        return {"booking": booking}

    def _validate_final_result(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the final booking against task constraints.
        """
        constraints = state.get("constraints", {})
        booking = state.get("booking")
        violations = []

        if booking is None:
            violations.append("booking_missing")
        else:
            flight = booking.get("flight", {})
            hotel = booking.get("hotel", {})

            if flight.get("origin") != constraints.get("origin"):
                violations.append("flight_origin_mismatch")

            if flight.get("destination") != constraints.get("destination"):
                violations.append("flight_destination_mismatch")

            if flight.get("date") != constraints.get("date"):
                violations.append("flight_date_mismatch")

            if flight.get("price", 0) > constraints.get("flight_price_max", 0):
                violations.append("flight_budget_violation")

            if hotel.get("city") != constraints.get("destination"):
                violations.append("hotel_city_mismatch")

            if hotel.get("checkin_date") != constraints.get("date"):
                violations.append("hotel_date_mismatch")

            if hotel.get("checkin_time", "00:00") < constraints.get(
                "hotel_checkin_after", "00:00"
            ):
                violations.append("hotel_checkin_time_violation")

        result = {
            "success": len(violations) == 0,
            "violations": violations,
        }

        state["final_validation"] = result
        return result

    def _send_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produces the final confirmation output.
        """
        final_validation = state.get(
            "final_validation",
            {"success": False, "violations": ["validation_missing"]},
        )

        if final_validation.get("success"):
            booking = state.get("booking", {})
            flight = booking.get("flight", {})
            hotel = booking.get("hotel", {})

            message = (
                f"Booked flight {flight.get('flight_id')} and "
                f"hotel {hotel.get('hotel_id')} successfully."
            )

            confirmation = {
                "status": "sent",
                "message": message,
            }
        else:
            confirmation = {
                "status": "failed",
                "message": f"Booking failed: {final_validation.get('violations')}",
            }

        state["confirmation"] = confirmation
        return confirmation