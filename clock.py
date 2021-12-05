import threading
import time

class GlobalClock(threading.Thread):

    def __init__(self):
        super().__init__()
        self.time = 0
        self.reset_at = 3600000 # reset clock after every 1 hour 
        self.events = dict()


    def subscribe(self, delta, callback, args):
        # delta should not exceed self.reset_at
        time = (self.time + delta)%self.reset_at
        self.events[time] = (callback, args)


    def run(self):
        while True:
            self.time = (self.time + 1)%self.reset_at
            if self.time in self.events:
                callback = self.events[self.time][0]
                args = self.events[self.time][1]
                del self.events[self.time]
                callback(args)

            time.sleep(0.001)


if __name__ == "__main__":
    clock = GlobalClock()
    clock.start()

    def callback(id):
        print(f"Event {id} fired")
        time.sleep(6)
        print(f"Event {id} completed")

    delta = 200
    print(f"Event subcription (\n\tcurrent-time: {clock.time}, \n\ttimeout-at: {(clock.time + delta)%clock.reset_at}, \n\tdelta: {delta}\n)")
    clock.subscribe(delta, callback, 1)
    

    time.sleep(2)

    delta = 300
    print(f"Event subcription (\n\tcurrent-time: {clock.time}, \n\ttimeout-at: {(clock.time + delta)%clock.reset_at}, \n\tdelta: {delta}\n)")
    clock.subscribe(delta, callback, 2)

        
