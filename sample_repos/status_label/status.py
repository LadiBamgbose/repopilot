from render import render


def display(name: str, state: str) -> str:
    if state == "active":
        return render(name)
    return f"Away: {name}"
