# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import os, sys, json, datetime
# from kiteconnect import KiteConnect

# # Load credentials
# CREDS_FILE = "Login Credentials.json"
# TOKEN_DIR = "AccessToken"

# try:
#     with open(CREDS_FILE, "r") as f:
#         login_credential = json.load(f)
# except FileNotFoundError:
#     raise RuntimeError(f"Credentials file '{CREDS_FILE}' not found. Please create it with your API key and secret.")

# # Initialize KiteConnect
# kite = KiteConnect(api_key=login_credential["api_key"])

# # Load or generate access token
# today_str = str(datetime.datetime.now().date())
# access_token_path = os.path.join(TOKEN_DIR, f"{today_str}.json")

# if os.path.exists(access_token_path):
#     with open(access_token_path, "r") as f:
#         access_token = json.load(f)
# else:
#     raise RuntimeError(
#         "Access token not found for today. Please run the login flow to generate a fresh token."
#     )

# kite.set_access_token(access_token)

# # FastAPI app
# app = FastAPI(title="KiteConnect Stock API")

# class StockResponse(BaseModel):
#     exchange: str
#     tradingsymbol: str
#     last_price: float
#     timestamp: datetime.datetime

# @app.get("/stock/{exchange}/{symbol}", response_model=StockResponse)
# def get_stock_price(exchange: str, symbol: str):
#     """
#     Get the last traded price (LTP) for a specific stock symbol on a given exchange.
#     """
#     instrument = f"{exchange}:{symbol.upper()}"
#     try:
#         ltp_data = kite.ltp(instrument)
#         data = ltp_data.get(instrument)
#         if data is None:
#             raise HTTPException(status_code=404, detail="Instrument not found")

#         return StockResponse(
#             exchange=exchange.upper(),
#             tradingsymbol=symbol.upper(),
#             last_price=data["last_price"],
#             timestamp=datetime.datetime.now()
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)



from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, sys, datetime
import json
from kiteconnect import KiteConnect

# Load credentials
CREDS_FILE = "Login Credentials.json"
TOKEN_DIR = "AccessToken"

try:
    with open(CREDS_FILE, "r") as f:
        login_credential = json.load(f)
        
except FileNotFoundError:
    raise RuntimeError(f"Credentials file '{CREDS_FILE}' not found. Please create it with your API key and secret.")

# Initialize KiteConnect
kite = KiteConnect(api_key=login_credential["api_key"])

# Load or generate access token
today_str = str(datetime.datetime.now().date())
access_token_path = os.path.join(TOKEN_DIR, f"{today_str}.json")



if os.path.exists(access_token_path):
    with open(access_token_path, "r") as f:
        access_token = f.read().strip()  # ✅ Read raw string and strip whitespaces
else:
    raise RuntimeError(
        "Access token not found for today. Please run the login flow to generate a fresh token."
    )

kite.set_access_token(access_token)  # ✅ Now set correctly

# FastAPI app
app = FastAPI(title="KiteConnect Stock API")

class StockResponse(BaseModel):
    exchange: str
    tradingsymbol: str
    last_price: float
    timestamp: datetime.datetime

@app.get("/stock/{exchange}/{symbol}", response_model=StockResponse)
def get_stock_price(exchange: str, symbol: str):
    """
    Get the last traded price (LTP) for a specific stock symbol on a given exchange.
    """
    instrument = f"{exchange}:{symbol.upper()}"
    try:
        ltp_data = kite.ltp(instrument)
        data = ltp_data.get(instrument)
        if data is None:
            raise HTTPException(status_code=404, detail="Instrument not found")

        return StockResponse(
            exchange=exchange.upper(),
            tradingsymbol=symbol.upper(),
            last_price=data["last_price"],
            timestamp=datetime.datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
