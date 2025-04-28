from flask import Blueprint, jsonify, request
from kiteconnect import KiteConnect
import logging

# Create Blueprint for F&O trading
fno_trading_bp = Blueprint('fno_trading', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_kite_instance():
    """Helper function to get KiteConnect instance from main app"""
    from main import kite
    return kite

@fno_trading_bp.route('/fno/trade_option', methods=['POST'])
def trade_option():
    try:
        data = request.get_json()
        
        # Required parameters
        symbol = data.get('symbol')
        strike_price = data.get('strike_price')
        expiry = data.get('expiry')
        quantity = data.get('quantity', 1)
        transaction_type = data.get('transaction_type', 'BUY')  # BUY or SELL
        option_type = data.get('option_type', 'CE')  # CE or PE
        
        if not all([symbol, strike_price, expiry]):
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters. Need symbol, strike_price, and expiry'
            }), 400

        # Validate transaction type
        if transaction_type not in ['BUY', 'SELL']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid transaction_type. Must be either BUY or SELL'
            }), 400

        # Validate option type
        if option_type not in ['CE', 'PE']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid option_type. Must be either CE or PE'
            }), 400

        kite = get_kite_instance()
        
        # Construct the trading symbol
        trading_symbol = f"{symbol}{expiry}{strike_price}{option_type}"
        
        # Map transaction type to Kite's constants
        kite_transaction_type = (kite.TRANSACTION_TYPE_BUY 
                               if transaction_type == 'BUY' 
                               else kite.TRANSACTION_TYPE_SELL)
        
        # Place order
        order = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NFO,
            tradingsymbol=trading_symbol,
            transaction_type=kite_transaction_type,
            quantity=quantity,
            product=kite.PRODUCT_NRML,
            order_type=kite.ORDER_TYPE_MARKET
        )
        
        return jsonify({
            'status': 'success',
            'message': f'{transaction_type} {option_type} option order placed successfully',
            'order_id': order,
            'details': {
                'symbol': symbol,
                'strike_price': strike_price,
                'expiry': expiry,
                'quantity': quantity,
                'transaction_type': transaction_type,
                'option_type': option_type,
                'trading_symbol': trading_symbol
            }
        })
        
    except Exception as e:
        logger.error(f"Error in trade_option: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Helper endpoint to get option details
@fno_trading_bp.route('/fno/option_details', methods=['GET'])
def get_option_details():
    try:
        symbol = request.args.get('symbol')
        strike_price = request.args.get('strike_price')
        expiry = request.args.get('expiry')
        option_type = request.args.get('option_type', 'CE')  # CE or PE
        
        if not all([symbol, strike_price, expiry]):
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters. Need symbol, strike_price, and expiry'
            }), 400

        kite = get_kite_instance()
        
        # Construct the trading symbol
        trading_symbol = f"{symbol}{expiry}{strike_price}{option_type}"
        
        # Get instrument details
        quote = kite.quote(f"NFO:{trading_symbol}")
        logger.info(f"Quote: {quote}")
        logger.info(f"Trading symbol: {trading_symbol}")
        return jsonify({
            'status': 'success',
            'data': quote
        })
        
    except Exception as e:
        logger.error(f"Error in get_option_details: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@fno_trading_bp.route('/fno/trade_multiple_options', methods=['POST'])
def trade_multiple_options():
    try:
        data = request.get_json()
        trades = data.get('trades', [])
        
        if not trades or not isinstance(trades, list):
            return jsonify({
                'status': 'error',
                'message': 'Missing or invalid trades array in request body'
            }), 400

        kite = get_kite_instance()
        results = []

        for trade in trades:
            # Required parameters for each trade
            symbol = trade.get('symbol')
            strike_price = trade.get('strike_price')
            expiry = trade.get('expiry')
            quantity = trade.get('quantity', 1)
            transaction_type = trade.get('transaction_type', 'BUY')  # BUY or SELL
            option_type = trade.get('option_type', 'CE')  # CE or PE
            
            if not all([symbol, strike_price, expiry]):
                results.append({
                    'status': 'error',
                    'message': f'Missing required parameters for trade: {trade}',
                    'trade': trade
                })
                continue

            # Validate transaction type
            if transaction_type not in ['BUY', 'SELL']:
                results.append({
                    'status': 'error',
                    'message': f'Invalid transaction_type for trade: {trade}',
                    'trade': trade
                })
                continue

            # Validate option type
            if option_type not in ['CE', 'PE']:
                results.append({
                    'status': 'error',
                    'message': f'Invalid option_type for trade: {trade}',
                    'trade': trade
                })
                continue

            try:
                # Construct the trading symbol
                trading_symbol = f"{symbol}{expiry}{strike_price}{option_type}"
                
                # Map transaction type to Kite's constants
                kite_transaction_type = (kite.TRANSACTION_TYPE_BUY 
                                    if transaction_type == 'BUY' 
                                    else kite.TRANSACTION_TYPE_SELL)
                
                # Place order
                order = kite.place_order(
                    variety=kite.VARIETY_REGULAR,
                    exchange=kite.EXCHANGE_NFO,
                    tradingsymbol=trading_symbol,
                    transaction_type=kite_transaction_type,
                    quantity=quantity,
                    product=kite.PRODUCT_NRML,
                    order_type=kite.ORDER_TYPE_MARKET
                )
                
                results.append({
                    'status': 'success',
                    'message': f'{transaction_type} {option_type} option order placed successfully',
                    'order_id': order,
                    'details': {
                        'symbol': symbol,
                        'strike_price': strike_price,
                        'expiry': expiry,
                        'quantity': quantity,
                        'transaction_type': transaction_type,
                        'option_type': option_type,
                        'trading_symbol': trading_symbol
                    }
                })
                
            except Exception as e:
                results.append({
                    'status': 'error',
                    'message': str(e),
                    'trade': trade
                })
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in trade_multiple_options: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 