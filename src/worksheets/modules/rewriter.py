import ast
import re
from _ast import Assign, Attribute, Expr
from typing import Any

from loguru import logger

from worksheets.modules.utils import assert_with_message


class FindFunctionCalls(ast.NodeTransformer):
    def __init__(self, valid_worksheets=None, valid_dbs=None, var_counter=None):
        self.assignments = []
        # I want to keep track of the number of variables I've created for each function
        # externally.
        self.var_counter = {} if var_counter is None else var_counter

        # These basically the worksheets that the developer has provided.
        if valid_worksheets is None:
            valid_worksheets = []

        if valid_dbs is None:
            valid_dbs = []
        self.valid_worksheets = valid_worksheets
        self.valid_dbs = valid_dbs
        self.valid_functions = valid_worksheets + valid_dbs

    def visit_Call(self, node):
        # Process nested function calls with keyword arguments
        self.generic_visit(node)
        # For args
        logger.debug(f"[+] Entering Call {ast.dump(node)}")
        for i, arg in enumerate(node.args):
            if isinstance(arg, ast.Call):
                if isinstance(arg.func, ast.Name):
                    name = arg.func.id
                elif isinstance(arg.func, ast.Attribute):
                    name = arg.func.value
                if name in self.valid_functions:
                    var_name = self._create_new_variable(name, arg)
                    if name == "Answer":
                        self._handle_db_functions(var_name, node.args[i])

        # For keywords
        for kw in node.keywords:
            if isinstance(kw.value, ast.Call):
                if isinstance(kw.value.func, ast.Name):
                    name = kw.value.func.id
                elif isinstance(kw.value.func, ast.Attribute):
                    name = kw.value.func.value
                if name in self.valid_functions:
                    var_name = self._create_new_variable(kw.value.func.id, kw.value)
                    if name == "Answer":
                        self._handle_db_functions(var_name, kw)
                    else:
                        kw.value = ast.Name(id=var_name, ctx=ast.Load())

        logger.debug(f"[-] Exiting Call {ast.dump(node)}")
        return node

    def visit_Attribute(self, node: Attribute) -> Any:
        self.generic_visit(node)
        logger.debug(f"[+] Entering Attribute {ast.dump(node)}")
        if (
            isinstance(node.value, ast.Call)
            and node.value.func.id in self.valid_functions
        ):
            var_name = self._create_new_variable(node.value.func.id, node.value)
            if node.value.func.id == "Answer":
                self._handle_db_functions(var_name, node.value)
            else:
                node.value = ast.Name(id=var_name, ctx=ast.Load())

        logger.debug(f"[-] Exiting Attribute {ast.dump(node)}")
        return node

    def visit_Expr(self, node: Expr) -> Any:
        self.generic_visit(node)
        logger.debug(f"[+] Entering Expr {ast.dump(node)}")
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in self.valid_functions
        ):
            var_name = self._create_new_variable(node.value.func.id, node.value)
            if node.value.func.id == "Answer":
                self._handle_db_functions(var_name, node.value)
            else:
                node.value = ast.Name(id=var_name, ctx=ast.Load())
        else:
            self.assignments.append(node)
        logger.debug(f"[-] Exiting Expr {ast.dump(node)}")
        return node

    def visit_Assign(self, node: Assign) -> Any:
        self.generic_visit(node)
        logger.debug(f"[+] Entering Assing {ast.dump(node)}")
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in self.valid_functions
        ):
            var_name = self._create_new_variable(node.value.func.id, node.value)
            if node.value.func.id == "Answer":
                self._handle_db_functions(var_name, node)
            else:
                node.value = ast.Name(id=var_name, ctx=ast.Load())

        logger.debug(f"[-] Exiting Assign {ast.dump(node)}")
        return node

    def _generate_var_name(self, name):
        name = camel_to_snake(name)
        name = name.lower()
        if name not in self.var_counter:
            self.var_counter[name] = 0
        else:
            self.var_counter[name] += 1

        if self.var_counter[name] == 0:
            var_name = name
        else:
            var_name = f"{name}_{self.var_counter[name]}"

        return var_name

    def _create_new_variable(self, name, value):
        # Create a new variable name
        var_name = self._generate_var_name(name)

        # Create a new variable and add it to assignments
        new_var = ast.Name(id=var_name, ctx=ast.Store())
        new_assignment = ast.Assign(targets=[new_var], value=value)
        logger.debug(f"[*] Exiting Create New Variable {ast.dump(new_assignment)}")
        self.assignments.append(new_assignment)

        return var_name

    def _handle_db_functions(self, var_name, assignment_node):
        # If the function is a database function, we need to execute it
        # and store the result in a new variable
        # new_var = ast.Name(id=f"{var_name}_result", ctx=ast.Store())
        assignment_node.value = ast.Name(id=f"{var_name}.result", ctx=ast.Load())
        # new_assignment = ast.Assign(
        #     targets=[new_var],
        #     value=ast.Call(
        #         func=ast.Attribute(
        #             value=ast.Name(id=var_name, ctx=ast.Load()),
        #             attr="execute",
        #             ctx=ast.Load(),
        #         ),
        #         args=[],
        #         keywords=[],
        #     ),
        # )
        # self.assignments.append(new_assignment)


class ExtractFunctionCalls(ast.NodeTransformer):
    def __init__(self, valid_worksheets, valid_dbs, var_counter=None):
        self.valid_worksheets = valid_worksheets
        self.valid_dbs = valid_dbs
        self.var_counter = var_counter

    def visit_Expr(self, node: Assign) -> Any:
        finder = FindFunctionCalls(
            self.valid_worksheets, self.valid_dbs, self.var_counter
        )
        finder.visit(node)
        if len(finder.assignments) > 0:
            return finder.assignments
        else:
            return node

    def visit_Assign(self, node: Assign):
        finder = FindFunctionCalls(
            self.valid_worksheets, self.valid_dbs, self.var_counter
        )
        finder.visit(node)
        if len(finder.assignments) > 0:
            return finder.assignments + [node]
        else:
            return node


class GenieValueTransformer(ast.NodeTransformer):
    def __init__(self, funcs, inbuilt_funcs):
        self.funcs = funcs
        self.inbuilt_funcs = inbuilt_funcs

    def visit_Call(self, node):
        # Process the function arguments recursively first
        self.generic_visit(node)

        # Check if function is 'confirm' or 'propose'
        if isinstance(node.func, ast.Name) and node.func.id in self.inbuilt_funcs:
            # Wrap the argument in GenieValue() if the function matches
            for i, arg in enumerate(node.args):
                node.args[i] = ast.Call(
                    func=ast.Name(id="GenieValue", ctx=ast.Load()),
                    args=[arg],
                    keywords=[],
                )
        return node

    def visit_Assign(self, node):
        # Process the value recursively first
        self.generic_visit(node)

        # We're interested in assignments where the value is a Call to BookRestaurant
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in self.funcs
        ):
            for kw in node.value.keywords:
                if not (
                    isinstance(kw.value, ast.Call)
                    and kw.value.func.id in self.inbuilt_funcs
                ):
                    kw.value = ast.Call(
                        func=ast.Name(id="GenieValue", ctx=ast.Load()),
                        args=[kw.value],
                        keywords=[],
                    )
        return node


def camel_to_snake(name):
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


# Parse the code into an AST
def rewrite_code_to_extract_funcs(
    original_code, valid_worksheets, valid_dbs, var_counter=None
):
    # Parse the original code into an AST
    tree = ast.parse(original_code)

    # Initialize the rewriter
    extract_func_rewriter = ExtractFunctionCalls(
        valid_worksheets=valid_worksheets, valid_dbs=valid_dbs, var_counter=var_counter
    )
    # genie_value_transformer = GenieValueTransformer(
    #     funcs=valid_worksheets + valid_dbs, inbuilt_funcs=["confirm", "propose"]
    # )

    # Rewrite the tree
    new_tree = extract_func_rewriter.visit(tree)

    # Convert the AST back to source code
    # new_code = astor.to_source(new_tree)
    # new_code = ast.unparse(ast.fix_missing_locations(new_tree))

    # Transform the values to GenieValue
    # new_tree = ast.fix_missing_locations(new_tree)
    # new_tree = genie_value_transformer.visit(new_tree)
    new_code = ast.unparse(ast.fix_missing_locations(new_tree))

    return new_code.strip()


if __name__ == "__main__":
    assert_with_message(
        rewrite_code_to_extract_funcs(
            """main.courses_to_take = CoursesToTake(course_0_details=Course(course_name='CS 247A', course_num_units=4))""",
            ["CoursesToTake", "Course"],
            [],
        ),
        """course = Course(course_name='CS 247A', course_num_units=4)
courses_to_take = CoursesToTake(course_0_details=course)
main.courses_to_take = courses_to_take""",
    )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             'Tip(tipster=Tipster(full_name="Darmain John", phone_number="650-555-5555"), story_type="campus_news", campus_news_story=CampusNewsStory(location="Lomita Ct near flomo", news_story="I recently witnessed a stabbing on Lomita Ct near flomo"), urgency="high", subject_area="crime_safety", additional_notes="I think it would be a good story for The Daily. Please give me a call at 650-555-5555 when you get a chance.")',
#             ["Tip", "Tipster", "CampusNewsStory"],
#             [],
#         ),
#         'tipster_0 = Tipster(full_name=GenieValue("Darmain John"), phone_number=GenieValue("650-555-5555"))\ncampus_news_story_0 = CampusNewsStory(location=GenieValue("Lomita Ct near flomo"), news_story=GenieValue("I recently witnessed a stabbing on Lomita Ct near flomo"))\ntip_0 = Tip(tipster=GenieValue(tipster_0), story_type=GenieValue("campus_news"), campus_news_story=GenieValue(campus_news_story_0), urgency=GenieValue("high"), subject_area=GenieValue("crime_safety"), additional_notes=GenieValue("I think it would be a good story for The Daily. Please give me a call at 650-555-5555 when you get a chance."))',
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             'Tip(campus_news_story=CampusNewsStory(news_location="near the student graduate housing"))',
#             ["Tip", "CampusNewsStory"],
#             [],
#         ),
#         """campus_news_story_0=CampusNewsStory(news_location=GenieValue('near the student graduate housing'))\ntip_0=Tip(campus_news_story=GenieValue(campus_news_story_0))""",
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """BookRestaurant(restaurant=answer_0.result, date='2022-03-01', time=confirm('19:00'), party_size=2, special_request_info="NA").confirm()""",
#             ["BookRestaurant"],
#             ["RestaurantDB"],
#         ),
#         """book_restaurant_0=BookRestaurant(restaurant=GenieValue(answer_0.result),date=GenieValue('2022-03-01'),time=confirm(GenieValue('19:00')),party_size=GenieValue(2),special_request_info=GenieValue('NA'))\nbook_restaurant_0.confirm()""",
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """UserInfo(user_task='Book Restaurant'); BookRestaurant(restaurant=Answer(query="SELECT * FROM restaurants WHERE 'chinese' = ANY(cuisines) AND answer(reviews, 'does this restaurant serve spicy food?') = 'Yes';",required_params={'restaurants': ['location']}), date="2024-05-05", time="12:00:00", number_of_people=5)""",
#             ["BookRestaurant", "UserInfo", "Answer"],
#             ["RestaurantDB"],
#         ),
#         """user_info_0=UserInfo(user_task=GenieValue('Book Restaurant'))\nanswer_0=Answer(query=GenieValue("SELECT * FROM restaurants WHERE 'chinese' = ANY(cuisines) AND answer(reviews, 'does this restaurant serve spicy food?') = 'Yes';"), required_params=GenieValue({'restaurants': ['location']}))\nbook_restaurant_0=BookRestaurant(restaurant=GenieValue(answer_0.result),date=GenieValue('2024-05-05'),time=GenieValue('12:00:00'),number_of_people=GenieValue(5))""",
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """UserInfo(user_task='Book Restaurant')
# BookRestaurant(restaurant=Answer("SELECT * FROM restaurants WHERE price = 'moderate' ORDER BY rating DESC LIMIT 1;", {'restaurants': ['location']}, ['restaurants']))""",
#             ["BookRestaurant", "UserInfo", "Answer"],
#             [],
#         ),
#         """user_info_0 = UserInfo(user_task=GenieValue('Book Restaurant'))
# answer_0 = Answer("SELECT * FROM restaurants WHERE price = 'moderate' ORDER BY rating DESC LIMIT 1;", {'restaurants': ['location']}, ['restaurants'])
# book_restaurant_0 = BookRestaurant(restaurant=GenieValue(answer_0.result))""",
#     )

#     user_target = """book_restaurant_0.restaurant = Answer("SELECT * FROM restaurants WHERE 'chinese' = ANY(cuisines) AND answer(reviews, 'does this restaurant serve spicy food?') = 'Yes' AND location = 'San Francisco';", {}, ["restaurants"])"""

#     expected_genie_target = """answer_0 = Answer("SELECT * FROM restaurants WHERE 'chinese' = ANY(cuisines) AND answer(reviews, 'does this restaurant serve spicy food?') = 'Yes' AND location = 'San Francisco';", {}, ["restaurants"])
# book_restaurant_0.restaurant = answer_0.result"""

#     assert_with_message(
#         rewrite_code_to_extract_funcs(user_target, ["Answer"], ["Answer"]),
#         expected_genie_target,
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """book_restaurant_0.restaurant = answer_0.result""", ["Answer"], ["Answer"]
#         ),
#         """book_restaurant_0.restaurant = answer_0.result""",
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """UserInfo(user_task='Book Restaurant')
# BookRestaurant(restaurant=Answer("looking for a nice restaurant"))""",
#             ["BookRestaurant", "UserInfo", "Answer"],
#             [],
#         ),
#         """user_info_0 = UserInfo(user_task=GenieValue('Book Restaurant'))
# answer_0 = Answer("looking for a nice restaurant")
# book_restaurant_0 = BookRestaurant(restaurant=GenieValue(answer_0.result))""",
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """book_restauarant_0.restaurant = confirm(answer_0.result[0])""",
#             ["BookRestaurant", "UserInfo", "Answer"],
#             [],
#         ),
#         """book_restauarant_0.restaurant = confirm(GenieValue(answer_0.result[0]))""",
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """book_restauarant_0.date = 'tomorrow'""",
#             ["BookRestaurant", "UserInfo", "Answer"],
#             [],
#         ),
#         """book_restauarant_0.date = GenieValue('tomorrow')""",
#     )

#     assert_with_message(
#         rewrite_code_to_extract_funcs(
#             """from datetime import datetime, timedelta

# # Calculate tomorrow's date from today's date
# tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

# # Set the date for the booking
# book_restaurant_0.date = tomorrow_date""",
#             ["BookRestaurant", "UserInfo", "Answer"],
#             [],
#         ),
#         """from datetime import datetime, timedelta
# tomorrow_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
# book_restaurant_0.date = GenieValue(tomorrow_date)""",
#     )
