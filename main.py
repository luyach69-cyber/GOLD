import os
import requests
import pandas as pd

# 從環境變數讀取 GitHub Secrets 中的 Telegram 憑證
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram 憑證未設定，跳過推播。")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f"推播失敗: {e}")

def evaluate_main_wave_signal(stock_code, tick, quote, k_history):
    """
    主升段與五檔防偽突破檢核核心邏輯
    """
    # 條件 1：現價突破當日均價線 (VWAP) 且漲幅大於 1%
    cond_vwap = (tick['price'] > quote['vwap']) and (tick['price'] >= quote['reference'] * 1.01)
    
    # 條件 2：突破早盤最高價
    cond_breakout = tick['price'] >= quote['opening_high']
    
    # 條件 3：量能放大
    if len(k_history) >= 5:
        recent_avg_vol = k_history['volume'].tail(5).mean()
    else:
        recent_avg_vol = 50
    cond_volume = tick['volume'] >= (recent_avg_vol * 1.5)
    
    # 條件 4：大單敲進與外盤追價
    cond_big_order = (tick['volume'] >= 15) and (tick['is_buy_side'] == True)
    
    # 條件 5：五檔掛單結構檢核 (防偽突破 / 防騙線)
    total_bid_vol = sum(quote['bid_volume'])
    total_ask_vol = sum(quote['ask_volume'])
    
    if total_ask_vol == 0:
        bid_ask_ratio = 2.0
    else:
        bid_ask_ratio = total_bid_vol / total_ask_vol
        
    best_bid_support = quote['bid_volume'][0] >= 30
    cond_order_book_solid = (bid_ask_ratio >= 1.5) and best_bid_support
    
    is_valid_signal = (
        cond_vwap and 
        cond_breakout and 
        cond_volume and 
        cond_big_order and 
        cond_order_book_solid
    )
    
    return is_valid_signal

def main():
    print("開始執行台股主升段智慧掃描與五檔防偽檢核...")
    
    watchlist = ["2330", "2303", "2454"]
    
    for code in watchlist:
        # 模擬即時資料（串接真實券商 API 時請替換為 API 回傳之 Tick / Quote）
        mock_tick = {
            'price': 600.0,
            'volume': 20,
            'is_buy_side': True
        }
        mock_quote = {
            'reference': 580.0,
            'vwap': 590.0,
            'opening_high': 595.0,
            'bid_volume': [45, 20, 15, 10, 5],
            'ask_volume': [10, 15, 20, 25, 30]
        }
        mock_k_history = pd.DataFrame({'volume': [10, 12, 15, 11, 14]})
        
        matched = evaluate_main_wave_signal(code, mock_tick, mock_quote, mock_k_history)
        
        if matched:
            current_price = mock_tick['price']
            suggested_entry = current_price
            stop_loss = round(current_price * 0.985, 2)   # 停損價 -1.5%
            take_profit = round(current_price * 1.035, 2) # 停利價 +3.5%
            
            ratio = sum(mock_quote['bid_volume']) / sum(mock_quote['ask_volume'])
            
            msg = (
                f"🚨 *【主升段強勢突破快訊】*\n"
                f"• 股票代號：`{code}`\n"
                f"• **現價 / 建議進場價**：`{suggested_entry}`\n"
                f"• **🔴 停損價 (-1.5%)**：`{stop_loss}`\n"
                f"• **🟢 停利價 (+3.5%)**：`{take_profit}`\n"
                f"• 籌碼動能：外盤大單敲進 `{mock_tick['volume']}` 張\n"
                f"• 五檔防偽檢核：買賣總量比 `{ratio:.1f}` 倍，下方有厚單支撐！\n"
                f"💡 *請前往券商模擬軟體確認後手動下單。*"
            )
            print(f"發現符合標的 {code}，發送 Telegram 推播...")
            send_telegram_alert(msg)
        else:
            print(f"股票 {code} 目前盤勢未達主升段標準或遭到過濾。")

if __name__ == "__main__":
    main()
