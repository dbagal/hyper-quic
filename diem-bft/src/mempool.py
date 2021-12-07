from collections import OrderedDict

import utils
import main
import messages


class MemPool:
    
    client_requests = OrderedDict()  # client requests indexed by their ids
    # this is used to get ids of the transactions committed during ledger synced up
    client_request_ids = dict()     # mapping of raw transaction strings to request ids.  
    cached_results = OrderedDict()  # results to client requests indexed by the client_request_ids
    staging_area = OrderedDict()  # temporary buffer to hold transactions till they get committed once they are sent to the block

    @staticmethod
    def get_num_staged_requests():
        return len(MemPool.staging_area)


    @staticmethod
    def get_num_pending_requests():
        return len(MemPool.client_requests)

    
    @staticmethod
    def move_to_staging_area(requests):
        """  
        @function:
        - when a block is formed for the given client requests, these requests are moved to the staging area
        indicating that they are getting processed.
        """
        pushed_requests = []
        for req in requests:
            # clear requests from the pending queue
            if MemPool.client_requests.get(req.id, None) is not None:
                del MemPool.client_requests[req.id]
                del MemPool.client_request_ids[req.transaction]
            
            # move these requests to the staging area
            # now if this replica didn't receive these requests in the first place from the client , 
            # it must have been due to client msgs lost in transit to this replica
            if MemPool.staging_area.get(req.id, None) is None:
                MemPool.staging_area[req.id] = req
                pushed_requests += [req]

        if len(pushed_requests)>0:
            transactions =  utils.formatted_list_string([req.transaction for req in pushed_requests])
            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Pushing transactions to MemPool's staging area (\
                    \n\ttxns: {transactions}\n)"
            )


    @staticmethod
    def move_to_pending_queue(requests):
        """  
        @function:
        - when a branch is pruned from the block tree, all transactions in the branch's blocks 
        are added back to the pending queue to process them again
        """
        for req in requests:
            if MemPool.staging_area.get(req.id, None) is not None:
                del MemPool.staging_area[req.id]
            
            if MemPool.client_requests.get(req.id, None) is None:
                MemPool.client_requests[req.id] = req
                MemPool.client_request_ids[req.transaction] = req.id

        transactions =  utils.formatted_list_string([req.transaction for req in requests])
        utils.log(
            id = main.Main._replica.replica_id, 
            msg = f"Pushing back uncommitted transactions to MemPool's pending queue (\
                \n\ttxns: {transactions}\n)"
        )


    @staticmethod
    def get_transactions():
        """  
        @function:
        - move client requests into staging area 
        - return client requests (containing single transactions) indexed by msg_id
        """
        # get requests which will form a block
        requests = list(MemPool.client_requests.values())

        # move the requests to staging area
        MemPool.move_to_staging_area(requests)

        return requests


    @staticmethod
    def add_client_request(client_request):
        """  
        @function:
        - add the client request to the mempool's queue if its not a retransmission
        - at some point, the block containing this transaction will be formed
        - at some other point, this block will be committed
        - flush all the transactions from MemPool's queue which are included in this block
        - return the ledger_state hash once the block containing the client's transaction is committed
        """

        # add client request to pending queue only if 
        # it is not added before to the pending queue
        # it is not being processed currently (i.e not staged)
        # it is not already processed and cached
        if MemPool.client_requests.get(client_request.id, None) is None and \
            MemPool.staging_area.get(client_request.id, None) is None and \
                MemPool.cached_results.get(client_request.id, None) is None:
            # on new client request add the request to the pool
            MemPool.client_requests[client_request.id] = client_request
            MemPool.client_request_ids[client_request.transaction] = client_request.id

            utils.log(
                id = main.Main._replica.replica_id, 
                msg = f"Transaction added to MemPool (\n\tclient-id: {client_request.sender}),\
                     \n\ttxn: {client_request.transaction}\n)"
            )
            return True
        else:
            #utils.log(
            #    id = main.Main._replica.replica_id, 
            #    msg = f"Retransmission of client request detected (\n\tclient-id: {client_request.sender}, \
            #        \n\ttxn: {client_request.transaction}\n)"
            #)

            # on retransmission of the client request if it was processed earlier and 
            # result is available in the cache, simply send the cached result
            cached_result = MemPool.cached_results.get(client_request.id, None)

            if cached_result is not None:
                utils.log(
                    id = main.Main._replica.replica_id, 
                    msg = f"Cached result returned for the retransmitted request (\n\tclient-id: {client_request.sender}), \
                        \n\ttxn: {client_request.transaction}\n)"
                )
                client_response = messages.ClientResponse(
                                        client_request_id = client_request.id, 
                                        ledger_state_hash = cached_result, 
                                        sender = main.Main._replica.replica_id
                                    )
                main.Main._replica.send(client_response, send_to=client_request.sender)
            
            return False


    @staticmethod
    def add_to_cache(client_request_id, result):
        if len(MemPool.cached_results) > main.Main._replica.system_config.mempool_cache_size:
            oldest_client_request_id = list(MemPool.cached_results)[0]
            del MemPool.cached_results[oldest_client_request_id]
        MemPool.cached_results[client_request_id] = result


    @staticmethod
    def flush_client_request(client_request_id):
        try:
            del MemPool.staging_area[client_request_id]
        except:
            # transaction may not have been received in the first place from the client
            pass

        try:
            req = MemPool.client_requests[client_request_id]
            del MemPool.client_request_ids[req.transaction]
            del MemPool.client_requests[client_request_id]
        except:
            pass