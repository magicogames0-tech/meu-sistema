from flask import Flask
import threading
import time
import iq2  # seu arquivo do bot

app = Flask(__name__)

def run_bot():
    while True:
        try:
            iq2.main()
        except Exception as e:
            print(f"[ERRO] Bot travou: {e}")
            time.sleep(10)

threading.Thread(target=run_bot, daemon=True).start()

@app.route("/")
def home():
    return "Bot IQ Option rodando no Render Free!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
