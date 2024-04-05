# filter_text format:
# * - any text
# substr - any text including the specified substring, case-insensitive
# Substr - any text including the specified substring, case-sensitive

# !substr - any text that does not include the specified substring, case-insensitive
# !Substr - any text that does not include the specified substring, case-sensitive

# "substr" - any text that contains the specified substring, case-insensitive
# "Substr" - any text that contains the specified substring, case-sensitive

# !"substr" - any text that does not contain the specified substring, case-insensitive
# !"substr" - any text that does not contain the specified substring, case-sensitive

# #substr1 & substr2
# #substr1 | substr2
#
# filter string may examples:
#   text = "Returns a list of strings that match any pattern in `include_patterns`"
#   1. filter_text = "strings"
#      check_filter(text, filter_text) returns True (match 'strings')
#
#   2. filter_text = "rings"
#      check_filter(text, filter_text) returns False (exactly word 'rings' not found in text)
#
#   3. filter_text = "*rings"
#      check_filter(text, filter_text) returns True (match 'strings')
#
#   4. filter_text = "!*rings"
#      check_filter(text, filter_text) returns False (match 'strings' but ! defines exclude filter)
#
#   5. filter_text = "Any"
#      check_filter(text, filter_text) returns False (match 'any' but capitalized word 'Any' defines
#      case-sensitive filtering)
#
#   7. filter_text = "list | *patt*"
#      check_filter(text, filter_text) returns True (match 'list', 'pattern', `include_patterns`)
#
#   8. filter_text = "list & tree"
#      check_filter(text, filter_text) returns False (match 'list' but not match 'tree')
#
#   not yet implemented
#   9. filter_text = "<list of strings>"
#      check_filter(text, filter_text) returns True (match 'list of strings')
#
from younotyou import younotyou as flt


def if_case_sensitive(word: str) -> bool:
    """
    Check the specified word begins with a capital letter
    :param word: word to be checked
    :return: True, if the word begins with a capital letter
    """
    cap_word = word.capitalize()
    return cap_word == word


def build_case_sensitive_flag(words: list) -> bool:
    for word in words:
        if if_case_sensitive(word):
            return True

    return False


def check_filter(input_text, filter_text: str) -> bool:
    # print(f"try to find filter: {filter_text} in text: {text}")
    if filter_text == '*':
        return True

    # convert the text under study into an array of words
    strings = input_text.split()

    flags_and = False   # a flag that indicates the presence of AND conditions in the filter line
    flags_or = False    # a flag that indicates the presence of OR conditions in the filter line

    # Let's split the filter string into two arrays. One contains AND conditions, the second - OR conditions
    # and immediately set the flags
    conditions_and = []
    conditions_or = []
    arr = filter_text.split(' | ')
    for item in arr:
        if item.find(' & ') >= 0:
            flags_and = True
            conditions_and.extend(item.split(' & '))
        else:
            flags_or = True
            conditions_or.append(item)

    # prepare two flags to analyze the search result
    and_was_found = False
    or_was_found = False

    # check the AND conditions
    if flags_and:
        # Now let's divide the resulting array into two arrays:
        # - one contains the conditions that should be in the search bar
        # - the second contains conditions that should not be in the search bar
        should_be = []
        should_not_be = []
        for condition in conditions_and:
            if condition.startswith('!'):
                should_not_be.append(condition.removeprefix('!'))
            else:
                should_be.append(condition)
        # If at least one word begins with a capital letter, then the entire search will be case sensitive!
        case_sensitive = build_case_sensitive_flag(conditions_and)
        # check the text for the conditions that should be in the text
        # since the flt function returns a list of found words, and not a sign, you will have to perform
        # this operation for each condition separately and accumulate the result
        and_was_found = True
        for condition in should_be:
            matches = flt(strings, include_patterns=[condition], case_sensitive=case_sensitive)
            and_was_found = and_was_found and len(matches) > 0
        # check the text for conditions that should not be in the text, only if such conditions are specified
        if len(should_not_be):
            matches = flt(strings, include_patterns=should_not_be, case_sensitive=case_sensitive)
            # If at least one word is found, then the AND condition does not match
            and_was_found = and_was_found and len(matches) == 0

    # now, if necessary, check the OR conditions
    if flags_or:
        # Now let's divide the resulting array into two arrays:
        # - one contains the conditions that should be in the search bar
        # - the second contains conditions that should not be in the search bar
        should_be = []
        should_not_be = []
        for condition in conditions_or:
            if condition.startswith('!'):
                should_not_be.append(condition.removeprefix('!'))
            else:
                should_be.append(condition)

        # If at least one word begins with a capital letter, then the entire search will be case sensitive!
        case_sensitive = build_case_sensitive_flag(conditions_and)
        # check the text for the conditions that should be in the text
        matches = flt(strings, include_patterns=should_be, case_sensitive=case_sensitive)
        # if at least one word is found, then the condition is considered fulfilled
        if len(matches) > 0:
            or_was_found = True
    # it's time to check the flags and make a decision
    complied = False
    if flags_and and and_was_found:
        complied = True
    if flags_or:
        complied = complied or or_was_found

    return complied


if __name__ == '__main__':
    text = "Test skip everything functionality like test"
    filter_str = "every* & like"

    print(f" find '{filter_str}' in '{text}'")
    result = check_filter(text, filter_str)
    print(result)
