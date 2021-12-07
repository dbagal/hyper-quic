import threading
import time

class Timer(threading.Thread):

    def __init__(self, interval, function, **params):
        super().__init__()
        self.interval = interval
        self.function = function
        self.pause_flag = False
        self.cancel_flag = False
        
        try:
            self.args = params["args"]
        except KeyError:
            self.args = ()


    def pause(self):
        self.pause_flag = True
        return time.time() - self.start_time


    def resume(self):
        self.pause_flag = False
        return time.time() - self.start_time


    def cancel(self):
        self.cancel_flag = True
        return time.time() - self.start_time


    def run(self):
        self.start_time = time.time()

        # run timer while it is not cancelled
        while not self.cancel_flag:
            if not self.pause_flag and time.time() - self.start_time  >= self.interval:
                self.function(*self.args)
                break
        
            

if __name__ == "__main__":
    def test(a,b):
        print("DONE", a,b)
        
    s = time.time()
    t = Timer(2, test, args=(1,2))
    t.start()


    #time.sleep(1)
    #x = t.pause()
    #print(f"Time elapsed on pause: {x}")


    #time.sleep(2)
    #t.resume()
    #print(f"Time elapsed on resume: {x}")

    #time.sleep(1)
    #x = t.cancel()
    #print(f"Time elapsed on cancel: {x}")


    #time.sleep(20)