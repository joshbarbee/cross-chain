## Notes / To Do:

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

Please see the individual functions described for a more detailed explanation of functionality, 
parameters, etc. The current flow of the program is documented below:

In main.py:
- We load in all of the command line arguments. The supported args currently are
    ``` 
    - tx or transaction: the hash to scan for
    - bk or bscKey : the API key used for the BSCSCan api
    - ek or ethKey : the API key used for the etherescan API
    - c or chains : the chains to analyze over
    - db or database : the database name to use for the mongodb api
    ```
- We create a MongoFetcher object for each chain passed from the arguments
- We then initialize ContractStores for all of the chains that we are using. A ContractStore
  wraps an Etherscan API into a set of 3 functions:
  - When creating a ContractStore, we pass it a BaseContractScanner (or it's derivates) as one of its arguments. The ContractStore uses the ContractScanner object (defined in scanwrapper.py) to pull information from the *Scan APIs as needed, such as getting Contract objects or the existence of a transaction

- We then initialize the Bridge object, constructing it with the following arguments:
  ```
  Bridges(ethstore, bscstore, polystore, filepath, ethfetcher, bscfetcher, polyfetcher)
  ```
  - The Bridges class will call the self.__load_bridges function to load the bridge information from the provided input file
    - __load_bridges will then create a Bridge object for each bridge in the input file. Note that a Bridge object is not one bridge contract on one chain, but a collection of multiple bridge instances across multiple supported chains.
      - The Bridge class constructor will call the __load_endpoints function to load in an Endpoint object, corresponding to an instance of a bridge on a particular chain. Each endpoint object is collected into the self.bridges variable within the Bridge class

- Then, we load the transaction on the source chain and any potential possible transfers on the destination
  chain, via bridges.load_transactions(args.transaction)
  - First we determine the chain that the transaction hash originated from
  - This will invoke Bridge.load_transaction() on each Bridge object that we have. *This can be optimized
    - Bridge.load_transaction will load the transaction information from MongoDB initially on the source chain, via Endpoint.load_src_transaction
      - load_src_transaction will query the MongoDB collection for the source chain for a transaction matching the provided transaction hash.
      - It will then determine if the transaction interacts with the smart contract at one of the outbound functions (send/sendNative) via Transaction.contains_function
    - From the block number of the source transaction and the chain ID of the destination chain (provided via get_src_transaction_chain) we then determine the relative block number on the destination chain via Bridge.get_relative_chain_block
      - get_relative_chain block uses the ContractStore and the *Scan APIs to determine, based on a block number on a source chain, the source chain, and the destination chain, the block number of the closest time-wise block creation on the destination chain
    - We then invoke the Endpoint.load_dest_transactions function, loading in potential linked transactions on the destination chain
      - load_dest_transactions will load in potential transactions based on the relative block number. It then queries the MongoDB database for all transactions within a range of the relative block number and adds the transaction to the self.dest_txs list if the Relay / inbound function for the bridge is interacted with

- We then link our transaction to any potential transactions via bridges.link_transaction()
  - bridges.link_transaction invokes the link_transactions function on each Bridge object
    - bridge.link_transactions invokes Bridge.link_token_transfers()
      - Bridge.link_token_transfers will go through each endpoint that we have for the bridge and invoke the Endpoint.get_src/dest_token_transfer on each. It then joins each source and destination transaction on the destReceiever parameter and the destination chain ID
        - get_src_token_transfer will invoke the Transaction.get_token_transfer function to load the token transfer event from the source transaction, then return a dataframe consisting of the found information.
          - get_token_transfer will go through each transfer contained within the transaction and return the information from the first transfer that was ERC20/721
        - get_src_token_transfer currently hardcodes a lot of logic for loading the token transfer info from the function call
      - Bridge.find_invalid_transfer_amt will go through all existing linked transactions and reduce to the set of transactions where the destination receiver received a token of amount less than the amount send on the source chain. Any transactions not matching the criteria are saved to self.invalid_tx

- We then output the information from the linked transactions via Bridges.output_transaction
  - This writes the linked transaction information calculated in link_transactions to stdout, or a file path if specified.
