import os
import sys
import copy
import time
import threading
import numpy as np
import pandas as pd
import xlwings as xw
import mibian
from datetime import datetime, timedelta
from kiteconnect import KiteConnect
from dateutil import parser as date_parser
# from py_vollib.black_scholes.implied_volatility import implied_volatility
# from py_vollib.black_scholes.greeks.analytical import delta, gamma, rho, theta, vega


# Setup KiteConnect API
print("----Option Chain----")
api_key = input("Enter Kite API Key: ")
access_token = input("Enter Kite Access Token: ")

kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

try:
    kite.margins()
except Exception:
    print("Login Failed!!!!")
    sys.exit()

# Create Excel File if Not Exists
excel_file = "TA Python.xlsx"
if not os.path.exists(excel_file):
    try:
        wb = xw.Book()
        wb.sheets.add("OptionChain")
        wb.save(excel_file)
        wb.close()
    except Exception as e:
        print(f"Error Creating Excel File: {e}")
        sys.exit()

wb = xw.Book(excel_file)
oc = wb.sheets("OptionChain")
oc.range("a:b").clear_contents()
oc.range("d6:e20").clear_contents()
oc.range("g1:v4000").clear_contents()

# Download Instruments
exchange = None
while exchange is None:
    try:
        exchange = pd.DataFrame(kite.instruments("NFO"))
        exchange = exchange[exchange["segment"] == "NFO-OPT"]
    except:
        print("Exchange Download Error... Retrying...")
        time.sleep(10)

# Populate Symbols in Excel
df_symbols = pd.DataFrame({"FNO Symbol": exchange["name"].unique()})
df_symbols.set_index("FNO Symbol", inplace=True)
oc.range("a1").value = df_symbols
oc.range("d2").value, oc.range("d3").value = "Symbol==>", "Expiry==>"

# Global Variables
pre_oc_symbol = pre_oc_expiry = ""
expiries_list = []
instrument_dict = {}
prev_day_oi = {}
stop_thread = False

def fetch_prev_day_oi(data):
    global prev_day_oi, stop_thread
    for symbol, details in data.items():
        if stop_thread:
            break
        while symbol not in prev_day_oi:
            try:
                pre_day_data = kite.historical_data(details["token"],
                    (datetime.now() - timedelta(days=5)).date(),
                    (datetime.now() - timedelta(days=1)).date(), "day", oi=True)
                prev_day_oi[symbol] = pre_day_data[-1]["oi"] if pre_day_data else 0
            except:
                time.sleep(0.5)

def calculate_greeks(premium, expiry, spot, strike, rate, opt_type):
    try:
        t = ((datetime(expiry.year, expiry.month, expiry.day, 15, 30) - datetime.now()).total_seconds()) / (365 * 24 * 3600)
        if premium == 0 or t <= 0 or spot <= 0 or strike <= 0 or rate <= 0:
            raise Exception
        flag = opt_type[0].lower()
        iv = implied_volatility(premium, spot, strike, t, rate, flag)
        return {
            "IV": iv,
            "Delta": delta(flag, spot, strike, t, rate, iv),
            "Gamma": gamma(flag, spot, strike, t, rate, iv),
            "Rho": rho(flag, spot, strike, t, rate, iv),
            "Theta": theta(flag, spot, strike, t, rate, iv),
            "Vega": vega(flag, spot, strike, t, rate, iv)
        }
    except:
        return dict.fromkeys(["IV", "Delta", "Gamma", "Rho", "Theta", "Vega"], 0)

print("Excel: Started")
while True:
    oc_symbol, oc_expiry = oc.range("e2").value, oc.range("e3").value
    if oc_symbol != pre_oc_symbol or oc_expiry != pre_oc_expiry:
        oc.range("g:v").clear_contents()
        instrument_dict = {}
        stop_thread = True
        time.sleep(2)
        if oc_symbol != pre_oc_symbol:
            oc.range("b:b").clear_contents()
            oc.range("d6:e20").clear_contents()
            expiries_list = []
        pre_oc_symbol, pre_oc_expiry = oc_symbol, oc_expiry

    if oc_symbol:
        try:
            if not expiries_list:
                sym_data = exchange[exchange["name"] == oc_symbol]
                expiries_list = sorted(sym_data["expiry"].unique())
                df_expiry = pd.DataFrame({"Expiry Date": expiries_list})
                df_expiry.set_index("Expiry Date", inplace=True)
                oc.range("b1").value = df_expiry

            if not instrument_dict and oc_expiry:
                df_oc = exchange[(exchange["name"] == oc_symbol) & (exchange["expiry"] == oc_expiry.date())]
                lot_size = df_oc.iloc[0]["lot_size"]
                for _, row in df_oc.iterrows():
                    instrument_dict[f"NFO:{row['tradingsymbol']}"] = {
                        "strikePrice": row["strike"],
                        "instrumentType": row["instrument_type"],
                        "token": row["instrument_token"]
                    }
                stop_thread = False
                threading.Thread(target=fetch_prev_day_oi, args=(instrument_dict,)).start()

            # Fetching Data
            option_data = {}
            index = "NSE:NIFTY 50" if oc_symbol == "NIFTY" else ("NSE:NIFTY BANK" if oc_symbol == "BANKNIFTY" else f"NSE:{oc_symbol}")
            spot_price = kite.quote(index)[index]["last_price"]
            quotes = kite.quote(list(instrument_dict.keys()))

            for symbol, quote in quotes.items():
                instr = instrument_dict[symbol]
                option_data[symbol] = {
                    "strikePrice": instr["strikePrice"],
                    "instrumentType": instr["instrumentType"],
                    "lastPrice": quote["last_price"],
                    "totalTradedVolume": quote["volume"],
                    "openInterest": int(quote["oi"] / lot_size),
                    "change": quote["last_price"] - quote["ohlc"]["close"] if quote["last_price"] else 0,
                    "changeinOpenInterest": int((quote["oi"] - prev_day_oi.get(symbol, 0)) / lot_size)
                }
                option_data[symbol].update(calculate_greeks(
                    quote["last_price"], oc_expiry.date(), spot_price, instr["strikePrice"], 0.1, instr["instrumentType"]
                ))

            df = pd.DataFrame(option_data).T
            ce_df = df[df.instrumentType == "CE"].copy()
            pe_df = df[df.instrumentType == "PE"].copy()

            ce_df = ce_df.rename(columns={"openInterest": "CE OI", "changeinOpenInterest": "CE Change in OI",
                                           "IV": "CE IV", "lastPrice": "CE LTP", "change": "CE LTP Change",
                                           "totalTradedVolume": "CE Volume"})
            pe_df = pe_df.rename(columns={"openInterest": "PE OI", "changeinOpenInterest": "PE Change in OI",
                                           "IV": "PE IV", "lastPrice": "PE LTP", "change": "PE LTP Change",
                                           "totalTradedVolume": "PE Volume"})
            df_combined = pd.concat([ce_df.set_index("strikePrice"), pe_df.set_index("strikePrice")], axis=1)
            df_combined = df_combined.replace(np.nan, 0)
            df_combined["Strike"] = df_combined.index

            summary = [
                ["Spot LTP", spot_price],
                ["Total Call OI", ce_df["CE OI"].sum()],
                ["Total Put OI", pe_df["PE OI"].sum()],
                ["Total Call Change in OI", ce_df["CE Change in OI"].sum()],
                ["Total Put Change in OI", pe_df["PE Change in OI"].sum()],
                ["", ""],
                ["Max Call OI", ce_df["CE OI"].max()],
                ["Max Put OI", pe_df["PE OI"].max()],
                ["Max Call OI Strike", ce_df[ce_df["CE OI"] == ce_df["CE OI"].max()].index[0]],
                ["Max Put OI Strike", pe_df[pe_df["PE OI"] == pe_df["PE OI"].max()].index[0]],
                ["", ""],
                ["Max Call Change in OI", ce_df["CE Change in OI"].max()],
                ["Max Put Change in OI", pe_df["PE Change in OI"].max()],
                ["Max Call Change in OI Strike", ce_df[ce_df["CE Change in OI"] == ce_df["CE Change in OI"].max()].index[0]],
                ["Max Put Change in OI Strike", pe_df[pe_df["PE Change in OI"] == pe_df["PE Change in OI"].max()].index[0]]
            ]

            oc.range("d6").value = summary
            oc.range("g1").value = df_combined

        except Exception as e:
            print(f"Error: {e}")
            continue
