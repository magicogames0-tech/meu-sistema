#!/usr/bin/env python3
# iq2.py
# Bot IQ Option -> Telegram
# Pronto para rodar direto pelo Python, sem variáveis de ambiente

import time
import datetime
import traceback
import requests
import pytz
import statistics
import random

# ======= CONFIGURAÇÃO DIRETA =======
IQ_EMAIL = "magicogames0@gmail.com"
IQ_PASSWORD = "david64920169"
TOKEN = "7830300218:AAHv5jzXNu0DTwlbS_4esVLWJYM7LAx2Jic"
CHAT_ID = -1002068593318

CANDLE_INTERVAL = 5    # minutos
LOOKBACK_CANDLES = 30  # usado para suporte/resistência e média móvel
CHECK_INTERVAL = 20    # segundos entre verificações
# ===================================

try:
    from iqoptionapi.stable_api import IQ_Option
    IQ_LIB_AVAILABLE = True
except Exception:
    IQ_LIB_AVAILABLE = False

# =================== Funções ===================
def telegram_send(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=data, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def detect_support_resistance(candles, n=20):
    highs = [c['high'] for c in candles[-n:]]
    lows = [c['low'] for c in candles[-n:]]
    return max(highs), min(lows)

def moving_average(candles, period=20):
    closes = [c['close'] for c in candles[-period:]]
    return statistics.mean(closes)

def detect_price_action(c1, c2):
    if c2['close'] > c2['open'] and c1['close'] < c1['open'] and c2['close'] > c1['open'] and c2['open'] < c1['close']:
        return "CALL", "Engolfo de Alta"
    if c2['close'] < c2['open'] and c1['close'] > c1['open'] and c2['close'] < c1['open'] and c2['open'] > c1['close']:
        return "PUT", "Engolfo de Baixa"
    corpo = abs(c2['close'] - c2['open']) if c2['close'] is not None and c2['open'] is not None else 0
    pavio_inferior = min(c2['open'], c2['close']) - c2['low'] if c2['low'] is not None else 0
    pavio_superior = c2['high'] - max(c2['open'], c2['close']) if c2['high'] is not None else 0
    if corpo > 0 and pavio_inferior > 2 * corpo and pavio_superior < corpo:
        return "CALL", "Martelo (Pinbar de Alta)"
    if corpo > 0 and pavio_superior > 2 * corpo and pavio_inferior < corpo:
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
    if signal == "CALL" and abs(c2['low'] - suporte) <= (c2['high'] - c2['low']) * 0.5 and c2['close'] > sma20:
        return "CALL", f"{pa_reason} no suporte + acima da SMA20"
    if signal == "PUT" and abs(c2['high'] - resistencia) <= (c2['high'] - c2['low']) * 0.5 and c2['close'] < sma20:
        return "PUT", f"{pa_reason} na resistência + abaixo da SMA20"
    return None, "sem confluência suficiente"

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
    weekday = now.weekday()
    hour = now.hour
    if weekday < 5 and 9 <= hour < 18:
        return "EURUSD"
    if 14 <= hour < 23:
        return "EURUSD-OTC"
    return None

# =================== IQ Connector ===================
class IQConnector:
    def __init__(self, email, password):
        self.api = None
        self.connected = False
        if IQ_LIB_AVAILABLE:
            try:
                self.api = IQ_Option(email, password)
            except Exception as e:
                print(f"[ERRO] Falha ao inicializar IQ_Option: {e}")

    def connect(self, max_retries=8):
        if not IQ_LIB_AVAILABLE:
            print("[ERRO] iqoptionapi não está instalado.")
            return False
        attempt = 0
        while attempt < max_retries:
            try:
                print(f"[INFO] Tentativa conexão IQ (attempt {attempt+1})...")
                self.connected, reason = self.api.connect()
                print(f"[DEBUG] Conectado: {self.connected} | Motivo: {reason}")
                if self.connected:
                    return True
            except Exception as e:
                print(f"[ERRO] Exceção ao conectar: {e}")
            sleep_for = min(5 * (2 ** attempt), 300) + random.uniform(0, 3)
            print(f"[INFO] Backoff: dormindo {sleep_for:.1f}s antes de nova tentativa.")
            time.sleep(sleep_for)
            attempt += 1
        print("[ERRO] Máximo de tentativas de conexão atingido.")
        return False

    def get_candles(self, asset, interval_minutes, n):
        if not self.connected:
            raise RuntimeError("Não conectado à IQ Option")
        timeframe = interval_minutes * 60
        candles = self.api.get_candles(asset, timeframe, n, time.time())
        if not candles:
            raise RuntimeError(f"Nenhuma vela retornada para {asset}")
        return candles

# =================== LOOP PRINCIPAL ===================
def main():
    print("===== BOT DE SINAIS IQ -> TELEGRAM =====")
    print("EURUSD (09h–18h, seg–sex): S/R + Price Action + SMA20")
    print("EURUSD-OTC (14h–23h, todos os dias): 3 velas fortes consecutivas")
    print("===================================================")

    connector = IQConnector(IQ_EMAIL, IQ_PASSWORD)
    if not connector.connect():
        print("[ERRO] Não foi possível conectar à IQ Option.")
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
