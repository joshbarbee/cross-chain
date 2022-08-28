# BEFORE RUNNING

1. If you do not want to provide your bsc and eth API keys each time you run the program,
create a .env file that contains the bscApiKey and ethApiKey environment variables.

2. Install Pipenv to manage the virtual environment. 

3. Pipenv install the dependencies: "pipenv install"


# Running 
1. To run a sample test, run "pipenv run dev" *this requires apiKeys to be set in .env

# Steps:
Currently, we only analyze over a range of blocks, specified by the -bs and -br launch options.
We are also only using one bridge, so analysis is only done on that bridge

In main.py:
- We load in all of the command line arguments. The supported args currently are
    ``` 
    - tx or transaction: the hash to scan for
    - bk or bscKey : the API key used for the BSCSCan api
    - ek or ethKey : the API key used for the etherescan API
    - c or chains : the chains to analyze over
    - db or database : the database name to use for the mongodb api
    ```
- We create a MongoFetcher object for each chain from the 
- We then initialize ContractStores for all of the chains that we are using. A ContractStore
  wraps an Etherscan API into a set of 3 functions:
  ```
  - get_contract(address) -> Contract : returns a Contract object from local memory or the *Scan APIs
  - get_block_timestamp(block) -> int : returns the timestamp a block was created
  - get_closest_block(timestamp) -> int: returns the closest block to a certain timestamp
  ```

- We then initialize the Bridge object, constructing it with the following arguments:
  ```
  Bridges(ethstore, bscstore, polystore, filepath, ethfetcher, bscfetcher, polyfetcher)
  ```

- Then, we load the transaction on the source chain and any potential possible transfers on the destination
  chain, via bridges.load_transactions(args.transaction)

- We then link our transaction to any potential transactions via bridges.link_transaction()

In bridge.py:
- We have an enum corresponding to the chains we support. The enum also has additional helper methods to resolve
  strings into enums, and vice-versa

- The Endpoint class is a single instance of a bridge on a chain. 
     It is initialized with the following arguments:
     ```
        chain : the chain the contract originates from
        address : the address of the contract
        db : the MongoFetcher instance that is used to pull tx info from MongoDB
        store : the ContractStore instance used to load contract data
        dest_funcs, src_funcs, dest_events, src_events : strings from the json
        input file describing the bridge
     ```

     The load_src_transaction(tx) function loads a single transaction from a transaction hash into a
     Transaction object. It then determines whether the transaction interacts with the outbound functions
     of that contract. If it does, the variable self.outbound_tx is set to the Transaction object

     get_src_transaction_chain gets the Chain object representation of the chain where the transaction 
     originated on.

     load_dest_transactions(start_block, end_block, amount) loads in all transactions matching an inbound
     function signature within the specified block range, saving into the self.dest_tx array

     get_src_token_transfers will return a Pandas dataframe consisting of any transaction transfer information
     from the src chain
     The columns are: ['srcHash', 'srcSender', 'srcReceiver', 'srcTokenAddr', 'chainId', 'srcValue']

     get_dest_token_transfers will return a Pandas dataframe consisting of any transaction transfer information
     from the destination chain
     The columns are: ['destHash', 'destSender', 'destReceiver', 'destTokenAddr', 'chainId', 'destValue', 'srcReceiver']

     verify_dest_token_transfers will go through all current transactions' token transfers on the destination chain. It will then verify that there is indeed a token transfer from the expected address. If not,
     the transaction is added to the self.invalid_tx array
    
- The Bridge class
