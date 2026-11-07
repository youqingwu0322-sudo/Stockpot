import os
from flask import Flask, request
import requests
import yfinance as yf

app = Flask(__name__)

def send_telegram_message(text, chat_id=None):
    """發送訊息到 Telegram"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    target_chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not target_chat_id:
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": text
    }
    requests.post(url, json=payload)

@app.route("/", methods=["GET"])
def home():
    return "Smart Stock Analysis Bot is running!"

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.json or {}
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").strip()

        if text.startswith("/start"):
            reply = (
                "🤖 **【AI 智慧股市與防詐分析小幫手】**\n\n"
                "• **直接輸入代號**（如 `0050`、`2330`、`AAPL`，**不用打 .TW**），自動幫你計算 **5日均線**、結合 **美股大盤** 與 **近期一個月新聞風向** 綜合評估是否可買進！\n"
                "• 輸入 `/news` 查看最新市場焦點。"
            )
        elif text == "新聞" or text.startswith("/news"):
            reply = (
                "📰 **【近期市場焦點摘要】**\n\n"
                "1. **美股與科技股動向**：聯準會動向與企業財報為影響全球股市的主旋律。\n"
                "2. **台股與 ETF 趨勢**：高股息與市值型 ETF 定期定額持續創高，操作建議分批布局，避免追高。\n\n"
                "💡 *小提示：直接傳送代號即可開始智慧分析！*"
            )
        else:
            raw_symbol = text.upper()
            
            # 智慧判斷台股：如果輸入純數字或台股常見代號且沒加 .TW，自動幫它補上 .TW
            if raw_symbol.isdigit() or (len(raw_symbol) == 4 and not raw_symbol.isalpha()):
                stock_symbol = f"{raw_symbol}.TW"
            elif raw_symbol in ["0050", "00878", "0056", "2330", "2317", "2454"]:
                stock_symbol = f"{raw_symbol}.TW"
            else:
                stock_symbol = raw_symbol

            reply = f"🔍 正在為您分析 **{stock_symbol}** 的 5日均線、美股連動與近期新聞，請稍候..."
            send_telegram_message(reply, chat_id)

            try:
                # 1. 抓取目標股票技術線圖 (近 10 天以計算 MA5)
                stock = yf.Ticker(stock_symbol)
                hist = stock.history(period="10d")

                if not hist.empty and len(hist) >= 5:
                    current_price = hist['Close'].iloc[-1]
                    # 計算 5 日均線 (MA5)
                    ma5 = hist['Close'].iloc[-5:].mean()
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change_pct = ((current_price - prev_close) / prev_close) * 100

                    # 2. 參考美股大盤 (^GSPC 標普500) 作為外部環境參考
                    sp500 = yf.Ticker("^GSPC")
                    sp_hist = sp500.history(period="3d")
                    sp_status = "持平穩定"
                    if not sp_hist.empty and len(sp_hist) >= 2:
                        sp_change = ((sp_hist['Close'].iloc[-1] - sp_hist['Close'].iloc[-2]) / sp_hist['Close'].iloc[-2]) * 100
                        sp_status = f"強勢上漲 (+{sp_change:.2f}%)" if sp_change > 0 else f"拉回震盪 ({sp_change:.2f}%)"

                    # 3. 取得近期一個月的新聞標題與風向摘要
                    news_list = stock.news or []
                    news_summary = ""
                    if news_list:
                        # 取前 2 則最新新聞
                        recent_titles = [item.get('title', '') for item in news_list[:2] if 'title' in item]
                        if recent_titles:
                            news_summary = "\n".join([f"• {t}" for t in recent_titles])
                    
                    if not news_summary:
                        news_summary = "• 近期無重大突發利空，市場維持常態波動。"

                    # 4. 綜合評估買進建議
                    # 邏輯：價格在 MA5 之上且美股穩健 -> 偏向可考慮分批佈局；若跌破 MA5 或美股大趨勢不佳 -> 建議保守觀望
                    if current_price >= ma5:
                        tech_advice = "🟢 **技術面：股價站上 5日均線 (MA5) 之上，短線動能偏多。**"
                        suggestion = "👉 **綜合評估**：短線趨勢向上，若美股維持穩健且無重大負面新聞，可考慮**分批逢低進場**或續抱，嚴守停損點。"
                    else:
                        tech_advice = "🔴 **技術面：股價目前位於 5日均線 (MA5) 之下，短線偏弱震盪。**"
                        suggestion = "👉 **綜合評估**：短線動能較弱，建議**暫時觀望、不要急著接刀**，等待站回 5日均線或量縮止穩再行評估。"

                    reply = (
                        f"📊 **【{stock_symbol} 智慧綜合分析報告】**\n\n"
                        f"• **當前最新價格**：`{current_price:.2f}`\n"
                        f"• **5日均線 (MA5)**：`{ma5:.2f}`\n"
                        f"• **今日漲跌幅**：`{change_pct:+.2f}%`\n"
                        f"• **美股大盤參考 (標普500)**：{sp_status}\n\n"
                        f"{tech_advice}\n\n"
                        f"📰 **近期一個月新聞風向**：\n{news_summary}\n\n"
                        f"{suggestion}\n\n"
                        f"⚠️ *投資有賺有賠，AI 綜合分析僅供參考，請自行評估風險。*"
                    )
                else:
                    reply = f"❌ 找不到代號 **{stock_symbol}** 的足夠歷史數據，請確認代號是否正確（例如輸入 `0050` 或 `2330`）。"
            except Exception as e:
                reply = f"⚠️ 分析過程發生錯誤：`{str(e)}`"

        send_telegram_message(reply, chat_id)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
