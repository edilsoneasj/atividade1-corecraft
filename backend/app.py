import os
import string
from flask import Flask, jsonify, request, send_from_directory
from rpc import BitcoinRPC, BitcoinRPCError
from decimal import Decimal, getcontext

getcontext().prec = 8

app = Flask(__name__)
rpc = BitcoinRPC()

# ---------- utilitários ----------

def ok(data):
    return jsonify({"ok": True, "data": data})

def fail(message, details=None, code=400):
    payload = {"ok": False, "error": {"message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return jsonify(payload), code


# ---------- endpoints API ----------

@app.get("/api/mempool/summary")
def api_mempool_summary():
    """
    Node snapshot:
    - getmempoolinfo (size, bytes, usage)
    - getrawmempool () para contar tipos de transações (p2pkh, p2sh, segwit, etc) e fee rates (agrupados por faixas)
    """
    try:
 
        mp = rpc.call("getmempoolinfo")
        mp_raw = rpc.call("getrawmempool", [True])  # verbose=true para obter detalhes das txs na mempool

        count_low_fee = 0
        count_medium_fee = 0
        count_high_fee = 0
        max_fee_rate = -float('inf')
        min_fee_rate = float('inf')
        total_vsize = 0.0
        
        
        
        # min_fee_rate_vsize = float('inf')
        # fee_rate_of_min_fee = 0.0
        # min_fee_vsize = 0.0
        # min_fee_sats = float('inf')

        # # Iterate through key (txid) and value (details) 
        ##or use getmempoolentry para obter detalhes de cada tx individualmente, mas isso pode ser muito pesado para a mempool inteira. O getrawmempool com verbose=true já traz os detalhes necessários.
        for txid, info in mp_raw.items():
            fee_sats = 0.0

            #raw_tx = rpc.call("getrawtransaction", [txid, True])

            fee_data = info.get("fees", {})
            fee_sats = float(fee_data.get("base", 0)) * 100000000  # converte de BTC para satoshis
            vsize = float(info.get("vsize", 1.0))  # evita divisão por zero
            fee_rate = float(fee_sats) / float(vsize)  # sat/vB
            total_vsize += vsize

 
            if fee_rate > max_fee_rate:
                max_fee_rate = fee_rate

            if fee_rate < min_fee_rate:
                min_fee_rate = fee_rate
                #min_fee_rate_vsize = vsize

            # if fee_sats < min_fee_sats:
            #     min_fee_sats = fee_sats
                
            #     fee_rate_of_min_fee = fee_rate
            #     min_fee_vsize = vsize
            

            if fee_rate < 10:
                count_low_fee += 1
            elif fee_rate <= 50:
                count_medium_fee += 1
            else:
                count_high_fee += 1


        data = {

            "mempool": {
                "total_transactions": mp.get("size"), #total de transações na mempool
                "total_size": mp.get("bytes"),
                "total_vsize": int(total_vsize),
                "usage": mp.get("usage"),
                "maxmempool": mp.get("maxmempool"),
                "mempool_min_fee_required": int (mp.get("mempoolminfee") * 100000000), #converte para satoshis
                # The mempoolminfee field in the getmempoolinfo RPC call represents the minimum fee rate
                # (in BTC/kB) required for a transaction to be accepted into the node's mempool. It is 
                # automatically adjusted to prioritize higher-fee transactions if the mempool exceeds 
                # the maxmempool size.
                #"mempoolmaxfee": mp.get("mempoolmaxfee"),
                "mempool_max_fee_rate": max_fee_rate,
                "mempool_min_fee_rate": min_fee_rate,
                "mempool_avg_fee_by_tx_count": (mp.get("total_fee") * 100000000) / mp.get("size") if mp.get("size") > 0 else 0,
                "mempool_avg_fee_by_bytes": (mp.get("total_fee") * 100000000) / mp.get("bytes") if mp.get("bytes") > 0 else 0,
                # "min_fee_rate_vsize": min_fee_rate_vsize,
                # "fee_rate_of_min_fee": fee_rate_of_min_fee,
                # "min_fee_vsize": min_fee_vsize,
                # "min_fee_sats": min_fee_sats,
            },
            "mempool_txs": {
                "total": len(mp_raw), #
                # "by_type": {
                #     "p2pkh": 0,
                #     "p2sh": 0,
                #     "p2wpkh": 0,
                #     "p2wsh": 0,
                #     "other": 0,
                # },
                "fee_distribution": {
                    "low_fee": count_low_fee,
                    "medium_fee": count_medium_fee,
                    "high_fee": count_high_fee,
                }
            }
        }
        return ok(data)
    except BitcoinRPCError as e:
        return fail("Falha ao consultar estado do node via RPC.", details=str(e), code=502)
    

@app.get("/api/blockchain/lag")
def api_blockchain_lag():
    """
    Consulta o "atraso" do node em relação à melhor cadeia conhecida.
    Usa getblockchaininfo (blocks vs headers) para estimar o lag.
    """
    try:
        bc = rpc.call("getblockchaininfo")
        blocks = bc.get("blocks", 0)
        headers = bc.get("headers", 0)
        lag = headers - blocks

        data = {
            "blocks": blocks,
            "headers": headers,
            "lag": lag,
        }


        return ok(data)
    except BitcoinRPCError as e:
        return fail("Falha ao consultar estado do node via RPC.", details=str(e), code=502)



@app.get("/api/node")
def api_node():
    """
    Node snapshot:
    - getblockchaininfo (chain, blocks, headers, difficulty, bestblockhash)
    - getmempoolinfo (size, bytes, usage)
    - getnetworkinfo (subversion, connections)
    """
    try:
        bc = rpc.call("getblockchaininfo")
        mp = rpc.call("getmempoolinfo")
        nw = rpc.call("getnetworkinfo")

        data = {
            "chain": bc.get("chain"),
            "blocks": bc.get("blocks"),
            "headers": bc.get("headers"),
            "difficulty": bc.get("difficulty"),
            "bestblockhash": bc.get("bestblockhash"),
            "mempool": {
                "txcount": mp.get("size"),
                "bytes": mp.get("bytes"),
                "usage": mp.get("usage"),
                "maxmempool": mp.get("maxmempool"),
                "mempoolminfee": mp.get("mempoolminfee"),
            },
            "network": {
                "subversion": nw.get("subversion"),
                "connections": nw.get("connections"),
                "version": nw.get("version"),
            }
        }
        return ok(data)
    except BitcoinRPCError as e:
        return fail("Falha ao consultar estado do node via RPC.", details=str(e), code=502)


@app.get("/api/blocks/recent")
def api_blocks_recent():
    """
    Lista N blocos recentes com estatísticas simples.
    Usa:
      - getblockcount
      - getblockhash(height)
      - getblockheader(hash)  (leve)
      - getblockstats(hash)   (stats úteis)
    """
    n = int(request.args.get("n", 10))
    n = max(1, min(n, 25))  # limite didático

    try:
        tip = rpc.call("getblockcount")
        blocks = []
        for h in range(tip, max(tip - n, -1), -1):
            bh = rpc.call("getblockhash", [h])
            header = rpc.call("getblockheader", [bh])
            stats = rpc.call("getblockstats", [bh])

            blocks.append({
                "height": h,
                "hash": bh,
                "time": header.get("time"),
                "mediantime": header.get("mediantime"),
                "txs": stats.get("txs"),
                "totalfee": stats.get("totalfee"),
                "avgfee": stats.get("avgfee"),
                "feerate_percentiles": stats.get("feerate_percentiles"),
                "avgfeerate": stats.get("avgfeerate"),
                "avg_tx_size": stats.get("avgtxsize"),
                "total_size": stats.get("total_size"),
            })

        return ok({"tip": tip, "items": blocks})
    except BitcoinRPCError as e:
        return fail("Falha ao consultar blocos recentes via RPC.", details=str(e), code=502)


@app.get("/api/block/<blockhash>")
def api_block(blockhash):
    """
    Resumo de um bloco por hash.
    Usa getblock(hash, verbosity=1) para evitar payload gigante.
    """
    try:
        blk = rpc.call("getblock", [blockhash, 1])

        data = {
            "hash": blk.get("hash"),
            "height": blk.get("height"),
            "confirmations": blk.get("confirmations"),
            "time": blk.get("time"),
            "nTx": blk.get("nTx"),
            "size": blk.get("size"),
            "weight": blk.get("weight"),
            "version": blk.get("version"),
            "previousblockhash": blk.get("previousblockhash"),
            "nextblockhash": blk.get("nextblockhash"),
            "tx": blk.get("tx")[:20],  # mostra só 20 txids por segurança/UX
        }
        return ok(data)
    except BitcoinRPCError as e:
        return fail("Falha ao consultar bloco.", details=str(e), code=502)


@app.get("/api/tx/<txid>")
def api_tx(txid):
    """
    Consulta uma transação por txid.

    Importante (conceito de integração real):
    - getrawtransaction (verbose=1) só funciona se:
      a) tx estiver na mempool OU
      b) tx estiver na wallet OU
      c) node foi iniciado com txindex=1 (indexação completa)
    """
    try:
        tx = rpc.call("getrawtransaction", [txid, True])
        data = {
            "txid": tx.get("txid"),
            "hash": tx.get("hash"),
            "version": tx.get("version"),
            "size": tx.get("size"),
            "vsize": tx.get("vsize"),
            "weight": tx.get("weight"),
            "locktime": tx.get("locktime"),
            "vin": tx.get("vin"),
            "vout": tx.get("vout"),
            "confirmations": tx.get("confirmations"),  # pode não existir
            "blockhash": tx.get("blockhash"),
            "time": tx.get("time"),
            "blocktime": tx.get("blocktime"),
        }
        return ok(data)
    except BitcoinRPCError as e:
        return fail(
            "Falha ao consultar tx. Dica: isso exige txindex=1, ou a tx precisa estar na mempool/wallet.",
            details=str(e),
            code=502
        )


# ---------- servir frontend (opcional) ----------
# Vamos servir o frontend por Flask para facilitar (um único comando pra rodar tudo).
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.get("/app.js")
def frontend_js():
    return send_from_directory(FRONTEND_DIR, "app.js")

@app.get("/styles.css")
def frontend_css():
    return send_from_directory(FRONTEND_DIR, "styles.css")


if __name__ == "__main__":
    # Dica: debug=True só em ambiente local
    app.run(host="127.0.0.1", port=8080, debug=True)

