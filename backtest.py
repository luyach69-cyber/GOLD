import pandas as pd
import numpy as np

def run_backtest(historical_data):
    """
    historical_data: 包含歷史 Tick 或分K 數據的 DataFrame
    必要欄位: ['code', 'datetime', 'price', 'reference', 'vwap', 'opening_high', 'volume', 'is_buy_side', 'bid_vol_sum', 'ask_vol_sum', 'best_bid_vol']
    """
    trades = []
    position = None
    
    for i in range(5, len(historical_data)):
        row = historical_data.iloc[i]
        k_history = historical_data.iloc[i-5:i]
        
        cond_vwap = (row['price'] > row['vwap']) and (row['price'] >= row['reference'] * 1.01)
        cond_breakout = row['price'] >= row['opening_high']
        recent_avg_vol = k_history['volume'].mean()
        cond_volume = row['volume'] >= (recent_avg_vol * 1.5)
        cond_big_order = (row['volume'] >= 15) and (row['is_buy_side'] == True)
        
        bid_ask_ratio = row['bid_vol_sum'] / max(row['ask_vol_sum'], 1)
        best_bid_support = row['best_bid_vol'] >= 30
        cond_order_book_solid = (bid_ask_ratio >= 1.5) and best_bid_support
        
        signal = cond_vwap and cond_breakout and cond_volume and cond_big_order and cond_order_book_solid
        
        if signal and position is None:
            entry_price = row['price']
            stop_loss = entry_price * 0.985
            take_profit = entry_price * 1.035
            
            position = {
                'entry_time': row['datetime'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            
        elif position is not None:
            current_price = row['price']
            
            if current_price <= position['stop_loss']:
                pnl = (position['stop_loss'] - position['entry_price']) / position['entry_price']
                trades.append({'type': 'LOSS', 'pnl': pnl, 'exit_time': row['datetime']})
                position = None
            elif current_price >= position['take_profit']:
                pnl = (position['take_profit'] - position['entry_price']) / position['entry_price']
                trades.append({'type': 'WIN', 'pnl': pnl, 'exit_time': row['datetime']})
                position = None
            elif str(row['datetime']).endswith("13:25:00"):
                pnl = (current_price - position['entry_price']) / position['entry_price']
                trades.append({'type': 'CLOSE', 'pnl': pnl, 'exit_time': row['datetime']})
                position = None

    if not trades:
        print("回測期間無觸發交易。")
        return
        
    df_trades = pd.DataFrame(trades)
    win_rate = len(df_trades[df_trades['pnl'] > 0]) / len(df_trades) * 100
    total_return = df_trades['pnl'].sum() * 100
    
    print(f"========== 回測績效報告 ==========")
    print(f"總交易次數：{len(df_trades)} 次")
    print(f"勝率：{win_rate:.2f}%")
    print(f"累計報酬率：{total_return:.2f}%")
    print(f"==================================")

if __name__ == "__main__":
    print("請載入歷史資料 DataFrame 並執行 run_backtest(df)")
