from shopkit.notifications.templates import order_placed


def render_order_email(name: str) -> str:
    return order_placed(name)
