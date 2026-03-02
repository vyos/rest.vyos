def normalize_to_list(value):
    """
    Normalize VyOS REST return values to list.

    Handles:
      dict -> keys
      list -> same
      str  -> [value]
      None -> []
    """
    if isinstance(value, dict):
        return list(value.keys())

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        return [value]

    return []


def normalize_to_dict(value):
    """
    Normalize VyOS REST return values to dict.

    list -> {item: {}}
    str  -> {value: {}}
    dict -> same
    """
    if isinstance(value, dict):
        return value

    if isinstance(value, list):
        return {v: {} for v in value}

    if isinstance(value, str):
        return {value: {}}

    return {}