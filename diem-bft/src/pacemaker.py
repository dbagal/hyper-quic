import threading
import block_tree
import mempool
import messages
import safety
import utils
import main
from collections import defaultdict

class Pacemaker:

    current_round = 0
    last_tc = None
    pending_timeouts = defaultdict(set)
    timeout_senders = defaultdict(set)
    timer = None


    @staticmethod
    def get_round_timer():
        # return the duration of the timer for each round
        return 4 * main.Main._replica.system_config.transmission_time_delta

    
    @staticmethod
    def start_timer(new_round):
        Pacemaker.stop_current_timer()
        Pacemaker.current_round = new_round

        # start the timer only when you have pending client requests
        if mempool.MemPool.get_num_staged_requests() != 0 or mempool.MemPool.get_num_pending_requests()!=0:
            
            Pacemaker.timer = threading.Timer(
                interval=Pacemaker.get_round_timer(), 
                function=Pacemaker.timeout_local_round
            )
            Pacemaker.timer.start()

            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Round timer started (\n\tround: {new_round}\n)"
            )


    @staticmethod
    def stop_current_timer():
        if Pacemaker.timer != None:
            Pacemaker.timer.cancel()

        # flush collected votes in block tree during previous round
        block_tree.BlockTree.flush_collected_votes()
        

    @staticmethod
    def timeout_local_round():

        Pacemaker.stop_current_timer()

        # Form and broadcast a timeout msg for the current_round once the round timer goes off
        timeout_msg = safety.Safety.make_timeout(
                            current_round = Pacemaker.current_round, 
                            high_qc = block_tree.BlockTree.high_qc, 
                            last_tc = Pacemaker.last_tc
                        )

        if timeout_msg!=None:
            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Local round timed out, timeout msg broadcasted (\
                    \n\ttimed-out-round: {Pacemaker.current_round}\n)"
            )
            main.Main._replica.broadcast(timeout_msg)


    @staticmethod
    def get_num_of_timeouts_collected(r):
        return len(Pacemaker.pending_timeouts[r])


    @staticmethod
    def process_remote_timeout(timeout_msg):
        """  
        @function:
        - on f+1 remote timeout msgs, stop the local timer and broadcast timeout msg to all replicas
        - on 2f+1 remote timeout msgs, form a TC
        """
        utils.log(
            id = main.Main._replica.replica_id, 
            msg = f"Processing remote timeout (\n\tfrom: {timeout_msg.sender},\
                        \n\ttimeout-for-round: {timeout_msg.current_round}\
                        \n\tcurrent-round: {Pacemaker.current_round}\n)"
        )

        # don't act on timeout msgs having round numbers less than its own round
        if timeout_msg.current_round < Pacemaker.current_round:
            return None

        # collect all the timeout msgs and the ids of their signers
        if timeout_msg.sender not in Pacemaker.timeout_senders:
            Pacemaker.timeout_senders[timeout_msg.current_round].add(timeout_msg.sender)
            Pacemaker.pending_timeouts[timeout_msg.current_round].add(timeout_msg)

        # on collection of f+1 timeout msg, timeout local round at this validator
        if len(Pacemaker.pending_timeouts[timeout_msg.current_round]) == main.Main._replica.system_config.num_byzantine + 1:
            Pacemaker.timeout_local_round()

        timeouts = list(Pacemaker.pending_timeouts[timeout_msg.current_round])

        # on collection of 2f+1 timeout msgs, form and return a TC
        if len(Pacemaker.pending_timeouts[timeout_msg.current_round]) == 2*main.Main._replica.system_config.num_byzantine + 1:
            return messages.TC(
                        current_round = timeout_msg.current_round, 
                        high_qc_rounds = [t_msg.high_qc.block_round for t_msg in timeouts], 
                        signatures = [t_msg.signature for t_msg in timeouts],
                        signers=[t_msg.sender for t_msg in timeouts]
                    )

        return None


    @staticmethod
    def advance_round_on_tc(tc):
        """  
        @function:
        - set current round to one more than that in the TC
        """

        # don't advance the round if TC is null or if current validator is already at a higher round
        # i.e the TC is for an older round
        if (tc == None) or (tc.current_round < Pacemaker.current_round):
            return False

        Pacemaker.last_tc = tc

        prev_round = Pacemaker.current_round
        new_round = tc.current_round+1

        if hasattr(main.Main._replica, "playground") and main.Main._replica.playground is not None and \
            hasattr(main.Main._replica.playground, "round_advancement") and \
                callable(getattr(main.Main._replica.playground, "round_advancement")):
                main.Main._replica.playground.round_advancement(Pacemaker.current_round, new_round)

        Pacemaker.start_timer(new_round)
        
        utils.log(
            id = main.Main._replica.replica_id, 
            msg = f"Round advanced on TC (\n\tfrom: {prev_round}, \
                \n\tto: {new_round}\n)"
        )
        return True
        

    @staticmethod
    def advance_round_on_qc(qc):
        """  
        @function:
        - set current round to one more than that in the QC
        """
        # don't advance the round if the QC is for an older round
        if (qc.block_round < Pacemaker.current_round):
            return False

        Pacemaker.last_tc = None

        prev_round = Pacemaker.current_round
        new_round = qc.block_round+1

        if hasattr(main.Main._replica, "playground") and main.Main._replica.playground is not None and \
            hasattr(main.Main._replica.playground, "round_advancement") and \
                callable(getattr(main.Main._replica.playground, "round_advancement")):
                main.Main._replica.playground.round_advancement(Pacemaker.current_round, new_round)

        Pacemaker.start_timer(new_round)
        utils.log(
            id = main.Main._replica.replica_id, 
            msg = f"Round advanced on QC (\n\tfrom: {prev_round}, \
                \n\tto: {new_round}\n)"
        )
        return True
