VERSION='release/1.1.1-rc.1'
# Pick a genesis file for your network in ./genesis-files.md
GENESIS='mainnet-109331-pruned-mpt.g'
# snap or full
SYNCMODE=full

make

# Download the genesis file
# Note: In a case of an upgrade from a previous node version,
# downloading new genesis file is not necessary. Skip this step and omit --genesis flag
wget https://download.fantom.network/$GENESIS

# Start a read-only node to join the selected network
# Substitute amount of available RAM for best performance
# --genesis flag is mandatory for first launch and optional otherwise
nohup ./build/opera --genesis $GENESIS --syncmode $SYNCMODE --cache 4000