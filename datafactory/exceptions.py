class MatchDoesntHaveInfo(Exception):
    def __init__(self):
        self.message = f"Match doesn't have the required information."
        super().__init__(self.message)