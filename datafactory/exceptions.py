class MatchDoesntHaveInfo(Exception):
    def __init__(self):
        self.message = f"Match doesn't have the required information."
        super().__init__(self.message)
        
class InvalidMatchInput(Exception):
    def __init__(self):
        self.message = f"The input given is not valid. Must be the json data of the match or an array with league name (str) and match id (int), in that order."
        super().__init__(self.message)