# THIS CODE IS NOT WORKING AND DIDN'T USE IT


# # option_chain_api.py
# import os
# import json
# from kiteconnect import KiteConnect
# import datetime
# from flask import Blueprint, request, jsonify

# # Create a Flask blueprint
# option_chain_bp = Blueprint('option_chain', __name__)

# # Load login credentials
# with open("Login Credentials.json", "r") as f:
#     login_credential = json.load(f)

# def get_kite_client():
#     with open(f"AccessToken/{datetime.datetime.now().date()}.json", "r") as f:
#         access_token = json.load(f)
#     kite = KiteConnect(api_key=login_credential["api_key"])
#     kite.set_access_token(access_token)
#     return kite

# @option_chain_bp.route('/get_option_chain', methods=['GET'])
# def get_option_chain():
#     symbol = request.args.get('symbol')
#     if not symbol:
#         return jsonify({"error": "Missing 'symbol' query param"}), 400

#     try:
#         kite = get_kite_client()

#         if not os.path.exists("instruments.json"):
#             instruments = kite.instruments()
#             with open("instruments.json", "w") as f:
#                json.dump(instruments, f, indent=2)
#         else:
#             with open("instruments.json", "r") as f:
#                 # instruments = json.load(f)
#                  try:
#                   instruments = json.load(f)
#                  except json.JSONDecodeError:
#                   return jsonify({"error": "instruments.json is corrupted or incomplete"}), 500

#         symbol = symbol.upper()
#         option_chain = [
#             item for item in instruments
#             if item['exchange'] == 'NFO'
#             and item['tradingsymbol'].startswith(symbol)
#             and item['instrument_type'] in ['CE', 'PE']
#             and item['segment'] == 'NFO-OPT'
#         ]

#         if not option_chain:
#             return jsonify({"error": "No option data found for this symbol"}), 404

#         option_chain = sorted(option_chain, key=lambda x: x['strike'])
#         tradingsymbols = [item['tradingsymbol'] for item in option_chain]
#         ltp_data = kite.ltp([f"NFO:{s}" for s in tradingsymbols])

#         result = []
#         for opt in option_chain:
#             key = f"NFO:{opt['tradingsymbol']}"
#             data = ltp_data.get(key, {})
#             result.append({
#                 "strike": opt['strike'],
#                 "expiry": opt['expiry'],
#                 "instrument_type": opt['instrument_type'],
#                 "tradingsymbol": opt['tradingsymbol'],
#                 "last_price": data.get("last_price", "NA"),
#                 "underlying": opt.get("name", symbol)
#             })

#         return jsonify(result[:20])

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


from flask import Blueprint, jsonify, request
from kiteconnect import KiteConnect
import json
import os
import datetime

option_chain_bp = Blueprint('option_chain', __name__)

# Load login credentials
with open("Login Credentials.json", "r") as f:
    login_credential = json.load(f)

# Get authenticated kite client
def get_kite_client():
    try:
        with open(f"AccessToken/{datetime.datetime.now().date()}.json", "r") as f:
            access_token = json.load(f)
        kite = KiteConnect(api_key=login_credential["api_key"])
        kite.set_access_token(access_token)
        return kite
    except Exception as e:
        raise Exception("Failed to get Kite client: " + str(e))

# Endpoint for getting Option Chain (F&O data)
@option_chain_bp.route('/get_option_chain', methods=['GET'])
def get_option_chain():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "Please provide a stock symbol"}), 400

    try:
        kite = get_kite_client()

        # Load instruments list or refresh it
        instruments_file = "instruments.json"
        if not os.path.exists(instruments_file):
            instruments = kite.instruments()
            with open(instruments_file, "w") as f:
                json.dump(instruments, f, indent=2)
        else:
            try:
                with open(instruments_file, "r") as f:
                    instruments = json.load(f)
            except json.JSONDecodeError:
                # Refresh corrupted file
                instruments = kite.instruments()
                with open(instruments_file, "w") as f:
                    json.dump(instruments, f, indent=2)

        # Filter for F&O options (Calls and Puts) on the symbol
        option_chain = [
            ins for ins in instruments
            if ins['segment'] == 'NFO-OPT' and ins['name'] == symbol.upper()
        ]

        if not option_chain:
            return jsonify({"error": f"No option chain found for symbol: {symbol}"}), 404

        return jsonify(option_chain), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
