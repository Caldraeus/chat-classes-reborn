import re

def combine_values(d: dict) -> dict:
    """
    Combines values of a nested dictionary with list values.

    :param dict d: A dictionary with possibly nested lists.
    :return: A dictionary with combined values.
    :rtype: dict
    """
    out = {}
    for key, value in d.items():
        if isinstance(value, list):
            combined_values = {}
            for v in value:
                if isinstance(v, dict):
                    for k, val in v.items():
                        if k in combined_values:
                            combined_values[k].extend(val)
                        else:
                            combined_values[k] = val
                else:
                    if key in combined_values:
                        combined_values[key].append(v)
                    else:
                        combined_values[key] = [v]
            out[key] = combined_values
        else:
            out[key] = value
    return out

def get_params(func_str):
    """
    Extracts the parameters from a string representation of a function signature.

    :param str func_str: A string containing the function signature.
    :return: A list of parameter names extracted from the function signature.
    :rtype: list[str]
    """
    start = func_str.index("(") + 1
    end = func_str.rindex(")")
    params = func_str[start:end]
    return [param.strip() for param in params.split(",")]


def append_or_create(d, key, value):
    """
    Appends a value to a list stored in the given key of a dictionary if the key already exists.
    Creates the key with a new list containing the value if it does not exist.
    Returns a list of values associated with the key.
    """
    if key in d:
        if isinstance(d[key], list):
            d[key].append(value)
        else:
            d[key] = [d[key], value]
    else:
        d[key] = value
    return d[key]

def parse_psv_rfplang(rfplang, target: str = "SELF", existing_list=None):
    """
    Take in an item's RFPLang, parse it's passive effects, and output as a dict, or attach to existing list.
    :param string rfplang:     The RFPLang string.
    :param dict existing_list: The existing list of passive effects, if one exists.
    """
    if existing_list is None:
        out = {}
    else:
        out = existing_list

    props = [item for item in rfplang.split(" && ") if item.startswith("PSV")]

    if target == "SELF":
        props = [
            prop for prop in props if prop.split("::")[-1] == target
            or prop.split("::")[-1] == "WEAPON"
            or prop.split("::")[-1] == "BOTH"
        ]
    else:
        props = [
            prop for prop in props if prop.split("::")[-1] == target
            or prop.split("::")[-1] == "BOTH"
        ]

    for prop in props:
        kwargs = prop.split("::")

        # Determine ability.
        effect = kwargs[1][:int(kwargs[1].index("("))]

        if effect == "TWEAK":
            # TWEAK(damage_type || status_effect || attribute)
            effect_trgt = get_params(kwargs[1])[0]
            effect_mod = kwargs[2]
            effect_mod_word = effect_mod[:effect_mod.index("(")]
            effect_mod_param = get_params(effect_mod)

            append_or_create(out, effect_trgt,
                             {effect_mod_word: effect_mod_param})

        if effect == "AUGMENT":
            # AUGMENT(damage_type || status_effect || attribute)
            effect_trgt = get_params(kwargs[1])[0]
            append_or_create(out, effect_trgt, kwargs[2])

    # Combine values for the same key
    out = combine_values(out)

    return out