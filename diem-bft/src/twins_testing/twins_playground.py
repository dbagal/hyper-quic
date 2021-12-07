import sys, random, datetime, string, os, threading
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import playground
import pacemaker
import leader_election
import messages
import crypto
import utils


class TwinsPlayground(playground.NetworkPlayground):

    def __init__(self, node_id, system_config, client_config, testcase, **params) -> None:
        super().__init__(**params)
    
        self.id = node_id
        self.system_config = system_config
        self.client_config = client_config

        for param, val in params.items():
            setattr(self, param, val)
        

        self.num_rounds = testcase["num-rounds"]

        # maintain the leader, msgs to drop, and network partition at every global round
        self.leaders = []
        self.msg_loss_schedule = []
        self.partition_scenarios = []
        
        for i in range(self.num_rounds):
            scenario = testcase[str(i)]
            self.leaders += [scenario["leader"]]
            self.msg_loss_schedule += [[messages.Messages.index[m] for m in scenario["msgs-lost"]]]
            self.partition_scenarios += [[set(partition) for partition in scenario["partition"]]]

        self.local_round = pacemaker.Pacemaker.current_round
        self.global_round = 0
        self.network_partition = self.partition_scenarios[self.global_round]

        # initialise the leader for the zeroth round
        leader_election.LeaderElection.leader[self.global_round] = self.leaders[self.global_round]

        # maintain a set of all faulty nodes and their non-faulty twins
        self.faulty_nodes  = set(testcase["compromised-nodes"])
        self.non_faulty_counterparts = set(testcase["twins"].values())

        # maintain a birdirectional faulty-node <-> non-faulty twin mapping
        self.twin = testcase["twins"]
        self.twin.update({v:k for k,v in testcase["twins"].items()})

        self.nodes = set(testcase["nodes"])

        # generate a mock payload if current validator is one amongst the compromised nodes
        # the compromised node will equivocate by overwriting all truthful 
        # proposal msgs produced by itself with the mock block
        if self.id in self.faulty_nodes:
            self.mock_payload = self.mock_payload_generator()

        # updates to the leader should be made once per round
        # maintain 'leaders_updated_for_round' just to ensure leader updation once per round
        self.leaders_updated_for_round = 0

        # 
        round_listener_thread = threading.Thread(target=self.global_round_listener)
        round_listener_thread.start()


    def round_advancement(self, current_round, next_round):
        """  
        @function:
        - if playground is enabled at the validator, pacemaker notifies the playground 
            of round advancement by invoking this function
        """
        # update local round at the playground, if pacemaker has progressed the system to a future round
        if next_round > current_round:
            self.local_round = current_round

            # notify local round update to the executor using the shared variable between this validator and the executor
            self.round_var.value = self.local_round
            
            utils.log_playground(
                id=self.id,
                msg = f"New round entered locally (\n\tnew-round: {self.local_round}, \
                        \n\tnetwork-partition: {utils.formatted_list_string(self.network_partition)}"
            )

            # if value in the shared variable is greater than the global round that the validator knows of,
            # log the global round update msg
            if self.round_var.value > self.global_round:
                utils.log_playground(
                    id=self.id,
                    msg = f"New round entered globally (\n\tnew-round: {self.round_var.value}, \
                        \n\tnetwork-partition: {utils.formatted_list_string(self.network_partition)}\
                        \n\tleader: {self.leaders[self.global_round]}"
                )


    def global_round_listener(self):
        """  
        @function:
        - keep listening for the global round on the shared variable between the validator and the executor
        """
        while True:

            # update the global round and the network partition for that global round 
            # if executor announces progression to future global round
            if self.round_var.value > self.global_round:
                self.global_round = self.round_var.value % len(self.partition_scenarios)
                self.network_partition = self.partition_scenarios[self.global_round]

            # stop this thread on receiving stop signal
            msg = self.notify_queue.get()
            try:
                if msg["type"] == "stop-signal":
                    break
            except:
                pass


    def mock_payload_generator(self):
        """ 
        @function:
        - get random strings as commands with specified length in config file
        - the transaction has the form => (client_id, timestamp): command
        """
        # get random client requests
        # we don't bother about the signature for the client requests because 
        # client signatures are only verified when they are actually received
        def get_request():
            cmd_len = self.client_config.client_command_length
            cmd = ''.join(random.choices(string.ascii_uppercase + string.digits, k = cmd_len))
            current_ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
            txn = f"({self.id},{current_ts}): {cmd}"
            client = random.choice(self.client_config.client_id_set)
            return  messages.ClientRequest(
                txn = txn, 
                sender = self.twin[self.id], 
                sender_key=self.client_config.client_keys[client][0],
                log=False
            )

        num_commands = random.choice(range(5))
        return [get_request() for _ in range(num_commands)]


    def get_partition_containing(self, nodes):
        """  
        @function:
        - get the partition containing all the nodes specified in 'nodes'
        - if no such partition containing all the nodes is present, return none
        """
        for partition in self.network_partition:
            intersection = set(nodes).intersection(set(partition))
            if len(intersection)==len(set(nodes)):
                return partition
        return None


    def intercept_intra_partition_msg(self, msg, sender, receiver):
        """  
        @function:
        - if the validator is a leader for the current global round, drop the msg according to the msg_loss_schedule
        - to ensure msgs are dropped once, remove the msg from the schedule once dropped
        """
        if self.id == self.leaders[self.global_round]:
            if msg.type in self.msg_loss_schedule[self.global_round]:
                self.msg_loss_schedule[self.global_round].remove(msg.type)
                utils.log_playground(
                    id=self.id,
                    msg = f"Intra-partition {messages.Messages.type[msg.type].upper()} message to {receiver} dropped (\n{msg.log()}\n)"
                )
                return None
        return msg


    def intercept_outgoing_msg(self, msg, sender, receiver):
        """  
        @function:
        - intercepted msgs are processed by this function
        - the msg can be entirely manipulated by this function
        """

        # drop intra-partition msgs according to the schedule in the testcase
        # msg = self.intercept_intra_partition_msg(msg, sender, receiver)

        # if this validator is a compromised node and is sending a proposal msg, 
        # emulate equivocation by replacing the actual block's payload with the mock payload
        if sender in self.faulty_nodes and msg.type==messages.Messages.PROPOSAL_MSG:

            # since proposal msgs are broadcasted, replace every msg's payload 
            # with the mock payload generated during initialisation
            if msg.block.payload != self.mock_payload:
            
                utils.log_playground(
                    id=self.id,
                    msg = f"Modifying PROPOSAL-MSG (\n\t{msg.log()}\n)"
                )

                msg.block.payload = self.mock_payload
                msg.block.id = crypto.Crypto.hash(
                    data = (
                        msg.block.author,
                        msg.block.round,
                        msg.block.payload,
                        msg.block.high_qc
                    )
                )
                msg.sender = self.twin[sender]

                utils.log_playground(
                    id=self.id,
                    msg = f"PROPOSAL-MSG modified (\n\t{msg.log()}\n)"
                )
            
        # drop inter-partition msgs amongst replicas
        if receiver in self.nodes:
            partition = self.get_partition_containing((sender, receiver))
            if partition is not None:
                return msg
            else:
                utils.log_playground(
                    id=self.id,
                    msg = f"Inter-partiton {messages.Messages.type[msg.type].upper()} message to {receiver} dropped (\n{msg.log()}\n)"
                )
        else:
            # don't drop msgs to clients
            return msg

        return None


    def update_leaders(self, qc):
        """  
        @function:
        - when a qc is received, deduce the next round, update the leader for the next round
        """
        next_round = self.global_round + 1

        if next_round > self.leaders_updated_for_round:

            # in case if diembft runs for more rounds than number of partition scenarios, 
            # repeat the partition scenarios
            r = next_round%len(self.partition_scenarios)
            next_leader = self.leaders[r]

            # set appropriate leader at every validator (i.e node/twin) 
            # if configured leader in the testcase is a compromised node
            partition = self.get_partition_containing((self.id,))
            if partition and (next_leader in self.faulty_nodes or next_leader in self.non_faulty_counterparts):
                twin = self.twin[next_leader]
                next_leader = partition.intersection({next_leader, twin}).pop()
                leader_election.LeaderElection.leader[next_round] = next_leader
                utils.log_playground(
                    id=self.id,
                    msg = f"Updating leader as one of the twins (\n\tleader: {next_leader}, \
                        \n\tfor-global-round: {next_round}\n)"
                )

            # set the configured leader in the testcase normally if it is not a compromised node
            elif partition:
                leader_election.LeaderElection.leader[next_round] = next_leader
                utils.log_playground(
                    id=self.id,
                    msg = f"Updating leader as one of the non-compromised nodes (\n\tleader: {next_leader},\
                        \n\tfor-global-round: {next_round}\n)"
                )
            
            self.leaders_updated_for_round = next_round

