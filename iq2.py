import os
import time
import datetime
import traceback
import requests
import pytz  # <<< adicionado

# ========= CONFIG =========
IQ_EMAIL = os.getenv("IQ_EMAIL")
IQ_PASSWORD = os.getenv("IQ_PASSWORD")
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))  # Default 0 se não existir

CANDLE_INTERVAL = 5    # minutos
LOOKBACK_CANDLES = 3   # quantas velas seguidas para confirmar tendência
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


def analyze_candles_for_signal(candles, lookback=3):
    if not candles or len(candles) < lookback:
        return None, "candles insuficientes"

    last = candles[-lookback:]
    bullish = True
    bearish = True

    for c in last:
        corpo = abs(c['close'] - c['open'])
        high = c.get('high', max(c['close'], c['open']))
        low = c.get('low', min(c['close'], c['open']))

        maximo = max(c['close'], c['open'])
        minimo = min(c['close'], c['open'])

        pavio_superior = high - maximo
        pavio_inferior = minimo - low
        range_total = high - low if high > low else corpo

        if range_total == 0 or corpo < 0.3 * range_total:
            return None, "candle fraco"

        if pavio_superior > corpo or pavio_inferior > corpo:
            return None, "pavio longo demais"

        if not (c['close'] > c['open']):
            bullish = False
        if not (c['close'] < c['open']):
            bearish = False

    if bullish:
        return "CALL", f"{lookback} velas fortes consecutivas de alta"
    if bearish:
        return "PUT", f"{lookback} velas fortes consecutivas de baixa"
    return None, "sem tendência clara"


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
    """Define qual ativo usar baseado no horário de Brasília"""
    weekday = now.weekday()  # 0 = segunda, 6 = domingo
    hour = now.hour

    # Mercado real -> apenas seg a sex, 09h–13h
    if weekday < 5 and 9 <= hour < 13:
        return "EURUSD"

    # OTC -> todos os dias, 20h–23h
    if 20 <= hour < 23:
        return "EURUSD-OTC"

    # Fora do horário
    return None


def main():
    print("===== BOT DE SINAIS IQ -> TELEGRAM =====")
    print("Configuração: Intervalo de 5M | Lookback 3 velas fortes")
    print("Horários: Mercado Real 09h–13h | OTC 20h–23h (BRT)")
    print("========================================")

    connector = IQConnector(IQ_EMAIL, IQ_PASSWORD)
    if IQ_LIB_AVAILABLE:
        ok = connector.connect()
        if ok:
            print("[OK] Conectado à IQ Option")
        else:
            print("[ERRO] Falha ao conectar na IQ Option")
            return
    else:
        print("[ERRO] iqoptionapi não encontrado, instale com: pip install git+https://github.com/Lu-Yi-Hsun/iqoptionapi.git")
        return

    last_signal_time = None
    pending_signal = None
    pending_time = None

    tz_brt = pytz.timezone("America/Sao_Paulo")  # <<< Timezone fixo BRT

    while True:
        try:
            now = datetime.datetime.now(tz_brt)  # <<< Agora sempre em horário de Brasília
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            asset = get_current_asset(now)

            if not asset:
                print(f"[{timestamp}] Fora do horário operacional. Aguardando...")
                time.sleep(CHECK_INTERVAL)
                continue

            candles = connector.get_candles(asset, CANDLE_INTERVAL, LOOKBACK_CANDLES)
            normalized = normalize_candles(candles)
            signal, reason = analyze_candles_for_signal(normalized, LOOKBACK_CANDLES)

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

                print(f"[{timestamp}] ({asset}) Sinal identificado: {signal} | Entrada às {next_entry.strftime('%H:%M:%S')} | Envio agendado às {send_time.strftime('%H:%M:%S')}")

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
                res = telegram_send(TOKEN, CHAT_ID, txt)
                print(f"[{timestamp}] ENVIADO -> {pending_signal['type']} | {pending_signal['asset']} | Entrada {pending_signal['next_entry'].strftime('%H:%M:%S')} | Telegram: {res.get('ok')}")
                pending_signal = None
                pending_time = None
            else:
                print(f"[{timestamp}] ({asset}) Sem sinal ({reason})")

        except Exception as e:
            tb = traceback.format_exc()
            print(f"[ERRO LOOP] {e}\n{tb}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERRO GERAL] {e}")
