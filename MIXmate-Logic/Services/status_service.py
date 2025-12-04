class MixStatus:
    def __init__(self):
        self.current_status = "READY"

    def set_status(self, status):
        self.current_status = status

    def get_status(self):
        return self.current_status
