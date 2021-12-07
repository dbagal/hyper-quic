import random
import string
import utils
from collections import defaultdict

import mempool
import pacemaker
import safety
import messages
import block_tree
import leader_election
import crypto
import ledger
import syncup

class Main:

    _replica = None
    sync_responses = defaultdict(int)
    start_processing = False


    @staticmethod
    def start():
        sign = ''.join(random.choices(string.ascii_uppercase +
                             string.digits, k = 20))
        
        genesis_qc = messages.QC(
            block_id = "#genesis", 
            block_round = 0, 
            parent_block_id = None, 
            parent_block_round = None, 
            exec_state_id = None, 
            commit_state_id = None, 
            vote_info_hash = crypto.Crypto.hash( 
                                data=(
                                    "#genesis",
                                    0,
                                    None,
                                    None,
                                    None,
                                )
                            ),
            signatures=[sign,]*Main._replica.system_config.num_validators, 
            signers=Main._replica.peers, 
            sender=leader_election.LeaderElection.get_leader(pacemaker.Pacemaker.current_round)
        )

        block_tree.BlockTree.high_qc = genesis_qc
        block_tree.BlockTree.high_commit_qc = genesis_qc

        genesis_block = block_tree.Block(
            payload=[],
            id = "#genesis",
            author = leader_election.LeaderElection.get_leader(0)
        )

        block_tree.BlockTree.add_node(genesis_block)
        Main.process_quorum_certificate(genesis_qc)
       

    @staticmethod
    def process_client_request(client_request):
        """  
        @params:
        - client_request: object of ClientRequest(single_transaction, sender, sender_key)

        @function:
        - dump the transaction in the MemPool module's queue of transactions
        """
        mempool.MemPool.add_client_request(client_request)

        # start processing as soon as first client request arrives
        if not Main.start_processing:
            Main.start_processing = True
            Main.process_new_round(last_tc=None)


    @staticmethod
    def process_quorum_certificate(qc):
        """  
        @function:
        - commit a block for which this qc is qc-of-qc for that block (if any)
        - select the leader for the next round
        - advance to the round one more than the qc round
        """
        block_tree.BlockTree.process_qc(qc)
        leader_election.LeaderElection.update_leaders(qc)
        pacemaker.Pacemaker.advance_round_on_qc(qc)


    @staticmethod
    def process_sync_request(sync_request):
        syncup.SyncUp.process_sync_request(sync_request)

    
    @staticmethod
    def process_sync_response(sync_response):
        syncup.SyncUp.process_sync_response(sync_response)


    @staticmethod
    def process_proposal_msg(proposal_msg):
        """  
        @params:
        - proposal_msg:  object of ProposalMsg(block, last_round_tc_at_leader, last_committed_block_qc_at_leader)

        @function:
        - process the latest qc (latest qc at the leader) attached in the block
        - sync up the committed blocks
        - speculatively execute the block and add it to the block tree
        - elect a leader locally for the next round
        - form a vote on this proposal and send it to the next leader
        """
        # sync up all ancestor blocks in case if any block is missing
        # two levels of sync up viz block sync up and ledger sync up
        # syncup.SyncUp.sync_up_ancestors(proposal_msg.meta_data)

        # move transactions of the block to staging area
        mempool.MemPool.move_to_staging_area(proposal_msg.block.payload)

        # process the high qc
        Main.process_quorum_certificate(proposal_msg.block.high_qc)

        # process this qc so that all replicas which might have been byzantine earlier 
        # can be in sync with the non-byzantine ones on the committed blocks
        Main.process_quorum_certificate(proposal_msg.high_commit_qc)
        
        # advance the round if instead of qc there's a tc that was formed in the last round
        pacemaker.Pacemaker.advance_round_on_tc(proposal_msg.last_tc)

        # if the both the sender and the author of the block in the proposal msg is not the leader, 
        # do not process the proposal msg any further since it is faulty
        current_round  = pacemaker.Pacemaker.current_round
        leader = leader_election.LeaderElection.get_leader(current_round)
        if proposal_msg.block.round != current_round or proposal_msg.sender!=leader or proposal_msg.block.author != leader:
            return 

        # speculatively execute the transactions in the block and add it to the block tree
        block_tree.BlockTree.execute_and_insert(proposal_msg.block)

        # form a vote on the proposal
        vote_msg = safety.Safety.make_vote(
            block = proposal_msg.block, 
            last_tc = proposal_msg.last_tc
        )

        # get the already elected leader (when we processed qc/tc) for the next round and 
        # send the vote msg to that leader
        next_leader = leader_election.LeaderElection.get_leader(current_round + 1)
        utils.log(
            id = Main._replica.replica_id,
            msg = f"Getting the next leader (\n\tnext-leader: {next_leader}\n)"
        )

        if vote_msg is not None:
            Main._replica.send(vote_msg, send_to=next_leader)
            utils.log(
                id = Main._replica.replica_id,
                msg = f"VOTE-MSG sent to next leader (\n\tsent-to-next-leader: {next_leader}, \
                    \n\tblock-id: {vote_msg.block_id}, \n\tblock-round: {vote_msg.block_round}\n)"
            )


    @staticmethod
    def process_timeout_msg(timeout_msg):
        """  
        @function:
        - process the tc attached in the block
        - sync up the committed blocks
        - if a validator is behind, it advances it's round to that for which timeout_msg is sent
        - after coming or being in the round of timeout_msg, timeout the round if you get f+1 timeout_msgs 
        - (and broadcast your own timeout msg)
        - and form a tc upon getting additional f timeout_msgs
        """
        # process the qcs to get in sync
        Main.process_quorum_certificate(timeout_msg.high_qc)
        Main.process_quorum_certificate(timeout_msg.high_commit_qc)

        # if a validator is not in the round for which timeout msgs are sent, it upgrades its round to that of the timeout msg
        pacemaker.Pacemaker.advance_round_on_tc(timeout_msg.last_tc)

        # process the timeout_msg after upgrading (if needed) yourself to that round 
        tc = pacemaker.Pacemaker.process_remote_timeout(timeout_msg)
        if tc is not None:
            # sync up all ancestor blocks in case if any block is missing
            # two levels of sync up viz block sync up and ledger sync up
            #syncup.SyncUp.sync_up_ancestors(timeout_msg.meta_data)

            pacemaker.Pacemaker.advance_round_on_tc(tc)
            Main.process_new_round(tc)
        else:
            utils.log(
                id = Main._replica.replica_id,
                msg = f"TIMEOUT-MSG processed (\n\tfor-round: {timeout_msg.current_round}, \
                    \n\ttimeouts-collected: {pacemaker.Pacemaker.get_num_of_timeouts_collected(timeout_msg.current_round)}\n)"
            )

    
    @staticmethod
    def process_new_round(last_tc):
        """  
        @function:
        - if this validator is the leader, generate a block and propose it
        """
        utils.log(
            id = Main._replica.replica_id,
            msg = f"Processing new round"
        )

        if Main._replica.replica_id == leader_election.LeaderElection.get_leader(pacemaker.Pacemaker.current_round) and \
            not syncup.SyncUp.under_progress:

            utils.log(
                id = Main._replica.replica_id,
                msg = f"New round processed (\n\tleader: self \
                    \n\tpending-client-requests: {mempool.MemPool.get_num_pending_requests()}\
                    \n\tstaged-requests: {mempool.MemPool.get_num_staged_requests()}\n)"
            )
            block = block_tree.BlockTree.generate_block()

            branch = block_tree.BlockTree.get_branch_rounds(block.high_qc.block_round)

            # broadcast the proposal msg with the proposed block and 
            # the branch entailing the proposed block as metadata for block sync up
            Main._replica.broadcast(
                messages.ProposalMsg(
                    block = block, 
                    last_tc = last_tc, 
                    high_commit_qc= block_tree.BlockTree.high_commit_qc,
                    meta_data = messages.MetaData(
                        branch = branch,
                        log_index = ledger.Ledger.log_index,
                        root_round = block_tree.BlockTree.root_round
                    )
                )
            )


    @staticmethod
    def process_vote_msg(vote_msg):
        
        qc = block_tree.BlockTree.process_vote_msg(vote_msg)
        if qc is not None:
            # sync up all ancestor blocks in case if any block is missing
            # two levels of sync up viz block sync up and ledger sync up
            #syncup.SyncUp.sync_up_ancestors(vote_msg.meta_data)

            # if qc is formed at the leader, process the qc, advance the round at leader and broadcast the proposal
            # on receiving this qc in the proposal msg, all validators enter the same round as that of the qc
            Main.process_quorum_certificate(qc)
            Main.process_new_round(last_tc=None)
        else:
            utils.log(
                id = Main._replica.replica_id,
                msg = f"VOTE-MSG processed (\n\tblock-id: {vote_msg.block_id}, \
                    \n\tblock-round: {vote_msg.block_round}, \
                    \n\tvotes-collected: {block_tree.BlockTree.get_number_of_votes_collected(vote_msg)}\n)"
            )