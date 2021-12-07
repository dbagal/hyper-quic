import multiprocessing, os, json, sys, datetime, threading, shutil
import time, random
from collections import defaultdict

current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import config
import twins_playground
import client_playground
from replica import Replica
from client import Client
import utils
import crypto


class TwinsExecutor:

    def __init__(self) -> None:

        self.system_config = config.SystemConfig()
        self.client_config = config.ClientConfig()

        self.setup()

        twins_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(twins_dir))
        fname = os.path.join(parent_dir, "logs", "twins", "executor.log")
        if not os.path.exists(os.path.dirname(fname)): os.makedirs(os.path.dirname(fname))
        utils.setup_logger("executor", fname)
        

    def setup(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))

        ledger_folder_path = os.path.join(root_dir, "ledger")
        logs_folder_path = os.path.join(root_dir, "logs")

        shutil.rmtree(ledger_folder_path)
        shutil.rmtree(logs_folder_path)
        
        if not os.path.exists(ledger_folder_path): os.makedirs(ledger_folder_path)
        if not os.path.exists(logs_folder_path): os.makedirs(logs_folder_path)


    def spawn_replicas(self, rid, keys, playground):
        replica = Replica(rid, keys, playground=playground)
        replica.start_processing()


    def spawn_clients(self, cid, keys, playground):
        client = Client(cid, keys, playground=playground)
        client.start_processing()


    def track_rounds(self, num_rounds, test_case_timer):
        """  
        @function:
        - keep track of the global notion of the round
        - stop the thread after num_rounds number of global rounds are done
        - a global round is assumed to be entered by all processes, once leader enters the round
        """
        highest_round = self.global_round
        replicas = {r:i for i,r in enumerate(self.system_config.replica_id_set)}

        while True:
            # check if the leader has entered the new round 
            i = replicas[self.leaders[self.global_round]]
            r = self.replica_rounds[i].value

            # if leader has entered a new round, announce it as a global round
            if r>highest_round:
                self.global_round = r
                highest_round = r
                print(f"Global round entered: {self.global_round}")

            for i in range(self.system_config.num_validators):     
                self.replica_rounds[i].value = self.global_round

            # stop this thread after configured number of rounds or if all requests have been already committed
            # or if testcase timer is up
            if self.global_round >= (num_rounds-1) or \
                len(self.requests) == self.num_cmds or self.time_up:
                test_case_timer.cancel()
                break 


    def execute_testcase(self, testcase, num):
        """  
        @function:
        - emulate BFT protocol according to the testcase and check for safety and liveness violations
        """

        self.time_up = False

        def timeout_testcase():
            self.time_up = True

        utils.log_executor(
            msg = f"################################################################################\
            \n                               TEST-CASE {num} \
            \n################################################################################"
        )

        delta = self.system_config.transmission_time_delta
        self.num_rounds = testcase["num-rounds"]

        # start a timer for the testcase after which it should force exit
        test_case_timer = threading.Timer(
            interval = int(delta*4*self.num_rounds), 
            function=timeout_testcase
        )
        test_case_timer.start()

        print(f"\nExecuting testcase {num} ...\n")

        self.global_round = 0

        # maintain a shared-variable between executor and every process which maintains the local round the process currently is in
        self.replica_rounds = [multiprocessing.Value('i', 0) for _ in range(self.system_config.num_validators)]
        
        faulty_nodes  = set(testcase["compromised-nodes"])

        # maintain a birdirectional faulty-node <-> non-faulty twin mapping
        twin = testcase["twins"]
        twin.update({v:k for k,v in testcase["twins"].items()})

        replica_id_set = self.system_config.replica_id_set
        client_id_set = self.client_config.client_id_set

        # get the list of leaders from the testcase to update the leader at every validator for every global round 
        self.leaders = []
        for i in range(self.num_rounds):
            scenario = testcase[str(i)]
            self.leaders += [scenario["leader"]]

        replicas = []

        manager = multiprocessing.Manager()

        # common notification queue used for unidirectional communication from executor to all the validators
        # this queue is used to send a stop signal to all replicas once all client responses have been received
        self.replica_notify_queue = manager.Queue()

        # common notification queue used for unidirectional communication from all clients to the executor
        # whenever client gets f+1 responses for a request, it notifies the executor
        # when all requests for all clients are responded to, executor shuts down the entire system
        self.client_notify_queue = manager.Queue()

        for i in range(self.system_config.num_validators):
            rid = replica_id_set[i]

            # give faulty node the same private key as its twin, so that it can equivocate
            if rid in faulty_nodes:
                private_key = self.system_config.replica_keys[twin[rid]][0]
            else:
                private_key = self.system_config.replica_keys[rid][0]
            
            keys = {
                "private-key":private_key,
                "public-keys":{
                    # public keys of all validators
                    **{
                        r:k[1] for r,k in self.system_config.replica_keys.items() 
                    },
                    # public keys of all clients
                    **{
                        r:k[1] for r,k in self.client_config.client_keys.items()
                    }
                }
            }
            # initialise custom twins-playground built on top of playground functionality provided by the BFT protocol
            # twins playground at each replica intercepts all msgs and drops/processes them according to the policies 
            # specified in the testcase
            playground = twins_playground.TwinsPlayground(
                node_id=rid,
                testcase=testcase,
                system_config=self.system_config,
                client_config= self.client_config, 
                round_var = self.replica_rounds[i],
                notify_queue = self.replica_notify_queue
            )
            
            r = multiprocessing.Process(target=self.spawn_replicas, args=(rid, keys, playground))
            replicas += [r]
            r.start()
        
        print("All replicas up!")

        # maintain client request-response metadata as and when clients receive responses to their requests
        self.requests = []
        self.num_cmds = self.client_config.num_clients * self.client_config.num_commands_to_be_sent

        # start a thread that tracks local rounds at all validators, deduced the global round, 
        # and announces it to all validators
        track_rounds_thread = threading.Thread(target=self.track_rounds, args=((testcase["num-rounds"], test_case_timer)) )
        track_rounds_thread.start()
        
        # allow some time for the replicas to setup
        # if you don't do so, the state required for some replicas will not be initialised and 
        # the BFT system will throw exceptions
        time.sleep(2)

        clients = []
        for i in range(self.client_config.num_clients):
            cid = client_id_set[i]
            keys = {
                "private-key":self.client_config.client_keys[cid][0],
                "public-keys":{
                    r:k[1] for r,k in self.system_config.replica_keys.items() 
                }
            }
            # initialise custom client playground built on top of the playground functionality provided
            # by the BFT system
            # client playground intercepts all msgs to and from the client and notifies executor about the responses
            # that the client has received for the requests sent
            playground = client_playground.ClientPlayground(
                node_id=cid,
                client_config= self.client_config,
                notify_queue=self.client_notify_queue
            )

            c = multiprocessing.Process(target=self.spawn_clients, args=(cid, keys, playground))
            clients += [c]
            c.start()

        print("All clients up!\n")

        # stop the BFT system if either all requests are responsded to or 
        # if number of rounds exceed the configured number of rounds in the testcase
        while True:
            
            try:
                self.requests += [self.client_notify_queue.get(timeout=1)]
            except:
                pass

            if len(self.requests) == self.num_cmds or self.time_up or \
                self.global_round >= (testcase["num-rounds"]-1):

                test_case_timer.cancel()
                
                # send a stop signal to all replicas
                for i in range(self.system_config.num_validators):
                    self.replica_notify_queue.put({
                        "type":"stop-signal"
                    })
                break
        
        for node in replicas+clients:
            node.terminate()

        self.check_liveness()
        self.check_safety()

        print("\nTestcase executed successfully!\n")


    def check_safety(self):
        """  
        @function:
        - checks the number of consistent ledgers by comparing their hashes
        """
        twins_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(os.path.dirname(twins_dir))

        ledger_folder = os.path.join(parent_dir, "ledger")
        ledger_files = [fname for fname in os.listdir(ledger_folder) if fname.endswith(".txt")]

        if len(ledger_files) > 0:
            ledger_hashes = defaultdict(int)
            ledgers = dict()

            for fname in ledger_files:
                path = os.path.join(ledger_folder, fname)
                with open(path, "r") as fp:
                    ledger = fp.read()

                ledger_hash = crypto.Crypto.hash(ledger)
                ledger_hashes[ledger_hash] += 1
                ledgers[ledger_hash] = ledger

            # safety property is satisfied only if there are 2f+1 consistent ledgers
            is_safe = False
            num_consistent_ledgers = max(ledger_hashes.values())
            consistent_ledger_idx = max(ledger_hashes, key=ledger_hashes.get)
            if num_consistent_ledgers >= 2*self.system_config.num_byzantine+1:
                ledger = ledgers[consistent_ledger_idx]

                ledger = [l for l in ledger.split("\n") if len(l)>0]
                if len(ledger)==len(set(ledger)):
                    is_safe = True

            utils.log_executor(
                msg = f"Safety verification (\n\tnum-consistent-ledgers: {num_consistent_ledgers}, \n\tis-safe: {is_safe}\n)"
            )
        else:
            utils.log_executor(
                msg = f"Empty ledgers, safety cannot be verified"
            )


    def check_liveness(self):
        """  
        @function:
        - for each response received at the client and forwarded to the executor (via notify_queue),
            find the response time
        - if the response time for a request is below 7*delta, then liveness is ensured, else not
        
        @note:
        - not all requests will have liveness ensured
        - this is because we are running the system only for a configured number of rounds, 
            so some requests which arrive late may not get committed before the configured number of rounds
        - while determining liveness, the timestamp of the original request sent is considered and not that of the retransmitted request
        """
        if len(self.requests)==0:
            num_requests = self.client_config.num_commands_to_be_sent * self.client_config.num_clients
            utils.log_executor(
                msg = f"Liveness violation (\n\tnum-requests-sent: {num_requests}, \n\tnum-responses: 0\n)"
            )
            return

        liveness_time_bound = 7*self.system_config.transmission_time_delta
        for req in self.requests:
            sent_ts = datetime.datetime.strptime(req["ts"], "%m-%d-%Y::%H:%M:%S.%f") 
            rcvd_ts = datetime.datetime.strptime(req["response-ts"], "%m-%d-%Y::%H:%M:%S.%f")
            t_delta = (rcvd_ts - sent_ts).total_seconds() 
            req["response-time"] = str(t_delta) + " secs"
            req["liveness-maintained"] = (t_delta <= liveness_time_bound)

            utils.log_executor(
                msg = f"Liveness verification (\n{utils.get_string_representation(req)}\n)"
            )


    def run(self):
        """  
        @function:
        - get each testcase from 'test_cases.json' and execute it
        """
        current_dir = os.path.dirname(os.path.realpath(__file__))
        testcases_file_path = os.path.join(current_dir, "test_cases.json")

        with open(testcases_file_path, "r") as fp:
            testcases = json.load(fp)

        #testcase = testcases[f"test-case-0"]
        #self.execute_testcase(testcase, num=0)
        
        num = 0
        nums = set()

        num_testcases_to_run = 5

        while len(nums)!=num_testcases_to_run:
            test_case_num = random.choice(list(range(0, testcases["num-testcases"])))
            nums.add(test_case_num)

        for num in nums:
            try:
                testcase = testcases[f"test-case-{num}"]
            except KeyError:
                break

            self.execute_testcase(testcase, num)
        

if __name__=="__main__":
    executor = TwinsExecutor()
    executor.run()