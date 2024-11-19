import argparse
import json
import os
import re
from glob import glob

from mappings import (
    acts_mapping,
    mapping_from_spreadsheet_fields_to_belief_state_fields,
    mapping_from_user_target_to_ActionLabel,
    star_acts,
)

from worksheets.environment import (
    GenieContext,
    GenieWorksheet,
    get_genie_fields_from_ws,
)

current_dir = os.path.dirname(os.path.abspath(__file__))


def import_agent(domain):
    if domain == "apartment_search":
        from apartment_search.apartment_search import apartment_search_agent, gsheet_id

        return apartment_search_agent.load_from_gsheet(gsheet_id)
    elif domain == "bank_fraud_report":
        from bank_fraud.bank_fraud import bank_fraud_agent, gsheet_id

        return bank_fraud_agent.load_from_gsheet(gsheet_id)
    elif domain == "trip_planner":
        from trip.trip import gsheet_id, trip_planner_agent

        return trip_planner_agent.load_from_gsheet(gsheet_id)
    elif domain == "trivia":
        from trivia.trivia import gsheet_id, trivia_agent

        return trivia_agent.load_from_gsheet(gsheet_id)
    else:
        raise ValueError(f"Domain {domain} not supported")


def get_predicted_belief_state_from_global_context(global_context, domain):
    local_context = GenieContext({})
    bot = import_agent(domain)

    bot.execute(global_context, local_context=local_context, sp=True)
    predicted_belief_state = {}
    for key, value in local_context.context.items():
        if isinstance(value, GenieWorksheet):
            for field in get_genie_fields_from_ws(value):
                if (
                    field.value is not None
                    and field.value != "NA"
                    and not isinstance(field.value, GenieWorksheet)
                ):
                    new_field_name, new_value = (
                        mapping_from_spreadsheet_fields_to_belief_state_fields(
                            value.__class__.__name__, field.name, field.value
                        )
                    )
                    predicted_belief_state[new_field_name] = new_value
    return predicted_belief_state


def compare_and_convert(value1, value2):
    # Helper function to convert string to boolean if possible
    def str_to_bool(value):
        if isinstance(value, str):
            if value.lower() == "true":
                return True
            elif value.lower() == "false":
                return False
        return value

    # Case 1: One is bool and the other is a string, convert string to bool and compare
    value1 = str_to_bool(value1)
    value2 = str_to_bool(value2)

    # Case 1: One is bool and the other is not, convert both to bool and compare
    if isinstance(value1, bool) != isinstance(value2, bool):
        return bool(value1) == bool(value2)

    # Case 2: One or both are int or float, convert both to float and compare
    elif isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
        return float(value1) == float(value2)

    # Case 3: If one is a number and the other is a string, try to convert the string to a number
    elif isinstance(value1, (int, float)) and isinstance(value2, str):
        try:
            return float(value1) == float(value2)
        except ValueError:
            return False
    elif isinstance(value1, str) and isinstance(value2, (int, float)):
        try:
            return float(value1) == float(value2)
        except ValueError:
            return False

    # Case 3: If neither special case, compare values directly
    return value1 == value2


def remove_quotes_inside_parentheses(text):
    # Regular expression to find and remove both single and double quotes inside parentheses
    pattern = r"\(([^()]*?)[\"']([^()]*?)[\"']\)"
    # Replace the single or double quotes inside parentheses
    return re.sub(pattern, r"(\1\2)", text)


def compute_two_dicts_equal(predicted_belief_state, gold_belief_state):
    if predicted_belief_state.keys() != gold_belief_state.keys():
        return False

    for key, value in predicted_belief_state.items():
        if gold_belief_state[key] == value:
            continue

        # else, attempt to do some standarization
        if compare_and_convert(value, gold_belief_state[key]):
            continue

        if isinstance(value, str) and isinstance(gold_belief_state[key], str):
            value = value.replace("is_atmost", "is_at_most")
            value = value.replace("is_atleast", "is_at_least")
            value = value.replace("dont_care", "dontcare")
            value = remove_quotes_inside_parentheses(value)
            value = value.lower()

        if gold_belief_state[key] == value:
            continue

        return False

    return True


def evaluate_JGA(data, domain):
    em = 0
    total = 0
    for i, turn in enumerate(data):
        predicted_belief_state = get_predicted_belief_state_from_global_context(
            turn["state"][0]["global_context"], domain
        )
        if "PredictedBeliefState" not in turn["event"]:
            continue
        gold_belief_state = turn["event"]["PredictedBeliefState"]

        if compute_two_dicts_equal(predicted_belief_state, gold_belief_state):
            em += 1

        total += 1

    return em, total


def evaluate_UA_metrics(data):
    em = 0
    total = 0

    user_targets = []
    for i, turn in enumerate(data):
        predicted_user_action = mapping_from_user_target_to_ActionLabel(
            turn["state"][0]["user_target"],
            user_targets,
            turn["state"][0]["user_target"],
        )

        if "ActionLabel" not in turn["event"]:
            continue
        user_targets.append(turn["state"][0]["user_target"])
        gold_user_action = turn["event"]["ActionLabel"]
        for i in ["user_hello", "user_apartment_goodbye", "user_bad_label"]:
            if i in gold_user_action:
                gold_user_action.remove(i)

        if set(predicted_user_action) == set(gold_user_action):
            em += 1
        else:
            print(predicted_user_action)
            print(gold_user_action)
            print("====")
        total += 1
    return em, total


def evaluate_system_action(data, domain):
    all_star_acts = (
        list(star_acts(domain).keys()) + ["out_of_scope"] + ["others"] + ["custom"]
    )
    accuracy = []
    pred = []
    true = []
    for i, turn in enumerate(data):
        ws_act = turn["state"][0]["system_action"]
        gt_act = turn["sys_act"]

        # If there are Genie Worksheet actions
        if len(ws_act):
            for act in ws_act:
                # If the action is a Report action, we consider it as correct
                if act.startswith("Report(None, "):
                    accuracy.append(1)
                    continue

                # Get mapped acts for the domain for this specific action
                mapped_act = acts_mapping(domain, act)

                if isinstance(gt_act, list):
                    for gt in gt_act:
                        # action is present in the mapped acts
                        if gt in mapped_act:
                            pred.append(all_star_acts.index(gt_act[0]))
                            true.append(all_star_acts.index(gt_act[0]))
                            accuracy.append(1)
                        else:
                            pred.append(all_star_acts.index(mapped_act[0]))
                            true.append(all_star_acts.index(gt_act[0]))
                            print("SA:", gt_act, mapped_act)

                            accuracy.append(0)
                else:
                    if (
                        gt_act
                        and gt_act != "goodbye_1"
                        and gt_act != "goodbye_2"
                        and gt_act != "out_of_scope"
                        and gt_act != "anything_else"
                    ):
                        if gt_act in mapped_act:
                            pred.append(all_star_acts.index(gt_act))
                            true.append(all_star_acts.index(gt_act))
                            accuracy.append(1)
                        else:
                            if len(mapped_act) > 0:
                                print(mapped_act)
                                pred.append(all_star_acts.index(mapped_act[0]))
                            else:
                                pred.append(all_star_acts.index("others"))
                            true.append(all_star_acts.index(gt_act))
                            accuracy.append(0)
                            print("SA:", gt_act, mapped_act)

                    else:
                        # Genie Worksheet doesn't contain the mentioned acts for goodbye and out of scope
                        pred.append(all_star_acts.index("others"))
                        true.append(all_star_acts.index("others"))
                        accuracy.append(1)
        else:
            if gt_act is None:
                # If the ground truth action is None, we consider it as correct
                pred.append(all_star_acts.index("others"))
                true.append(all_star_acts.index("others"))
                accuracy.append(1)
            # else:
            #     # Else there exists some action that should have been taken
            #     pred.append(all_star_acts.index("others"))
            #     true.append(all_star_acts.index(gt_act))
            #     accuracy.append(0)

    return accuracy, pred, true


def evaluate_task(files, domain, evaluate, evaluate_all):
    acc = []

    preds = []
    trues = []

    jga_em = 0
    jga_total = 0
    uaAcc_em = 0
    uaAcc_total = 0

    for file in files:
        with open(file, "r") as f:
            data = json.load(f)
        print(file)

        if len(data) == 0:
            continue
        if evaluate_all or evaluate == "JGA":
            jga_em_this_turn, jga_total_this_turn = evaluate_JGA(data, domain)
            jga_em += jga_em_this_turn
            jga_total += jga_total_this_turn

        if evaluate_all or evaluate == "UA":
            uaAcc_em_this_turn, uaAcc_total_this_turn = evaluate_UA_metrics(data)
            uaAcc_em += uaAcc_em_this_turn
            uaAcc_total += uaAcc_total_this_turn

        if evaluate_all or evaluate == "SA":
            acc_this_turn, pred_this_turn, true_this_turn = evaluate_system_action(
                data, domain
            )
            print(acc_this_turn)
            if len(acc_this_turn):
                acc.append(sum(acc_this_turn) / len(acc_this_turn))
                if len(pred_this_turn) and len(true_this_turn):
                    preds.append(pred_this_turn)
                    trues.append(true_this_turn)

    if evaluate_all or evaluate == "SA":
        print(f"SaAcc: {sum(acc) / len(acc)}")

    if evaluate_all or evaluate == "JGA":
        print(f"JGA: {jga_em}/{jga_total} = {jga_em/jga_total}")

    if evaluate_all or evaluate == "UA":
        print(f"UaAcc: {uaAcc_em}/{uaAcc_total} = {uaAcc_em/uaAcc_total}")


if __name__ == "__main__":

    def create_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--input", type=str)
        parser.add_argument("--domain", type=str)
        parser.add_argument(
            "--evaluation_metric", type=str, default="SA", choices=["SA", "JGA", "UA"]
        )
        parser.add_argument("--evaluate_all", action="store_true")
        return parser

    args = create_parser().parse_args()
    files = glob(os.path.join(args.input, "*.json"))
    evaluate_task(files, args.domain, args.evaluation_metric, args.evaluate_all)
