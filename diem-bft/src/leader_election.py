import random

import ledger
import pacemaker
import utils
import main


class LeaderElection:

    validators = None
    window_size = None
    exclude_size = None
    leader = dict()

    @staticmethod
    def elect_reputation_leader(qc):
        """
        @returns:
        - independently and locally elected leader with the same seed, 
        so that all validators elect the same leader
        @function:
        - get the active validators who are actively voting in the past few rounds.
        - get the leaders of the past few rounds
        - remove the leaders of past few rounds from active validators to ensure fairness
        - pick one leader randomly with the same seed across all validators 
        """
        try:
            # active_validators is the set of all replicas 
            # who voted without fail in the last 'window_size' rounds
            active_validators = set()

            # last_leaders is the set of all leaders for the past 'exclude_size' rounds
            last_leaders = set()

            i=0
            current_qc = qc
            
            # Traverse the committed-blocks chain upwards 
            # Get the active validators and the elected leaders for the past rounds
            while (i < LeaderElection.window_size) or (len(last_leaders) < LeaderElection.exclude_size):
                current_committed_block = ledger.Ledger.committed_blocks_history[current_qc.parent_block_id]
                
                block_leader = current_committed_block.author

                if i < LeaderElection.window_size:
                    active_validators.update(current_qc.signers)

                if len(last_leaders) < LeaderElection.exclude_size:
                    last_leaders.add(block_leader)

                current_qc = current_committed_block.high_qc
                i+=1
            
            # Remove leaders of the past rounds from active_validators to ensure fairness 
            # for all processes to be elected as a leader
            active_validators = active_validators.difference(last_leaders)
            random.seed(qc.block_round)

            return random.choice(sorted(list(active_validators)))
        except:
            return None

    
    @staticmethod
    def get_round_robin_leader(round):
        idx = ((round+1)//2)%len(LeaderElection.validators)
        return sorted(list(LeaderElection.validators))[idx]


    @staticmethod
    def update_leaders(qc):
        """ 
        @function:
        - elect the leader if the QC forms a contiguous chain
        """
        # use custom leader election only if the method is defined in the playground
        if hasattr(main.Main._replica, "playground") and main.Main._replica.playground is not None and \
            hasattr(main.Main._replica.playground, "update_leaders") and \
                callable(getattr(main.Main._replica.playground, "update_leaders")):
            main.Main._replica.playground.update_leaders(qc)
        else:
            # At every QC, elect the leader for the next round
            extended_round = qc.parent_block_round
            qc_round = qc.block_round
            current_round = pacemaker.Pacemaker.current_round

            # Elect leader only if its a continuous chain
            if extended_round != None and (extended_round + 1 == qc_round) and \
                (qc_round + 1 == current_round):

                # remove leaders of old rounds 
                if len(LeaderElection.leader) > main.Main._replica.system_config.round_leader_history:
                    min_round = min(list(LeaderElection.leader.keys()))
                    del LeaderElection.leader[min_round]
                    
                next_leader = LeaderElection.elect_reputation_leader(qc=qc)
                if next_leader is not None:
                    LeaderElection.leader[current_round+1] = next_leader
                    utils.log(
                        id = main.Main._replica.replica_id, 
                        msg = f"Reputation-based Leader Election (\n\tfor-round: {current_round+1}, \
                            \n\tleader-elected: {LeaderElection.leader[current_round+1]}\n)"
                    )
                else:
                    # during the initial phases when there's not enough history to get reputation based leader, 
                    # switch to round robin leader
                    LeaderElection.leader[current_round+1] = LeaderElection.get_round_robin_leader(current_round)
                    utils.log(
                        id = main.Main._replica.replica_id, 
                        msg = f"Round-Robin Leader Election (\n\tfor-round: {current_round+1}, \
                            \n\tleader-elected: {LeaderElection.leader[current_round+1]}\n)"
                    )

            else:
                # If there’s no contiguous chain it means that something went wrong and instead of QC, a TC was formed 
                # because of which continuity was detsroyed. So it would be wrong to elect the validator as a leader 
                # when something failed in its reign.
                LeaderElection.leader[current_round+1] = LeaderElection.get_round_robin_leader(current_round)
                utils.log(
                    id = main.Main._replica.replica_id, 
                    msg = f"Round-Robin Leader Election (\n\tfor-round: {current_round+1}, \
                        \n\tleader-elected: {LeaderElection.leader[current_round+1]}\n)"
                )


    @staticmethod
    def get_leader(round):
        """  
        @function:
        - return the current leader either if it is already elected using reputation based mechanism or else elect it using round-robin
        """
        # For ANY round, if the leader is NOT elected with the reputation scheme, 
        # fall back to the round-robin method
        leader = LeaderElection.leader.get(round, None)

        if leader is None:
            leader = LeaderElection.get_round_robin_leader(round)

        return leader