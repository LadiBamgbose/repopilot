from policy import price_for


def quote_package(pounds: int, method: str) -> float:
    return price_for(method, pounds)
