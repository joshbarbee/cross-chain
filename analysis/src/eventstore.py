from contract import Event


class EventStore():
    """
        Manages references to the same event, so that we
        can decode similar events
    """

    def __init__(self) -> None:
        self.events: dict[str, list[str, Event]] = {}

    def get_event(self, event: Eve) -> Event | None:
        return self.events
