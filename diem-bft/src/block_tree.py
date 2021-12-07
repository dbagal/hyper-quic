import traceback
from collections import defaultdict
import utils
import crypto
import ledger
import messages
import main
import pacemaker
import mempool

class Block:

    def __init__(self, payload, id=None, author=None) -> None:
        self.round = pacemaker.Pacemaker.current_round
        self.payload = payload
        self.high_qc = BlockTree.high_qc
        if author is None: self.author = main.Main._replica.replica_id
        else: self.author = author
        if id is None:
            self.id = crypto.Crypto.hash(
                data = (
                    self.author,
                    self.round,
                    self.payload,
                    self.high_qc
                )
            )
        else:
            self.id = id

        utils.log(
            id = main.Main._replica.replica_id,
            msg = f"Block created (\n{self.log()}\n)"
        )


    def log(self):
        if self.high_qc is None: high_qc_id = None
        else: high_qc_id = self.high_qc.id 
        
        return utils.get_string_representation(
            {
                "id": self.id,
                "author" : self.author,
                "round": self.round,
                "high-qc": high_qc_id,
                "payload": utils.formatted_list_string([payload.transaction for payload in self.payload])
            }
        )


class BlockTree:

    pending_block_tree = dict()  # round -> block mapping
    block_rounds = dict()  # block.id -> round mapping
    pending_votes = defaultdict(set)  # collects similar vote msgs indexed by their ledger-commit-info hash
    high_commit_qc = None   # highest qc which resulted in a commit of some block
    high_qc = None  # highest qc seen so far
    root_round = 0
    sync_responses = defaultdict(dict)
    sync_up_blocks_added = []


    class BlockTreeNode:
        def __init__(self, block):
            self.id = block.id
            self.block = block
            self.parent_round = BlockTree.high_qc.block_round
            self.children_rounds = set()
            BlockTree.block_rounds[block.id] = block.round


    @staticmethod
    def update_root_round(root_round):
        """  
        @function:
        - whenever a block is committed, it becomes the root of the block tree
        - this function updates updates the root_round class variable which keeps a track of the root of the block tree
        """
        BlockTree.root_round = root_round

        # delete all rounds less than the new root_round
        r = root_round-1
        while True:
            try:
                del BlockTree.pending_block_tree[r]
            except:
                break
    

    def get_branch_rounds(block_round):
        """  
        @function:
        - return the branch rounds starting from the root and ending at block_round (including block_round)
        - minimum length of the branch = 1 (root node corresponding to committed block)
        """
        r = block_round
        chain_rounds = [r,]
        while r > BlockTree.root_round:  
            # maintain rounds in the branch starting from the root round
            try:
                # if this validator is falling behind and doesn't have a round in its block tree, 
                # skip the round because other validators will verify if they have any missing rounds 
                # from the rounds that you send
                r = BlockTree.pending_block_tree[r].parent_round 
                # add parent round, only if parent block exists in the block tree
                parent = BlockTree.pending_block_tree[r]
                chain_rounds += [r,]
            except:
                break

        return chain_rounds


    @staticmethod
    def add_missing_block(block_node):
        try:
            block = block_node.block
            parent_round = block.high_qc.block_round

            # add the block in the block tree and update its parent round
            BlockTree.pending_block_tree[block.round] = BlockTree.BlockTreeNode(block)
            BlockTree.pending_block_tree[block.round].parent_round = parent_round

            # update the children round of the parent of this block if any
            if BlockTree.pending_block_tree.get(parent_round, None) is not None:
                BlockTree.pending_block_tree[parent_round].children_rounds.add(block.round)

            """ for r in BlockTree.pending_block_tree.keys():
                bnode = BlockTree.pending_block_tree[r]
                if bnode.parent_round == block.round and block.round!=r:
                    BlockTree.pending_block_tree[block.round].children_rounds.add(r) """

            # move transactions to the staging area once the missing block is added
            mempool.MemPool.move_to_staging_area(block_node.block.payload)

            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Missing Block added to the block tree(\n\tblock-id: {block.id}\
                    \n\tblock-tree:\n{BlockTree.get_block_tree_as_string()})"
            )

            utils.log_block_tree(
                id = main.Main._replica.replica_id, 
                msg = f"Missing Block added (\n\tblock-id: {block.id}\
                    \n\tblock-tree:\n{BlockTree.get_block_tree_as_string()})"
            )
            
        except:
            print(traceback.format_exc())


    @staticmethod
    def add_node(block):
        """  
        @function:
        - fetch the block round from the block 
        - add the block to that round
        - set parent round of the block to the parent_round
        """
        try:
            # new proposals extend the highest certified block known locally to the validator
            parent_round = BlockTree.high_qc.block_round

            BlockTree.pending_block_tree[block.round] = BlockTree.BlockTreeNode(block)

            if BlockTree.pending_block_tree.get(parent_round, None) is not None:
                BlockTree.pending_block_tree[parent_round].children_rounds.add(block.round)

            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Block added to the block tree(\n\tblock-id: {block.id}\n\tblock-tree:\n{BlockTree.get_block_tree_as_string()})"
            )

            utils.log_block_tree(
                id = main.Main._replica.replica_id, 
                msg = f"Block added (\n\tblock-id: {block.id}\n\tblock-tree:\n{BlockTree.get_block_tree_as_string()})"
            )
            
        except:
            print(traceback.format_exc())


    @staticmethod
    def delete_branch(round):
        """  
        @function:
        - given a round, get the branch associated with the block and delete it including the root
        """
        block_node = BlockTree.pending_block_tree.get(round, None)
        if block_node:
            mempool.MemPool.move_to_pending_queue(block_node.block.payload)

            # traverse deep inside the tree and delete all children branches
            children_rounds_to_be_deleted = block_node.children_rounds.difference({round})
            if children_rounds_to_be_deleted:
                for r in children_rounds_to_be_deleted:
                    BlockTree.delete_branch(r)
            
            # delete the root
            del BlockTree.pending_block_tree[round]
            del BlockTree.block_rounds[block_node.block.id]
            return 
        return


    @staticmethod
    def prune(block_id):
        """  
        @function:
        - prune all branches not belonging to block_id
        - make block with block_id as the root
        """
        
        block_round = BlockTree.block_rounds[block_id]

        # get the round numbers forming a chain of blocks starting from this block 
        # all the way upto the root
        r = block_round
        chain_rounds = {r,}
        while r!= BlockTree.root_round:
            try:
                r = BlockTree.pending_block_tree[r].parent_round
                chain_rounds.add(r)
            except:
                pass

        # prune all other branches except the current branch
        for r in chain_rounds:
            if r!=block_round:
                children_branches_to_be_pruned = BlockTree.pending_block_tree[r].children_rounds.difference(chain_rounds)
                for root in children_branches_to_be_pruned:
                    BlockTree.delete_branch(root)

        # remove all ancestor blocks
        for ancestor_round in chain_rounds.difference({block_round}):
            block = BlockTree.pending_block_tree[ancestor_round]
            del BlockTree.block_rounds[block.id]
            del BlockTree.pending_block_tree[ancestor_round]

        # make the current block as the root
        BlockTree.pending_block_tree[block_round].parent = None
        BlockTree.update_root_round(block_round)

        utils.log(
            id = main.Main._replica.replica_id, 
            msg = f"Block tree pruned, new root established (\n\troot-block-id: {BlockTree.pending_block_tree[BlockTree.root_round].id}\
                \n\tblock-tree: \n{BlockTree.get_block_tree_as_string()})"
        )
                    
    
    @staticmethod
    def get_block_tree_as_string():
        tree = ""
        for r, node in BlockTree.pending_block_tree.items():
            txns = [req.transaction for req in node.block.payload]
            payload = utils.formatted_list_string(txns, num_tabs=3)
            tree += f"\t{r}:\tblock-id={node.block.id}\
                \n\t\tparent-round: {node.parent_round}\
                \n\t\tchildren-round: {node.children_rounds}\
                \n\t\tpayload: {payload}\n"
        return tree


    @staticmethod
    def process_qc(qc):
        """  
        @function:
        - commit the state for which this qc is the qc-of-qc
        - update the high_commit_qc to this qc if this qc resulted 
          in a commit of some state for which it was a qc-of-qc
        - update the high_qc to that of this qc
        """

        if qc.commit_state_id != None:

            # commit the blocks only if they are not committed already
            # if blocks are already committed, they are absent in the tree
            # however the latest committed block is at the root
            commit_block_round = BlockTree.block_rounds.get(qc.parent_block_id, None)

            if commit_block_round is not None and commit_block_round!=BlockTree.root_round:
            
                # commit the entire chain of the block for which this qc is the qc-of-qc
                ledger.Ledger.commit(qc.parent_block_id)

                # prune the chain to set this block as the new root
                BlockTree.prune(qc.parent_block_id)

                # even if this qc resulted in a commit of some block, 
                # it is a high_commit_qc at the validator only if its the latest one
                if qc.block_round > BlockTree.high_commit_qc.block_round:
                    BlockTree.high_commit_qc = qc
        
        # this qc will be the high_qc seen at the validator only if it is the latest one
        if qc.block_round > BlockTree.high_qc.block_round:
            BlockTree.high_qc = qc

        
    @staticmethod
    def execute_and_insert(block):
        """  
        @function:
        - speculatively execute the block and add it to the pending tree
        """
        # execute the block
        ledger.Ledger.speculate(block)

        # extend the block tree from the highest qc seen so far locally at the validator
        BlockTree.add_node(block)


    @staticmethod
    def get_number_of_votes_collected(vote_msg):
        vote_idx = crypto.Crypto.hash(data = (vote_msg.commit_state_id, vote_msg.vote_info_hash))
        return len(BlockTree.pending_votes[vote_idx])
    
    
    @staticmethod
    def process_vote_msg(vote_msg):
        """  
        @function:
        - get the high_commit_qc and commit the required block to get in sync 
          with other validators on the committed blocks
        - check the number of similar vote msgs collected for the block
        - form and return a qc if number of similar vote msgs collected are 2f+1
        """
        # commit blocks that are committed at other validators
        # this is usually when a replica was byzantine earlier and 
        # hence behaved arbitrarily thereby not committing the blocks
        if vote_msg.high_commit_qc is not None:
            BlockTree.process_qc(vote_msg.high_commit_qc)

        # keep storing votes received and the senders of those votes for a block
        # all vote msgs with same vote info and ledger commit info will be stored in 
        # pending_votes indexed by the ledger commit info hash
        vote_idx = crypto.Crypto.hash(data = (vote_msg.commit_state_id, vote_msg.vote_info_hash))
        BlockTree.pending_votes[vote_idx].add(vote_msg)

        # as soon as 2f+1 votes are collected, form and return a qc
        if len(BlockTree.pending_votes[vote_idx]) == 2*main.Main._replica.system_config.num_byzantine + 1:
            
            votes = list(BlockTree.pending_votes[vote_idx])
            qc = messages.QC(
                        block_id = vote_msg.block_id, 
                        block_round = vote_msg.block_round, 
                        parent_block_id = vote_msg.parent_block_id, 
                        parent_block_round = vote_msg.parent_block_round, 
                        exec_state_id = vote_msg.exec_state_id, 
                        commit_state_id = vote_msg.commit_state_id, 
                        vote_info_hash=vote_msg.vote_info_hash,
                        signatures = [v_msg.signature for v_msg in votes], 
                        signers = [v_msg.sender for v_msg in votes], 
                        sender = main.Main._replica.replica_id
                    )
            
            return qc
        return None


    @staticmethod
    def generate_block():
        return Block(payload=mempool.MemPool.get_transactions())

    
    @staticmethod
    def flush_collected_votes():
        BlockTree.pending_votes.clear()
