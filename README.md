# atividade1-corecraft

README - edilsoneasj  
  
  make sure to export the ambient variable for the bitcoin core node,
  WITHOUT the type of network (mainnet, testnet, regtest) in the variable name
  example: 
  export BTC_DATADIR="/home/user/BitcoinCorecraft/codigos/Aula4Semana1"

run btc node  
run: python3 backend/app.py

http://127.0.0.1:8080/
http://127.0.0.1:8080/api/mempool/summary
http://127.0.0.1:8080/api/blockchain/lag





bitcoin.conf used in this project:
signet=1
fallbackfee=0.0001
[signet]
port=58445
rpcbind=127.0.0.1
rpcallowip=127.0.0.1
rpcport=58443
