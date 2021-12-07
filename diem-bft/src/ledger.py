from collections import OrderedDict, defaultdict

import block_tree
import utils
import crypto
import messages
import mempool
import main
import syncup

class Ledger:
    
    pending_states = dict()
    committed_blocks_history = OrderedDict()
    log_index = 0
    commit_hbq = []

    @staticmethod
    def speculate(block):
        """  
        @function:
        - execute the block
        """
        utils.log(
            id = main.Main._replica.replica_id, 
            msg = f"Block executed (\n\texec-state-id: {block.id}\n)"
        )
        
        return block.id


    @staticmethod
    def get_log_chunk(from_log_index):
        """  
        @function:
        - return the subset of the log starting from 'from_log_index' to 'to_log_index'
        """
        try:
            with open(main.Main._replica.system_config.ledger_paths[main.Main._replica.replica_id], "r") as fp:
                ledger_state = fp.read().split("\n")
            if from_log_index < Ledger.log_index:
                return [ cmd for cmd in ledger_state[from_log_index:] if len(cmd)>0]
        except:
            # if current validator itself is not up-to-date with the log chunk that is desired, return []
            pass
        return []


    @staticmethod
    def pending_state(block_id):
        block_round = block_tree.BlockTree.block_rounds[block_id]
        try:
            state_block = block_tree.BlockTree.pending_block_tree[block_round].block
            return state_block
        except KeyError:
            utils.log(
                    id = main.Main._replica.replica_id, 
                    msg = f"Pending state not found (\n\tblock-id: {block_id}, \
                        \n\tblock-round: {block_round} \
                        \n\tblock-tree:\n{block_tree.BlockTree.get_block_tree_as_string()}\n)"
                )
            raise KeyError


    @staticmethod
    def write_to_log(cmd):

        # commit the state
        with open(main.Main._replica.system_config.ledger_paths[main.Main._replica.replica_id], "a+") as fp:
            fp.write(cmd+"\n")

        Ledger.log_index += 1

        # calculate the ledger state hash
        with open(main.Main._replica.system_config.ledger_paths[main.Main._replica.replica_id], "r") as fp:
            ledger_state = fp.read()
        ledger_state_hash = crypto.Crypto.hash(ledger_state)

        client_request_id = mempool.MemPool.client_request_ids.get(cmd, None)
        if client_request_id is not None:

            utils.log(
                    id = main.Main._replica.replica_id,
                    msg = f"Syncing up ledger, command written (\n\tcmd: {cmd}\n)"
                )

            # add results to cache to return cached results in case client retransmits the request
            mempool.MemPool.add_to_cache(
                client_request_id= client_request_id,
                result=ledger_state_hash
            )

            # send result of the transaction back to the client
            main.Main._replica.send(
                messages.ClientResponse(
                        client_request_id = client_request_id, 
                        ledger_state_hash = ledger_state_hash, 
                        sender = main.Main._replica.replica_id
                    ), 
                send_to=mempool.MemPool.client_requests[client_request_id].sender
            )

            # flush out transactions from Mempool once they are committed
            # transactions are wiped out from the memory only when they are committed
            mempool.MemPool.flush_client_request(client_request_id)
            
    
    @staticmethod
    def commit(block_id):
        """  
        @function:
        - commit all blocks (i.e store the results in the persistent storage) 
          starting from the root round (lowest round) till block_round, including block_round
        - calculate the hash of the persistent ledger
        - for every transaction in all the committed blocks, find the client who requested that transaction
        - send result (in this case - ledger state hash) back to the client and flush this transaction from mempool
        """
        def _commit(block):

            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Block in the chain committed (\n\tcommitted-block-id: {block.id}\
                    \n\tblock-tree: \n{block_tree.BlockTree.get_block_tree_as_string()} )"
            )

            Ledger.log_index += len(block.payload)
            
            # commit the state
            with open(main.Main._replica.system_config.ledger_paths[main.Main._replica.replica_id], "a+") as fp:
                for client_request in block.payload:
                    fp.write(str(client_request.transaction)+"\n")
                
            # calculate the ledger state hash
            with open(main.Main._replica.system_config.ledger_paths[main.Main._replica.replica_id], "r") as fp:
                ledger_state = fp.read()
            ledger_state_hash = crypto.Crypto.hash(ledger_state)

            for client_request in block.payload:
                # add results to cache to return cached results in case client retransmits the request
                mempool.MemPool.add_to_cache(
                    client_request_id= client_request.id,
                    result=ledger_state_hash
                )
                # flush out transactions from Mempool once they are committed
                # transactions are wiped out from the memory only when they are committed
                mempool.MemPool.flush_client_request(client_request.id)
                
                # send result of the transaction back to the client
                main.Main._replica.send(
                    messages.ClientResponse(
                            client_request_id = client_request.id, 
                            ledger_state_hash = ledger_state_hash, 
                            sender = main.Main._replica.replica_id
                        ), 
                    send_to=client_request.sender
                )

        # store the last few committed blocks as this is required for the reputation based leader election scheme
        if len(Ledger.committed_blocks_history) > main.Main._replica.system_config.committed_block_history:
            oldest_block_id = list(Ledger.committed_blocks_history)[0]
            del Ledger.committed_blocks_history[oldest_block_id]
        Ledger.committed_blocks_history[block_id] = Ledger.pending_state(block_id)
        
        # get the round associated with the block
        block_round = block_tree.BlockTree.block_rounds[block_id]
        
        # commit all blocks in the chain upwards
        r = block_round
        chain_rounds = [r,]
        while r > (block_tree.BlockTree.root_round+1):
            r = block_tree.BlockTree.pending_block_tree[r].parent_round
            try:
                parent = block_tree.BlockTree.pending_block_tree[r]
                chain_rounds = [r] + chain_rounds
            except:
                break
        
        if not syncup.SyncUp.under_progress:
            
            # if sync up is complete, commit all blocks which were held back because of the syncing up of ledger
            for block in Ledger.commit_hbq:
                _commit(block)
                utils.log(
                    id = main.Main._replica.replica_id,
                    msg = f"Held back block committed (\n\t{block.log()}\n)"
                )
            Ledger.commit_hbq.clear()

            # commit the entire branch of the block
            for rnd in chain_rounds:
                try:
                    block_id = block_tree.BlockTree.pending_block_tree[rnd].id
                    block = Ledger.pending_state(block_id)
                    _commit(block)

                except KeyError:
                    # for missing rounds, just continue
                    # it is not necessary that all numbers between lowest round and the block round 
                    # will be there in this particular validator's block tree
                    continue
        else:

            # if sync up is going on, hold back the commits for some time until syncup is complete
            for rnd in chain_rounds:
                try:
                    block_id = block_tree.BlockTree.pending_block_tree[rnd].id
                    block = Ledger.pending_state(block_id)
                    Ledger.commit_hbq += [block]
                    utils.log(
                        id = main.Main._replica.replica_id,
                        msg = f"Adding block to hold-back-queue to commit later (\n\t{block.log()}\n)"
                    )
                except KeyError:
                    # for missing rounds, just continue
                    # it is not necessary that all numbers between lowest round and the block round 
                    # will be there in this particular validator's block tree
                    continue


        

        
        
            
