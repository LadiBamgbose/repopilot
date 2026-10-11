from formatting import format_member


def message(name: str, status: str) -> str:
    if status == "new":
        return format_member(name)
    return f"Hello again, {name}."
