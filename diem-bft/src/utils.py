import datetime
import random
import os
import logging
import hashlib
import main

def get_transaction_components(txn):
    # (c2@localhost:8022:8023,2021-11-24 10:20:09.970391): 14BZ3MVP8O
    client_id = txn[txn.find("(")+1 : txn.find(",")]
    ts = txn[txn.find(",")+1 : txn.find(")")]
    cmd = txn.split(":")[-1].strip(" ")
    return client_id, ts, cmd


def get_string_representation(content_dict):
    string = "\t--------------------\n"
    for key, val in content_dict.items():
        string+= f"\t {key}: {val}\n"
    string += "\t--------------------"
    return string


def formatted_list_string(list, num_tabs=2):
    string = "[\n"
    for elem in list:
        string += "\t"*num_tabs+str(elem)+",\n"
    string+= "\t"*(num_tabs-1)+" ]"
    return string


def get_id():
    # 2021-26-21::23:26:1634873217
    ts = datetime.datetime.now().strftime("%Y-%M-%d::%H:%M:%s")
    random_num = str(random.random()*1000000)
    id = hashlib.sha1((ts+random_num).encode()).hexdigest()
    return id


def log(id, msg):
    process_name = id.split("@")[0]
    logger = logging.getLogger(f"{process_name}")
    current_ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
    logger.info(current_ts+"\n"+msg+"\n")


def log_block_tree(id, msg):
    process_name = id.split("@")[0]
    logger = logging.getLogger(f"{process_name}-block-tree")
    current_ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
    logger.info(current_ts+"\n"+msg+"\n")


def log_playground(id, msg):
    process_name = id.split("@")[0]
    logger = logging.getLogger(f"{process_name}-twins")
    current_ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
    logger.info(current_ts+"\n"+msg+"\n")


def log_executor(msg):
    logger = logging.getLogger(f"executor")
    current_ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
    logger.info(current_ts+"\n"+msg+"\n")


def setup_logger(logger_name, log_file, level=logging.ERROR):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s : %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    l.setLevel(level)
    l.addHandler(fileHandler)  


    

