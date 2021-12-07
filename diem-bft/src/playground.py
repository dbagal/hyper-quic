
class NetworkPlayground():
    
    def __init__(self, **params) -> None:
        for param, val in params.items():
            setattr(self, param, val)


    def configure(self, **params):
        for param, val in params.items():
            setattr(self, param, val)


    def intercept_outgoing_msg(self, msg, sender, receiver):
        return msg


    def intercept_incoming_msg(self, msg, sender, receiver):
        return msg