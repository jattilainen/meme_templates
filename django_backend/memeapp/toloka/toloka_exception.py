class TolokaException(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(self.message)
