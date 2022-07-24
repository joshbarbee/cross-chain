#BEFORE RUNNING

1. If you do not want to provide your bsc and eth API keys each time you run the program,
create a .env file that contains the bscApiKey and ethApiKey environment variables.

2. Install Pipenv to manage the virtual environment. 

3. Pipenv install the dependencies: "pipenv install"


#Running 
1. To run a sample test, run "pipenv run dev-bsc" or "pipenv run dev-eth" *this requires apiKeys to be set in .env

#Modifiying
Current output not what you want? Here's a list of all functions, maybe one does what you want it to do?
src/main.py: loads in configurations and outputs the tx info, as well as interacted contracts currently
src/contract.py:
- Contract:get_func_signatures - load the function signatures for a contract after initialzation
- Contract class (view source code for more info about properties)
- Function class (view source code for more info about accessible properties)
- Event class (view source code for more info about accessible properties)
src/transaction.py:
- Call class (view source for more info about properties)
- Call:set_contract - assigns a contract object to a call object
- Transaction class (view source for more info about properties)
- Transaction:interacted_functions: get all of CALL/CALLCODE/etc contract objects that the function interacted with that are verified.