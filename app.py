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
    return "ETF Stock Telegram Bot is running successfully!"

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """接收你在 Telegram 傳送的指令或代號"""
    data = request.json or {}

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").strip()

        if text.startswith("/start"):
            reply = (
                "📈 【歡迎使用 ETF 股市與即時行情小幫手！】\n\n"
                "• 輸入股票或 ETF 代號（例如 0050.TW、00878.TW、AAPL），查詢最新報價與漲跌幅。\n"
                "• 輸入關鍵字「新聞」或 /news，查看近期 ETF 市場動態！"
            )
        elif text == "新聞" or text.startswith("/news"):
            reply = (
                "📰 【近期 ETF 市場焦點摘要】\n\n"
                "1. 市值型與高股息並進：定期定額熱度持續，存股族偏好分散配置於各大權值股與高息標的。\n"
                "2. 除息旺季留意：熱門 ETF 除息前後常吸引資金進出，建議留意相關公告與實際殖利率。\n\n"
                "💡 小提示：直接輸入 ETF 代號（如 0050.TW）可看最新股價！"
            )
        else:
            stock_symbol = text.upper()
            try:
                stock = yf.Ticker(stock_symbol)
                hist = stock.history(period="5d")

                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else None

                    if prev_close:
                        change = current_price - prev_close
                        change_pct = (change / prev_close) * 100
                        change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
                    else:
                        change_str = "無法計算"

                    reply = (
                        f"📊 【{stock_symbol} 最新行情】\n\n"
                        f"• 最新價格：{current_price:.2f}\n"
                        f"• 漲跌表現：{change_str}\n\n"
                        f"⚠️ 數據僅供參考，投資請自行評估風險。"
                    )
                else:
                    reply = f"❌ 找不到代號 {stock_symbol} 的資料。台股 ETF 請加上 .TW（例如 0050.TW）。"
            except Exception as e:
                reply = f"⚠️ 查詢發生錯誤：{str(e)}"

        send_telegram_message(reply, chat_id)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
