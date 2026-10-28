import os
import requests
import pandas as pd

# 1. Telegram 推播設定（從環境變數讀取 GitHub Secrets）
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

# 2. 主升段與五檔防偽突破檢核核心邏輯
def evaluate_main_wave_signal(stock_code, tick, quote, k_history):
    """
    stock_code: 股票代號
    tick: 最新成交明細 (price=成交價, volume=成交量, is_buy_side=是否為外盤買進)
    quote: 當前報價與五檔 (reference=參考價, vwap=均價線, opening_high=早盤高點, 
                         bid_volume=委買五檔張數陣列, ask_volume=委賣五檔張數陣列)
    k_history: 近期 K 線歷史數據 DataFrame (包含 volume 欄位)
    """
    
    # --- [維度一] 價格結構與均價線突破 ---
    # 條件 1：現價必須站上當日均價線 (VWAP) 且漲幅大於 1%
    cond_vwap = (tick['price'] > quote['vwap']) and (tick['price'] >= quote['reference'] * 1.01)
    
    # 條件 2：突破早盤最高價 (Opening Range High)
    cond_breakout = tick['price'] >= quote['opening_high']
    
    # --- [維度二] 量能放大 ---
    if len(k_history) >= 5:
        recent_avg_vol = k_history['volume'].tail(5).mean()
    else:
        recent_avg_vol = 50  # 預設保護值
    cond_volume = tick['volume'] >= (recent_avg_vol * 1.5)
    
    # --- [維度三] 籌碼動能與大單敲進 ---
    # 條件 3：單筆成交量具備一定規模（例如 >= 15張）且為外盤成交 (買方積極追價)
    cond_big_order = (tick['volume'] >= 15) and (tick['is_buy_side'] == True)
    
    # --- [維度四] 五檔掛單結構檢核 (防偽突破 / 防騙線) ---
    total_bid_vol = sum(quote['bid_volume'])  # 委買五檔總量
    total_ask_vol = sum(quote['ask_volume'])  # 委賣五檔總量
    
    # 防呆：避免分母為零
    if total_ask_vol == 0:
        bid_ask_ratio = 2.0
    else:
        bid_ask_ratio = total_bid_vol / total_ask_vol
        
    # 最佳買進檔（第一檔）是否有厚實掛單支撐（例如第一檔至少有 30 張掛單防守）
    best_bid_support = quote['bid_volume'][0] >= 30
    
    # 綜合防偽條件：委買總量是委賣的 1.5 倍以上，且下方第一檔有厚單防守
    cond_order_book_solid = (bid_ask_ratio >= 1.5) and best_bid_support
    
    # --- 最終判定：所有條件必須同時成立 ---
    is_valid_signal = (
        cond_vwap and 
        cond_breakout and 
        cond_volume and 
        cond_big_order and 
        cond_order_book_solid
    )
    
    return is_valid_signal

# 3. 盤中主程式進入點
def main():
    print("開始執行台股主升段智慧掃描與五檔防偽檢核...")
    
    # 模擬您的監控觀察清單（實際串接券商 API 時改從 API 取得清單）
    watchlist = ["2330", "2303", "2454"]
    
    for code in watchlist:
        # --- 模擬即時資料（實際開發時替換為 Shioaji 或其他券商即時回調 Tick / Quote 資料） ---
        mock_tick = {
            'price': 600.0,
            'volume': 20,
            'is_buy_side': True  # 外盤成交
        }
        mock_quote = {
            'reference': 580.0,
            'vwap': 590.0,
            'opening_high': 595.0,
            'bid_volume': [45, 20, 15, 10, 5],  # 委買五檔張數
            'ask_volume': [10, 15, 20, 25, 30]   # 委賣五檔張數
        }
        mock_k_history = pd.DataFrame({'volume': [10, 12, 15, 11, 14]})
        
        # 執行主升段與五檔邏輯判斷
        matched = evaluate_main_wave_signal(code, mock_tick, mock_quote, mock_k_history)
        
        if matched:
            ratio = sum(mock_quote['bid_volume']) / sum(mock_quote['ask_volume'])
            msg = (
                f"🚨 *【主升段強勢突破快訊】*\n"
                f"• 股票代號：`{code}`\n"
                f"• 價格：`{mock_tick['price']}` (突破均價與早盤高點)\n"
                f"• 籌碼動能：外盤大單敲進 `{mock_tick['volume']}` 張\n"
                f"• 五檔防偽檢核：委買總量為委賣的 `{ratio:.1f}` 倍，下方有厚單支撐！\n"
                f"💡 *請前往券商模擬軟體確認後手動下單。*"
            )
            print(f"發現符合標的 {code}，發送 Telegram 推播...")
            send_telegram_alert(msg)
        else:
            print(f"股票 {code} 目前盤勢未達主升段標準或遭到過濾。")

if __name__ == "__main__":
    main()
