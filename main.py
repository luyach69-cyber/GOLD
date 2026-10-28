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

def get_dynamic_watchlist():
    """
    動態取得當日台股當沖熱門股 / 成交量排行清單
    實務上可串接證交所公開 JSON API 或券商 API 的排行功能
    """
    print("正在取得今日台股當沖熱門與成交量排行標的...")
    try:
        # 範例動態熱門清單（實務上可替換為串接 API 或爬蟲取得的當日成交量前幾名代號）
        hot_watchlist = ["2330", "2303", "2454", "2603", "3231", "2317", "2464"]
        return hot_watchlist
    except Exception as e:
        print(f"取得熱門清單失敗: {e}")
        return ["2330", "2303"]

def evaluate_optimized_main_wave_signal(stock_code, tick, quote, k_history):
    """
    優化版主升段與價差捕捉邏輯（結合近 1 小時高點突破與放寬的五檔防偽）
    """
    # 1. 均價線防線：現價必須站上 VWAP，且漲幅大於 0.8%
    cond_vwap = (tick['price'] > quote['vwap']) and (tick['price'] >= quote['reference'] * 1.008)
    
    # 2. 價格結構：突破「近 1 小時內 K 線的高點」，捕捉盤中二次攻擊
    if len(k_history) >= 12:
        recent_1h_high = k_history['high'].tail(12).max()
    else:
        recent_1h_high = k_history['high'].max() if len(k_history) > 0 else quote['reference']
    cond_breakout = tick['price'] >= recent_1h_high
    
    # 3. 量能爆發：當前成交量為近期平均的 2 倍以上
    recent_avg_vol = k_history['volume'].tail(5).mean() if len(k_history) >= 5 else 50
    cond_volume = tick['volume'] >= (recent_avg_vol * 2.0)
    
    # 4. 籌碼追價：外盤大單敲進（張數 >= 15）
    cond_big_order = (tick['volume'] >= 15) and (tick['is_buy_side'] == True)
    
    # 5. 五檔防偽檢核：買賣總量比放寬至 1.2 倍，但第一檔要求至少 40 張厚單防守
    total_bid_vol = sum(quote['bid_volume'])
    total_ask_vol = sum(quote['ask_volume'])
    
    if total_ask_vol == 0:
        bid_ask_ratio = 2.0
    else:
        bid_ask_ratio = total_bid_vol / total_ask_vol
        
    best_bid_support = quote['bid_volume'][0] >= 40
    cond_order_book_solid = (bid_ask_ratio >= 1.2) and best_bid_support
    
    is_valid_signal = (
        cond_vwap and 
        cond_breakout and 
        cond_volume and 
        cond_big_order and 
        cond_order_book_solid
    )
    
    return is_valid_signal

def main():
    print("=== 啟動台股主升段智慧掃描與價差捕捉系統 ===")
    
    # 1. 自動取得當日熱門觀察清單
    watchlist = get_dynamic_watchlist()
    print(f"今日自動鎖定監控標的：{watchlist}")
    
    for code in watchlist:
        # 模擬即時資料（串接真實券商 API 時請替換為 API 回傳之 Tick / Quote / K線歷史）
        mock_tick = {
            'price': 180.0,
            'volume': 20,
            'is_buy_side': True
        }
        mock_quote = {
            'reference': 175.0,
            'vwap': 178.0,
            'opening_high': 185.0,
            'bid_volume': [50, 30, 20, 10, 5],
            'ask_volume': [20, 25, 30, 15, 10]
        }
        mock_k_history = pd.DataFrame({
            'high': [176, 177, 178, 179, 179.5] * 3,
            'volume': [10, 12, 15, 11, 14] * 3
        })
        
        matched = evaluate_optimized_main_wave_signal(code, mock_tick, mock_quote, mock_k_history)
        
        if matched:
            current_price = mock_tick['price']
            suggested_entry = current_price
            stop_loss = round(current_price * 0.985, 2)   # 停損價 -1.5%
            take_profit = round(current_price * 1.035, 2) # 停利價 +3.5%
            
            ratio = sum(mock_quote['bid_volume']) / sum(mock_quote['ask_volume'])
            
            msg = (
                f"🚨 *【主升段價差突破快訊】*\n"
                f"• 股票代號：`{code}`\n"
                f"• **現價 / 建議進場價**：`{suggested_entry}`\n"
                f"• **🔴 停損價 (-1.5%)**：`{stop_loss}`\n"
                f"• **🟢 停利價 (+3.5%)**：`{take_profit}`\n"
                f"• 籌碼動能：外盤大單敲進 `{mock_tick['volume']}` 張\n"
                f"• 五檔防偽檢核：買賣總量比 `{ratio:.1f}` 倍，下方第一檔有 40 張厚單防守！\n"
                f"💡 *請前往券商模擬軟體確認後手動下單。*"
            )
            print(f"發現符合標的 {code}，發送 Telegram 推播...")
            send_telegram_alert(msg)
        else:
            print(f"股票 {code} 目前盤勢未達主升段標準或遭到過濾。")

if __name__ == "__main__":
    main()
