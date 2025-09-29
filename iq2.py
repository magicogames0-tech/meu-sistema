import os
import time
import datetime
import traceback
import requests
import pytz
import statistics

# ========= CONFIG =========
IQ_EMAIL = os.getenv("IQ_EMAIL")
IQ_PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

CANDLE_INTERVAL = 5    # minutos
LOOKBACK_CANDLES = 30  # usado para suporte/resistência e média móvel
CHECK_INTERVAL = 20    # segundos entre verificações
# ==========================

try:
    from iqoptionapi.stable_api import IQ_Option
    IQ_LIB_AVAILABLE = True
except Exception:
    IQ_LIB_AVAILABLE = False


class IQConnector:
    def __init__(self, email, password):
        self.api = None
        self.connected = False
        if IQ_LIB_AVAILABLE:
            self.api = IQ_Option(email, password)

    def connect(self):
        if not IQ_LIB_AVAILABLE:
            print("[ERRO] iqoptionapi não está instalado.")
            return False
        print("[INFO] Tentando conectar na IQ Option...")
        self.connected, reason = self.api.connect()
        print(f"[DEBUG] Conectado: {self.connected} | Motivo: {reason}")
        return self.connected

    def get_candles(self, asset, interval_minutes, n):
        if not self.connected:
            raise RuntimeError("Não conectado à IQ Option")
        timeframe = interval_minutes * 60
        candles = self.api.get_candles(asset, timeframe, n, time.time())
        if not candles:
            raise RuntimeError(f"Nenhuma vela retornada para {asset}")
        return candles


def telegram_send(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# =============== ANALISE EURUSD (mercado real) =================
def detect_support_resistance(candles, n=20):
    highs = [c['high'] for c in candles[-n:]]
    lows = [c['low'] for c in candles[-n:]]
    return max(highs), min(lows)  # resistência, suporte


def moving_average(candles, period=20):
    closes = [c['close'] for c in candles[-period:]]
    return statistics.mean(closes)


def detect_price_action(c1, c2):
    """Retorna padrão de price action entre 2 últimas velas"""
    # Engolfo de alta
    if c2['close'] > c2['open'] and c1['close'] < c1['open'] and c2['close'] > c1['open'] and c2['open'] < c1['close']:
        return "CALL", "Engolfo de Alta"

    # Engolfo de baixa
    if c2['close'] < c2['open'] and c1['close'] > c1['open'] and c2['close'] < c1['open'] and c2['open'] > c1['close']:
        return "PUT", "Engolfo de Baixa"

    # Martelo / Pinbar de alta
    corpo = abs(c2['close'] - c2['open'])
    pavio_inferior = min(c2['open'], c2['close']) - c2['low']
    pavio_superior = c2['high'] - max(c2['open'], c2['close'])
    if pavio_inferior > 2 * corpo and pavio_superior < corpo:
        return "CALL", "Martelo (Pinbar de Alta)"
    if pavio_superior > 2 * corpo and pavio_inferior < corpo:
        return "PUT", "Estrela Cadente (Pinbar de Baixa)"

    return None, None


def analyze_eurusd_real(candles):
    if len(candles) < LOOKBACK_CANDLES:
        return None, "candles insuficientes"

    resistencia, suporte = detect_support_resistance(candles, 20)
    sma20 = moving_average(candles, 20)

    c1, c2 = candles[-2], candles[-1]
    signal, pa_reason = detect_price_action(c1, c2)

    if not signal:
        return None, "sem padrão de Price Action"

    # Confirmar se está perto de suporte/resistência
    if signal == "CALL" and abs(c2['low'] - suporte) <= (c2['high'] - c2['low']) * 0.5 and c2['close'] > sma20:
        return "CALL", f"{pa_reason} no suporte + acima da SMA20"
    if signal == "PUT" and abs(c2['high'] - resistencia) <= (c2['high'] - c2['low']) * 0.5 and c2['close'] < sma20:
        return "PUT", f"{pa_reason} na resistência + abaixo da SMA20"

    return None, "sem confluência suficiente"


# =============== ANALISE EURUSD-OTC (mantida) =================
def analyze_otc(candles, lookback=3):
    if not candles or len(candles) < lookback:
        return None, "candles insuficientes"

    last = candles[-lookback:]
    bullish = all(c['close'] > c['open'] for c in last)
    bearish = all(c['close'] < c['open'] for c in last)

    if bullish:
        return "CALL", f"{lookback} velas fortes consecutivas de alta"
    if bearish:
        return "PUT", f"{lookback} velas fortes consecutivas de baixa"
    return None, "sem tendência clara"


# ===============================================================
def normalize_candles(candles):
    normalized = []
    for c in candles:
        try:
            normalized.append({
                'open': float(c.get('open', c.get('o', 0))),
                'close': float(c.get('close', c.get('c', 0))),
                'high': float(c.get('max', c.get('h', c.get('high', 0)))),
                'low': float(c.get('min', c.get('l', c.get('low', 0)))),
                'from': c.get('from', c.get('from_time', None))
            })
        except Exception as e:
            print(f"[WARN] Erro ao normalizar candle: {e}")
    return normalized


def get_current_asset(now):
    weekday = now.weekday()  # 0 = segunda, 6 = domingo
    hour = now.hour

    if weekday < 5 and 9 <= hour < 11:  # EURUSD mercado real
        return "EURUSD"
    if 20 <= hour < 23:  # OTC
        return "EURUSD-OTC"
    return None


def main():
    print("===== BOT DE SINAIS IQ -> TELEGRAM =====")
    print("EURUSD (09h–11h, seg–sex): S/R + Price Action + SMA20")
    print("EURUSD-OTC (20h–23h, todos os dias): 3 velas fortes consecutivas")
    print("===================================================")

    connector = IQConnector(IQ_EMAIL, IQ_PASSWORD)
    if IQ_LIB_AVAILABLE:
        ok = connector.connect()
        if not ok:
            print("[ERRO] Falha ao conectar na IQ Option")
            return
    else:
        print("[ERRO] iqoptionapi não encontrado")
        return

    tz_brt = pytz.timezone("America/Sao_Paulo")
    last_signal_time = None
    pending_signal, pending_time = None, None

    while True:
        try:
            now = datetime.datetime.now(tz_brt)
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            asset = get_current_asset(now)

            if not asset:
                print(f"[{timestamp}] Fora do horário operacional. Aguardando...")
                time.sleep(CHECK_INTERVAL)
                continue

            candles = connector.get_candles(asset, CANDLE_INTERVAL, LOOKBACK_CANDLES)
            normalized = normalize_candles(candles)

            if asset == "EURUSD":
                signal, reason = analyze_eurusd_real(normalized)
            else:
                signal, reason = analyze_otc(normalized, 3)

            if signal and last_signal_time != normalized[-1]['from']:
                candle_start = datetime.datetime.fromtimestamp(normalized[-1]['from'], tz=tz_brt)
                next_entry = candle_start + datetime.timedelta(minutes=CANDLE_INTERVAL)
                send_time = next_entry - datetime.timedelta(minutes=1)

                pending_signal = {
                    "type": signal,
                    "reason": reason,
                    "next_entry": next_entry,
                    "asset": asset
                }
                pending_time = send_time
                last_signal_time = normalized[-1]['from']

                print(f"[{timestamp}] ({asset}) Sinal identificado: {signal} | Entrada às {next_entry.strftime('%H:%M:%S')}")

            elif pending_signal and now >= pending_time:
                txt = (
                    f"🔔 *SINAL CONFIRMADO* 🔔\n\n"
                    f"*Tipo:* {pending_signal['type']}\n"
                    f"*Ativo:* {pending_signal['asset']}\n"
                    f"*Intervalo:* {CANDLE_INTERVAL}M\n"
                    f"*Motivo:* {pending_signal['reason']}\n"
                    f"*Horário da entrada:* {pending_signal['next_entry'].strftime('%H:%M:%S')}\n\n"
                    f"ATÉ GALE 1\n\n"
                    f"💡 Recomendação: Operar sempre dentro dos horários de maior volatilidade."
                )
                telegram_send(TOKEN, CHAT_ID, txt)
                print(f"[{timestamp}] ENVIADO -> {pending_signal['type']} | {pending_signal['asset']}")
                pending_signal, pending_time = None, None
            else:
                print(f"[{timestamp}] ({asset}) Sem sinal ({reason})")

        except Exception as e:
            print(f"[ERRO LOOP] {e}\n{traceback.format_exc()}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERRO GERAL] {e}")
