def acts_mapping(domain: str, act: str):
    if domain == "apartment_search":
        if act.startswith("AskField(search_apartment, num_bedrooms"):
            return ["apartment_ask_num_bedrooms", "hello"]
        elif act.startswith("AskField(search_apartment, price"):
            return ["apartment_ask_price"]
        elif act.startswith("AskField(search_apartment, floor_level"):
            return ["apartment_ask_floor"]
        elif act.startswith("AskField(search_apartment, has_balcony"):
            return ["apartment_ask_balcony"]
        elif act.startswith("AskField(search_apartment, balcony_side"):
            return ["apartment_ask_balcony"]
        elif act.startswith("AskField(search_apartment, has_elevator"):
            return ["apartment_ask_elevator"]
        elif act.startswith("AskField(search_apartment, nearby_point_of_interest"):
            return ["apartment_ask_nearby_pois"]
        elif act.startswith("Report(search_apartment_result"):
            return [
                "apartment_inform_search_result",
                "apartment_inform_nothing_found",
                "apartment_inform_search_criteria",
            ]
        elif act.startswith("ProposeAgentAct(NewSearchApartment"):
            return ["apartment_ask_search_more"]
    elif domain == "apartment_schedule":
        if act.startswith("AskField(request_apartment_visit, customer_name"):
            return ["apartment_ask_name", "ask_name", "hello"]
        elif act.startswith("AskField(request_apartment_visit, apartment_name"):
            return ["apartment_ask_apartment_name"]
        elif act.startswith("AskField(request_apartment_visit, day_of_visit"):
            return ["apartment_ask_day"]
        elif act.startswith("AskField(request_apartment_visit, start_time"):
            return ["apartment_ask_start_time"]
        elif act.startswith("AskField(request_apartment_visit, application_fee_paid"):
            return ["apartment_ask_application_fee_paid"]
        elif act.startswith(
            "AskField(request_apartment_visit, special_request_from_customer"
        ):
            return ["apartment_ask_custom_message"]
        elif act.startswith("Report(request_apartment_visit_result"):
            return [
                "apartment_inform_viewing_unavailable",
                "apartment_inform_viewing_available",
                "apartment_inform_booking_successful",
            ]
        elif act.startswith("ProposeAgentAct(ConfirmApartmentVisit"):
            return [
                "anything_else",
                "apartment_inform_viewing_unavailable",
                "apartment_inform_viewing_available",
                "apartment_inform_booking_successful",
            ]
    elif domain == "bank_fraud_report":
        if act.startswith("AskField(main, full_name"):
            return ["ask_name", "hello"]
        elif act.startswith("AskField(main, fraud_report"):
            return ["bank_ask_fraud_details"]
        elif act.startswith("AskField(main, first_authentication_details"):
            return ["bank_ask_account_number"]
        elif act.startswith("AskField(main, second_authentication_details"):
            return ["bank_ask_dob", "bank_inform_cannot_authenticate"]
        elif act.startswith("AskField(first_authentication, account_number"):
            return ["bank_ask_account_number"]
        elif act.startswith("AskField(first_authentication, pin"):
            return ["bank_ask_pin"]
        elif act.startswith("AskField(second_authentication, security_answer_1"):
            return ["bank_ask_mothers_maiden_name", "bank_inform_cannot_authenticate"]
        elif act.startswith("AskField(second_authentication, security_answer_2"):
            return ["bank_ask_childhood_pets_name", "bank_inform_cannot_authenticate"]
        elif act.startswith("AskField(second_authentication, date_of_birth"):
            return ["bank_ask_dob", "bank_inform_cannot_authenticate"]
        elif act.startswith("Report(bank_fraud_report"):
            return [
                "bank_inform_fraud_report_submitted",
                "bank_inform_cannot_authenticate",
            ]
        else:
            return []
    elif domain == "trivia":
        if act.startswith("AskField(question_answer, user_answer"):
            return ["trivia_ask_question", "trivia_bye"]
        elif act.startswith("AskField(main, starting_question_number"):
            return ["hello", "trivia_ask_question_number"]
        elif act.startswith("AskField(question_answer, continue_trivia"):
            return [
                "trivia_inform_answer_correct_ask_next",
                "trivia_inform_answer_incorrect_ask_next",
                "trivia_inform_answer_2_ask_next",
                "trivia_ask_question",
            ]
        else:
            return ["trivia_ask_question", "trivia_inform_answer_correct_ask_next"]
    elif domain == "trip":
        if act.startswith("AskField(travel_information, travel_mode"):
            return ["trip_ask_travel_mode", "hello"]
        elif act.startswith("AskField(travel_information, departure_location"):
            return ["ask_departure_location"]
        elif act.startswith("AskField(travel_information, arrival_location"):
            return ["trip_ask_arrival_location"]
        elif act.startswith("AskField(travel_information, departure_time"):
            return ["trip_ask_departure_time"]
        elif act.startswith("ProposeAgentAct(ContinueDetails,"):
            return ["trip_inform_simple_step_ask_proceed"]
        elif act.startswith("AskField(continue_details, show_next_step"):
            return [
                "trip_inform_simple_step_ask_proceed",
                "trip_inform_last_step_and_done",
                "trip_instructions_done",
            ]
        else:
            return [
                "hello",
                "query",
                "trip_inform_nothing_found",
                "anything_else",
                "goodbye_1",
                "out_of_scope",
            ]


def star_acts(domain):
    if domain == "apartment_search":
        return {
            "hello": "say hello to the user",
            "apartment_ask_num_bedrooms": "request Num Rooms from user",
            "apartment_ask_price": "request Price (monthly cold rent) from user",
            "apartment_ask_floor": "request Level from user",
            "apartment_ask_balcony": "request Has Balcony from user",
            "apartment_ask_elevator": "request Has Elevator from user",
            "apartment_ask_nearby_pois": "request Nearby POIs from user",
            "query": "query to find apartments",
            "apartment_inform_search_result": "inform user apartment search result",
            "apartment_inform_nothing_found": "tell user no apartments matched their criteria",
            "apartment_ask_search_more": "ask the user if they want to search for more apartments",
            "apartment_inform_search_criteria": "tell user what criteria you can search apartments for",
            "goodbye_2": "say goodbye to user",
            "anything_else": "ask user if they need anything else",
            "out_of_scope": "tell the user that you're not sure what they'd like to do",
        }
    elif domain == "apartment_schedule":
        return {
            "hello": "Hello, how can I help?",
            "ask_name": "Could you give me your name, please?",
            "apartment_ask_name": "Could you give me your name, please?",
            "apartment_ask_apartment_name": "What apartment are you interested in?",
            "apartment_ask_day": "What day would you like to make the booking for?",
            "apartment_ask_start_time": "When would you like the viewing to start?",
            "apartment_ask_end_time": "For how long would you like to see the apartment?",
            "apartment_ask_application_fee_paid": "Have you already paid the application fee for the apartment?",
            "apartment_ask_custom_message": "Would you like to add a message for the letting agency?",
            "apartment_inform_viewing_unavailable": "I am sorry, but there is no viewing available at your preferred time.",
            "apartment_inform_viewing_available": "Great, there is still a viewing available at that time. Would you like me to book it for you?",
            "apartment_inform_booking_successful": "Excellent, the booking is done for you!",
            "goodbye_1": "Thank you and goodbye.",
            "anything_else": "Is there anything else that I can do for you?",
            "out_of_scope": "I am sorry, I don't quite understand what you mean. I am only able to help you book apartment viewings.",
        }

    elif domain == "plane_search":
        return {
            "hello": "say hello to user",
            "ask_departure_location": "request Departure City from user",
            "plane_ask_arrival_city": "request Arrival City from user",
            "plane_ask_date": "request Date from user",
            "plane_request_optional": "inform user what we can filter flights by",
            "query": "query flight search api",
            "plane_inform_flight_details": "inform user about a flight that matches their criteria",
            "plane_inform_nothing_found": "inform user no flights were found",
            "plane_ask_more_questions": "ask the user if they want to search for more flights",
            "anything_else": "ask the user if they need anything else",
            "goodbye_2": "say goodbye to user",
            "out_of_scope": "tell the user that you're not sure what they'd like to do",
        }
    elif domain == "bank_fraud_report":
        return {
            "hello": "say hello to user",
            "ask_name": "request Full Name from user",
            "bank_ask_account_number": "request Account Number from user",
            "bank_ask_pin": "request PIN from user",
            "bank_ask_fraud_details": "request Fraud Report from user",
            "query": "query bank api to authenticate user",
            "bank_inform_cannot_authenticate": "inform user authentication failed",
            "bank_inform_fraud_report_submitted": "inform user fraud report was submitted successfully",
            "bank_ask_dob": "request Date Of Birth from user",
            "bank_ask_mothers_maiden_name": "request Mother's Maiden Name from user",
            "bank_ask_childhood_pets_name": "request Name Of Childhood Pet from user",
            "anything_else": "ask user if they need anything else",
            "goodbye_1": "say goodbye to user",
            "bank_inform_nothing_found": "inform user nothing was found",
        }
    elif domain == "trip":
        return {
            "hello": "say hello to the user",
            "trip_ask_travel_mode": "request Travel Mode from user",
            "ask_departure_location": "request Departure Location from user",
            "trip_ask_arrival_location": "request Arrival Location from user",
            "trip_ask_departure_time": "request Departure Time from user",
            "query": "query api for trip directions",
            "trip_inform_simple_step_ask_proceed": "inform user a simple direction",
            "trip_inform_detailed_step": "inform user a detailed direction",
            "trip_inform_last_step_and_done": "inform user final direction",
            "trip_instructions_done": "inform user they should be at destination",
            "anything_else": "ask the user if there's anything else they need",
            "goodbye_1": "say goodbye to the user",
            "trip_inform_nothing_found": "inform user you weren't able to find any directions",
            "out_of_scope": "tell user that you're not sure what they'd like to do",
        }
    elif domain == "trivia":
        return {
            "hello": "say hello to user",
            "trivia_ask_question_number": "ask user for a trivia question number",
            "query": "query the trivia api to retrieve a trivia question",
            "trivia_ask_question": "ask the trivia question to user",
            "trivia_inform_answer_correct_ask_next": "inform user their answer was correct",
            "trivia_inform_answer_incorrect_ask_next": "inform user their answer was incorrect",
            "trivia_inform_answer_2_ask_next": "inform user the correct answer since they don't know it",
            "anything_else": "ask user if there's anything else they need",
            "trivia_bye": "say goodbye to user",
            "trivia_inform_nothing_found": "inform user you weren't able to find anything",
            "out_of_scope": "tell user that you're not sure what they'd like to do",
        }


def convertable_int(value):
    try:
        return int(value)
    except ValueError:
        return value


def mapping_from_spreadsheet_fields_to_belief_state_fields(
    spreadsheet_name, field_name, value
):
    if spreadsheet_name == "SearchApartment":
        mapping = {
            "num_bedrooms": "NumRooms",
            "floor_level": "Level",
            "price": "Price",
            "has_balcony": "HasBalcony",
            "balcony_side": "BalconySide",
            "has_elevator": "HasElevator",
            "nearby_point_of_interest": "NearbyPOIs",
        }
        belief_state_field_name = mapping[field_name]
        if belief_state_field_name == "Price" and isinstance(
            convertable_int(value), int
        ):
            value = f"api.is_at_most({value})"
        return belief_state_field_name, value

    if spreadsheet_name == "PlaneSearch":
        mapping = {
            "departure_city": "DepartureCity",
            "arrival_city": "ArrivalCity",
            "date": "Date",
            "airline": "Airline",
            "cabin_class": "Class",
            "price": "Price",
            "duration_hours": "DurationHourss",
        }
        belief_state_field_name = mapping[field_name]
        return belief_state_field_name, value


def mapping_from_user_target_to_ActionLabel(
    user_target, past_user_targets, global_context
):
    res = []
    if (
        "search_apartment" in user_target
        or "SearchApartment" in user_target
        or "SearchApartment" in global_context
    ):
        if not any(
            "search_apartment" in past_user_target
            or "SearchApartment" in past_user_target
            for past_user_target in past_user_targets
        ):
            res.append("user_apartment_search_ask_apartment")
        if "num_bedrooms" in user_target:
            res.append("user_apartment_search_inform_num_bedrooms")
        if "price" in user_target:
            res.append("user_apartment_search_inform_price")
        if "floor_level" in user_target:
            res.append("user_apartment_search_inform_floor")
        if "has_balcony" in user_target:
            res.append("user_apartment_search_inform_balcony")
        if "has_elevator" in user_target:
            res.append("user_apartment_search_inform_elevator")
        if "nearby_point_of_interest" in user_target:
            res.append("user_apartment_search_inform_poi")

    return res
