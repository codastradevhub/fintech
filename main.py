import os
import sys
import json
import datetime
from flask import Flask, jsonify, request

try:
    from kiteconnect import KiteConnect
except ImportError:
    os.system('pip install kiteconnect')
    from kiteconnect import KiteConnect

# Load or ask for login credentials
try:
    with open("Login Credentials.json", "r") as f:
        login_credential = json.load(f)
except:
    print("---- Enter your Zerodha Login Credentials ----")
    login_credential = {
        "api_key": str(input("Enter API Key: ")),
        "api_secret": str(input("Enter API Secret: "))
    }
    if input("Press Y to save login credentials (any key to skip): ").upper() == "Y":
        with open("Login Credentials.json", "w") as f:
            json.dump(login_credential, f)
        print("Data Saved...")
    else:
        print("Login cancelled.")
        sys.exit()

# Access token loading or login
access_token_path = f"AccessToken/{datetime.datetime.now().date()}.json"
if os.path.exists(access_token_path):
    with open(access_token_path, "r") as f:
        access_token = json.load(f)
    kite = KiteConnect(api_key=login_credential["api_key"])
    kite.set_access_token(access_token)
else:
    kite = KiteConnect(api_key=login_credential["api_key"])
    print("Login URL:", kite.login_url())
    request_token = input("Enter the request token from URL after login: ")
    try:
        session = kite.generate_session(request_token, api_secret=login_credential["api_secret"])
        access_token = session["access_token"]
        os.makedirs("AccessToken", exist_ok=True)
        with open(access_token_path, "w") as f:
            json.dump(access_token, f)
        kite.set_access_token(access_token)
        print("Login successful.")
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit()

# Start Flask App
app = Flask(__name__)

@app.route('/get_stock_price', methods=['GET'])
def get_stock_price():
    stock_symbol = request.args.get('symbol')
    if not stock_symbol:
        return jsonify({"error": "Missing 'symbol' query param"}), 400

    try:
        instrument = f"NSE:{stock_symbol.upper()}"
        print(f"Fetching stock price for {instrument}...")

        ltp_data = kite.ltp([instrument])
        if instrument in ltp_data:
            return jsonify({
                "symbol": stock_symbol.upper(),
                "last_price": ltp_data[instrument]["last_price"]
            })
        else:
            return jsonify({"error": "Stock not found or invalid symbol"}), 404

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
