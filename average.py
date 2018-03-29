import requests
import json
import numpy as np
import pandas as pd
import time
import sys

short_term = 6
mid_term = 36

periods = ["60", "300", "1800"]

query = {"periods": ','.join(periods)}

url = "https://api.cryptowat.ch/markets/bitflyer/btcfxjpy/ohlc"

# [UNIX timestamp, 始値, 高値, 安値, 終値, 出来高]

def getPriceArrays():
    start = time.time()

    response = json.loads(requests.get(url, params=query).text)["result"]

    count = 0
    while len(response) == 0:
        count += 1
        print("レスポンスエラー({})".format(count))

        if count > 4:
            print("価格の取得が5連続エラーだったからEXITしとくよ")
            sys.exit()

        time.sleep(3)

        response = json.loads(requests.get(url).text)["result"]

    prices_1minute = np.array(response["60"][-mid_term:]).astype(np.int32)
    prices_5minute = np.array(response["300"][-mid_term:]).astype(np.int32)
    prices_30minute = np.array(response["1800"][-mid_term:]).astype(np.int32)

    prices_1minute_close = prices_1minute[:, 4]
    prices_5minute_close = prices_5minute[:, 4]
    prices_30minute_close = prices_30minute[:, 4]

    print("価格取得時間：{}".format(time.time() - start))

    return [prices_1minute_close, prices_5minute_close, prices_30minute_close]


def calcSMA(price_array):
    average_short_before = int(np.average(price_array[-6:-1]))
    average_short_now = int(np.average(price_array[-5:]))

    average_mid_before = int(np.average(price_array[:25]))
    average_mid_now = int(np.average(price_array[-25:]))

    return [average_short_before, average_short_now, average_mid_before, average_mid_now]


def calcEMA(price_array):
    s = pd.Series(price_array)
    ema5 = s.ewm(span=5).mean().astype(int)
    ema35 = s.ewm(span=35).mean().astype(int)

    # print("短期：{}, {}, 中期：{}, {}".format(ema5[25], ema5[24], ema25[25], ema25[24]))

    print(ema35)


def detectSignal(short_before, short_now, mid_before, mid_now):
    if short_before < short_now and mid_before < mid_now and mid_now < short_now:
        signal = "BUY"
    elif short_now < short_before and mid_now < mid_before and short_now < mid_now:
        signal = "SELL"
    else:
        signal = "NONE"
    return signal


def checkSMA():
    price_array_1, price_array_5, price_array_30 = getPriceArrays()

    [short_before_1, short_now_1, mid_before_1, mid_now_1] = calcSMA(price_array_1)
    [short_before_5, short_now_5, mid_before_5, mid_now_5] = calcSMA(price_array_5)

    signal_1minute = detectSignal(short_before_1, short_now_1, mid_before_1, mid_now_1)
    signal_5minute = detectSignal(short_before_5, short_now_5, mid_before_5, mid_now_5)

    print("1分足：{}".format(signal_1minute))
    print("5分足：{}".format(signal_5minute))

    if signal_1minute == "BUY" and signal_5minute == "BUY":
        side = "BUY"

    elif signal_1minute == "SELL" and signal_5minute == "SELL":
        side = "SELL"

    else:
        side = "No Signal"

    return [side, short_now_1]


if __name__ == "__main__":
    while True:

        prices_1, prices_5, prices_30 = getPriceArrays()

        calcEMA(prices_5)

        time.sleep(60)
