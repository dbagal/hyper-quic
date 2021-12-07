import block_tree
import messages
import main
import pacemaker
import utils
import ledger
import crypto

class Safety:
    
    private_key = None
    public_keys = dict()
    highest_vote_round = 0
    high_qc_round = 0


    @staticmethod
    def safe_to_extend(block_round, qc_round, last_tc):
        """  
        @params:
        - block_round:  round of the block in the proposal msg
        - qc_round:     round of the highest QC (not the previous one, because previously TC was formed)
        - last_tc:      TC at the leader of the proposed block at the last round

        @function:
        - all the ancestors of a particular branch are committed once we find the QC-of-QC for a block in the branch
        - sometimes QC-of-QC cannot be formed because there can be TCs in between
        - after a committed block at round r, all nodes will set their latest_qc rounds to atleast (>=) r
        - leader should extend the qc only if its qc round is greater than or equal to all high_qc rounds at the other nodes i.e
          qc_round >= max(last_tc.high_qc_rounds)
        """
        return (last_tc.current_round + 1 == block_round) and \
            qc_round >= max(last_tc.high_qc_rounds)


    @staticmethod
    def safe_to_vote(block_round, qc_round, tc):
        """ 
        @params:
        - block_round:  round of the block in the proposal msg
        - qc_round:     round of the highest QC seen so far
        - tc:           TC (if formed, else null) at the leader of the proposed block at the last round

        @function:
        - it is safe to vote a proposal only if it is well formed i.e it contains either a qc or a tc
        - if there's a tc that is formed, the leader extends the chain from the highest 
          of all high_qc_rounds at all validators
        """

        # Voting should be in monotonically increasing rounds
        if block_round <= max(Safety.highest_vote_round, qc_round):
            return False
        
        # qc must preceed a block or 
        # if there's a tc, the leader should extend the qc with round >= all latest_qc_rounds at the validators
        # this check is for ensuring that a msg is well formed i.e it mandatorily contains either a qc or a tc 
        return (qc_round + 1 == block_round) or Safety.safe_to_extend(block_round, qc_round, tc)


    @staticmethod
    def safe_to_timeout(current_round, qc_round, last_tc):
        """  
        @params:
        - current_round:    current round at the node
        - qc_round:         round of the highest qc
        - last_tc:    TC of the last round (if formed else null)

        @function:
        - check if there's a qc/tc that resulted the validator to enter the current_round
        - at current_round, since no progress is observed (i.e no QC or TC is formed), the current_round is then safe to timeout
        """
        # don't timeout in an older round
        if (qc_round < Safety.high_qc_round) or \
            current_round <= max(Safety.highest_vote_round-1, qc_round):
            return False
        return (qc_round+1 == current_round) or (last_tc.current_round+1 == current_round)


    @staticmethod
    def determine_commit_state(block_round, qc):
        """  
        @params:
        - block_round:  round of the block in the proposal msg
        - qc:           round of the qc attached to the block in the proposal msg

        @function:
        - if block_round is a continuous extension of qc, then you're expecting the block certified by this qc to be committed 
        when a QC will be formed for this particular block
        """
        if qc.block_round + 1 == block_round and qc.block_id!="#genesis":
            return qc.block_id  # assumed ledger state id to be same as block_id in this implementation
        return None


    @staticmethod
    def valid_signatures(high_qc, last_tc):
        """  
        @function:
        - check if signatures in high_qc and last_tc are from actually signed by the valid signers
        """

        valid_last_tc = True
        valid_high_qc = True

        if last_tc!=None:
            
            for signature, signer, high_qc_round in zip(last_tc.signatures, last_tc.signers, last_tc.high_qc_rounds):
                calculated_hash = crypto.Crypto.hash(
                    data = (
                        last_tc.current_round,
                        high_qc_round
                    )
                )
                hashed_data_received = crypto.Crypto.verify(signature, Safety.public_keys[signer])
                if hashed_data_received != calculated_hash:
                    valid_last_tc = False
                    break

        calculated_hash = crypto.Crypto.hash(
            data=(
                high_qc.commit_state_id,
                high_qc.vote_info_hash
            )
        )

        for signature, signer in zip(high_qc.signatures, high_qc.signers):
                hashed_data_received = crypto.Crypto.verify(signature, Safety.public_keys[signer])
                if hashed_data_received != calculated_hash:
                    valid_high_qc = False
                    break
        
        if not valid_high_qc:
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"Invalid high_qc (\n{high_qc.log()}\n)"
            )

        if not valid_last_tc:
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"Invalid last_tc (\n{last_tc.log()}\n)"
            )

        return valid_last_tc and valid_high_qc


    @staticmethod
    def make_vote(block, last_tc):
        """  
        @params:
        - block:            block attached in the proposal msg for which the validator needs to make a vote for
        - last_tc:    tc if it is formed in the last round, else null

        @function:
        - check the well-formedness of the proposal, only then make a vote for it
        """
        # Block contains the latest QC that the leader has seen so far
        # if TC was formed in the last round, qc_round won't be consecutive to the round of the block to which it is attached
        high_qc_round = block.high_qc.block_round
        if last_tc is None: last_tc_id = None
        else: last_tc_id = last_tc.id
        
        utils.log(
            id = main.Main._replica.replica_id,
            msg = f"Checking if safe to vote (\n\tblock-round: {block.round}, \
                \n\thigh-qc-round: {high_qc_round}\n\tlast-tc: {last_tc_id} \n)"
        )

        if Safety.safe_to_vote(block.round, high_qc_round, last_tc):
            
            utils.log(
                id = main.Main._replica.replica_id,
                msg = f"Safe to vote check satisfied (\n\tblock-round: {block.round}, \
                    \n\thigh-qc-round: {high_qc_round}\n\tlast-tc: {last_tc_id} \n)"
            )

            Safety.high_qc_round = max(Safety.high_qc_round, high_qc_round)
            Safety.highest_vote_round = max(Safety.highest_vote_round, block.round)

            if block.high_qc.block_id == "#genesis": high_commit_qc = None
            else: high_commit_qc = block_tree.BlockTree.high_commit_qc

            branch = block_tree.BlockTree.get_branch_rounds(block.high_qc.block_round)
            
            return messages.VoteMsg(
                block_id = block.id, 
                block_round = block.round, 
                parent_block_id = block.high_qc.block_id, 
                parent_block_round = block.high_qc.block_round, 
                exec_state_id = block.id, 
                commit_state_id = Safety.determine_commit_state(block.round, block.high_qc), 
                high_commit_qc = high_commit_qc,
                sender = main.Main._replica.replica_id,
                meta_data = messages.MetaData(
                    branch = branch,
                    log_index = ledger.Ledger.log_index,
                    root_round = block_tree.BlockTree.root_round
                )
            )

        return None


    @staticmethod
    def make_timeout(current_round, high_qc, last_tc):
        """  
        @params:
        - current_round:    ongoing round's number 
        - high_qc:          highest qc at this validator
        - last_tc:          tc (if formed else null) in the last round     
        """
        
        if Safety.safe_to_timeout(
                current_round=current_round, 
                qc_round=high_qc.block_round, 
                last_tc=last_tc
            ):

            # Stop voting for current round, because it's about to be timed out
            Safety.highest_vote_round = max(Safety.highest_vote_round, current_round)
            branch = block_tree.BlockTree.get_branch_rounds(high_qc.block_round)

            return messages.TimeoutMsg(
                current_round = pacemaker.Pacemaker.current_round,
                high_qc = block_tree.BlockTree.high_qc,
                last_tc = pacemaker.Pacemaker.last_tc,
                high_commit_qc = block_tree.BlockTree.high_commit_qc,
                sender = main.Main._replica.replica_id,
                meta_data = messages.MetaData(
                    branch = branch,
                    log_index = ledger.Ledger.log_index,
                    root_round = block_tree.BlockTree.root_round
                )
            )

        return None