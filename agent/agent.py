import time
from copy import deepcopy
from typing import Any, Dict, Optional

from .tools import search_flights, search_hotels
from .faults import FaultInjector


class TravelAgent:
    """
    Deterministic travel-booking agent with fault injection and replay support.
    """

    def __init__(
        self,
        task: Dict[str, Any],
        recorder: Any,
        fault_config: Optional[Dict[str, Any]] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        start_step_name: Optional[str] = None,
        patches: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.task = task
        self.recorder = recorder
        self.fault_injector = FaultInjector(fault_config)
        self.state = deepcopy(initial_state) if initial_state else {}
        self.start_step_name = start_step_name
        self.patches = patches or {}
        
        # If start_step_name is provided, we are in replay mode
        self._skip_mode = start_step_name is not None
        self._is_replay = start_step_name is not None

    def run(self) -> Dict[str, Any]:
        """
        Runs the agent pipeline. Skips steps before start_step_name if in replay mode.
        """
        if not self._skip_mode:
            self.recorder.save_checkpoint(
                state=self.state,
                step_id=0,
                name="initial",
            )

        steps_to_run = [
            ("parse_request", "planner", self._parse_request, lambda: {"instruction": self.task.get("instruction")}, 0.98),
            ("extract_constraints", "planner", self._extract_constraints, lambda: {"parsed_request": self.state.get("parsed_request")}, 0.97),
            ("search_flights", "tool_call", self._search_flights, lambda: {"origin": self.state.get("constraints", {}).get("origin"), "destination": self.state.get("constraints", {}).get("destination"), "date": self.state.get("constraints", {}).get("date")}, 0.95),
            ("filter_flights_by_budget", "transform", self._filter_flights_by_budget, lambda: {"flights": self.state.get("flights"), "budget": self.state.get("constraints", {}).get("flight_price_max")}, 0.96),
            ("select_cheapest_flight", "decision", self._select_cheapest_flight, lambda: {"filtered_flights": self.state.get("filtered_flights")}, 0.94),
            ("search_hotels", "tool_call", self._search_hotels, lambda: {"city": self.state.get("constraints", {}).get("destination"), "checkin_date": self.state.get("constraints", {}).get("date")}, 0.95),
            ("filter_hotels_by_checkin", "transform", self._filter_hotels_by_checkin, lambda: {"hotels": self.state.get("hotels"), "hotel_checkin_after": self.state.get("constraints", {}).get("hotel_checkin_after")}, 0.96),
            ("select_hotel", "decision", self._select_hotel, lambda: {"filtered_hotels": self.state.get("filtered_hotels")}, 0.94),
            ("create_booking", "tool_call", self._create_booking, lambda: {"selected_flight": self.state.get("selected_flight"), "selected_hotel": self.state.get("selected_hotel")}, 0.93),
            ("validate_final_result", "validator", self._validate_final_result, lambda: {"booking": self.state.get("booking"), "constraints": self.state.get("constraints")}, 0.99),
            ("send_confirmation", "output", self._send_confirmation, lambda: {"final_validation": self.state.get("final_validation"), "booking": self.state.get("booking")}, 0.99),
        ]

        for name, step_type, step_fn, input_payload, confidence in steps_to_run:
            if self._skip_mode:
                if name == self.start_step_name:
                    self._skip_mode = False
                else:
                    continue

            self._execute_step(
                name=name,
                step_type=step_type,
                step_fn=step_fn,
                input_payload=input_payload,
                confidence=confidence,
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
        Executes one agent step, applies faults/patches, and records it.
        """
        step_id = len(self.recorder.trace["steps"]) + 1
        state_before = deepcopy(self.state)

        # 1. Apply original faults (only if NOT in replay mode)
        if not self._is_replay:
            self.fault_injector.before_step(name, self.state)

        # 2. Apply replay patches (if in replay mode and patch exists)
        if self._is_replay and name in self.patches:
            patch = self.patches[name]
            if "state_override" in patch:
                for k, v in patch["state_override"].items():
                    if isinstance(v, dict) and isinstance(self.state.get(k), dict):
                        self.state[k].update(v)
                    else:
                        self.state[k] = v

        input_data = input_payload() if callable(input_payload) else input_payload

        start_time = time.perf_counter()
        error = None
        output: Dict[str, Any] = {}

        try:
            output = step_fn(self.state)
        except Exception as exc:
            error = str(exc)

        # 3. Apply original faults after step (only if NOT in replay mode)
        if error is None and not self._is_replay:
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
        
        self.recorder.save_checkpoint(
            state=self.state,
            step_id=step_id,
            name=name,
        )

        return output

    # ---------------------------------------------------------
    # Step Functions (Unchanged from Phase 2)
    # ---------------------------------------------------------

    def _parse_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        fields = ["origin", "destination", "date", "budget", "hotel_checkin_after"]
        parsed_request = {field: self.task.get(field) for field in fields}
        parsed_request["instruction"] = self.task.get("instruction")
        state["parsed_request"] = parsed_request
        return parsed_request

    def _extract_constraints(self, state: Dict[str, Any]) -> Dict[str, Any]:
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
        flights = state.get("flights", [])
        constraints = state.get("constraints", {})
        budget = constraints.get("flight_price_max", 0)
        filtered_flights = [f for f in flights if f.get("price", float("inf")) <= budget]
        state["filtered_flights"] = filtered_flights
        return {"filtered_flights": filtered_flights}

    def _select_cheapest_flight(self, state: Dict[str, Any]) -> Dict[str, Any]:
        filtered_flights = state.get("filtered_flights", [])
        selected_flight = None
        if filtered_flights:
            selected_flight = min(filtered_flights, key=lambda f: f.get("price", float("inf")))
        state["selected_flight"] = selected_flight
        return {"selected_flight": selected_flight}

    def _search_hotels(self, state: Dict[str, Any]) -> Dict[str, Any]:
        constraints = state.get("constraints", {})
        hotels = search_hotels(
            city=constraints.get("destination"),
            checkin_date=constraints.get("date"),
        )
        state["hotels"] = hotels
        return {"hotels": hotels}

    def _filter_hotels_by_checkin(self, state: Dict[str, Any]) -> Dict[str, Any]:
        hotels = state.get("hotels", [])
        constraints = state.get("constraints", {})
        hotel_checkin_after = constraints.get("hotel_checkin_after", "00:00")
        filtered_hotels = [h for h in hotels if h.get("checkin_time", "00:00") >= hotel_checkin_after]
        state["filtered_hotels"] = filtered_hotels
        return {"filtered_hotels": filtered_hotels}

    def _select_hotel(self, state: Dict[str, Any]) -> Dict[str, Any]:
        filtered_hotels = state.get("filtered_hotels", [])
        selected_hotel = filtered_hotels[0] if filtered_hotels else None
        state["selected_hotel"] = selected_hotel
        return {"selected_hotel": selected_hotel}

    def _create_booking(self, state: Dict[str, Any]) -> Dict[str, Any]:
        selected_flight = state.get("selected_flight")
        selected_hotel = state.get("selected_hotel")
        booking = None
        if selected_flight and selected_hotel:
            booking = {
                "booking_id": "BK-1000",
                "flight": selected_flight,
                "hotel": selected_hotel,
                "total_price": selected_flight.get("price", 0) + selected_hotel.get("price", 0),
            }
        state["booking"] = booking
        return {"booking": booking}

    def _validate_final_result(self, state: Dict[str, Any]) -> Dict[str, Any]:
        constraints = state.get("constraints", {})
        booking = state.get("booking")
        violations = []

        if booking is None:
            violations.append("booking_missing")
        else:
            flight = booking.get("flight", {})
            hotel = booking.get("hotel", {})

            if flight.get("origin") != constraints.get("origin"): violations.append("flight_origin_mismatch")
            if flight.get("destination") != constraints.get("destination"): violations.append("flight_destination_mismatch")
            if flight.get("date") != constraints.get("date"): violations.append("flight_date_mismatch")
            if flight.get("price", 0) > constraints.get("flight_price_max", 0): violations.append("flight_budget_violation")
            if hotel.get("city") != constraints.get("destination"): violations.append("hotel_city_mismatch")
            if hotel.get("checkin_date") != constraints.get("date"): violations.append("hotel_date_mismatch")
            if hotel.get("checkin_time", "00:00") < constraints.get("hotel_checkin_after", "00:00"): violations.append("hotel_checkin_time_violation")

        result = {"success": len(violations) == 0, "violations": violations}
        state["final_validation"] = result
        return result

    def _send_confirmation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        final_validation = state.get("final_validation", {"success": False, "violations": ["validation_missing"]})
        if final_validation.get("success"):
            booking = state.get("booking", {})
            flight = booking.get("flight", {})
            hotel = booking.get("hotel", {})
            message = f"Booked flight {flight.get('flight_id')} and hotel {hotel.get('hotel_id')} successfully."
            confirmation = {"status": "sent", "message": message}
        else:
            confirmation = {"status": "failed", "message": f"Booking failed: {final_validation.get('violations')}"}
        
        state["confirmation"] = confirmation
        return confirmation