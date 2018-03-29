import pybitflyer as pybitflyer
import time
import sys
import datetime
import average
import line

public_api = pybitflyer.API()
api = pybitflyer.API(api_key="YOUR_API_KEY", api_secret="YOUR_API_SECRET")


def isSuperBusyOrStop(status):
    if status == "SUPER BUSY" or status == "STOP":
        return True


def clearPosition():
    pos = api.getpositions(product_code="FX_BTC_JPY")
    if len(pos) != 0:

        if pos[0]["side"] == "BUY":
            side = "SELL"
        else:
            side = "BUY"

        size_sum = 0
        for position in pos:
            size_sum += position["size"]

        api.sendchildorder(product_code="FX_BTC_JPY", child_order_type="MARKET", side=side, size=size_sum)


def clearPositionAndExit():
    print("Clear position start")

    api.cancelallchildorders(product_code="FX_BTC_JPY")

    count = 0
    while count < 10:
        clearPosition()

        count += 1
        time.sleep(30)

        print(count)

    print("Position cleared, exit")
    line.notify("EXITするよ")

    sys.exit()


def placeIFOCO(side, price_now):

    if side == "BUY":
        return api.sendparentorder(order_method="IFDOCO", parameters=([
            {"product_code": "FX_BTC_JPY", "condition_type": "LIMIT", "side": "BUY", "size": size, "price": price_now - range_ifd},
            {"product_code": "FX_BTC_JPY", "condition_type": "LIMIT", "side": "SELL", "size": size, "price": price_now - range_ifd + range_oco_profit},
            {"product_code": "FX_BTC_JPY", "condition_type": "STOP", "side": "SELL", "size": size, "trigger_price": price_now - range_ifd - range_oco_loss}
        ]))

    if side == "SELL":
        return api.sendparentorder(order_method="IFDOCO", parameters=([
            {"product_code": "FX_BTC_JPY", "condition_type": "LIMIT", "side": "SELL", "size": size, "price": price_now + range_ifd},
            {"product_code": "FX_BTC_JPY", "condition_type": "LIMIT", "side": "BUY", "size": size, "price": price_now + range_ifd - range_oco_profit},
            {"product_code": "FX_BTC_JPY", "condition_type": "STOP", "side": "BUY", "size": size, "trigger_price": price_now + range_ifd + range_oco_loss}
        ]))


def confirmWinOrLose():
    executions = api.getexecutions(product_code="FX_BTC_JPY")[:8]
    latest_side = executions[0]["side"]

    size_total = 0
    entry_prices = []
    exit_prices = []
    for execution in executions:
        if execution["side"] == latest_side:
            exit_prices.append(execution["price"])
            size_total += execution["size"]

        else:
            entry_prices.append(execution["price"])
            size_total -= execution["size"]
            if size_total == 0:
                break

    entry_price = int(sum(entry_prices) / len(entry_prices))
    exit_price = int(sum(exit_prices) / len(exit_prices))

    if latest_side == "SELL":
        profit = exit_price - entry_price

    else:
        profit = entry_price - exit_price

    if profit > 0:
        judge = "WIN"
    else:
        judge = "LOSE"

    return [profit, judge]


def calcProfitAndLoss(win_list, lose_list):
    win_count = len(win_list)
    lose_count = len(lose_list)
    if win_count == 0 and lose_count == 0:
        print("error")

    win_percentage = round(((win_count / (win_count + lose_count)) * 100), 1)
    total_profit = sum(win_list) + sum(lose_list)

    return [win_count, lose_count, win_percentage, total_profit]


def measureTimeInMarketOrder():
    start_time = time.time()

    # 買い注文のレスポンスが辞書型でない（注文が通っていない）場合
    if not isinstance((api.sendchildorder(product_code="FX_BTC_JPY", child_order_type="MARKET", side="BUY", size=0.001)), dict):
        response_time = 10
        return response_time

    # 売り注文のレスポンスが辞書型でない場合は注文が通るまで繰り返す
    if not isinstance((api.sendchildorder(product_code="FX_BTC_JPY", child_order_type="MARKET", side="SELL", size=0.001)), dict):
        while True:
            if isinstance((api.sendchildorder(product_code="FX_BTC_JPY", child_order_type="MARKET", side="SELL", size=0.001)), dict):
                break

        response_time = 10
        return response_time

    response_time = time.time() - start_time
    return response_time


def hedgeDelay():
    time_delay_start = datetime.datetime.now()
    print("！！！！遅延を検知しました！！！！({})".format(time_delay_start))
    line.notify("遅延を検知しました")

    api.cancelallchildorders(product_code="FX_BTC_JPY")
    print("オーダーをキャンセルしました。")

    time.sleep(10)

    clearPosition()

    time.sleep(60)

    clearPosition()

    response_time = measureTimeInMarketOrder()
    print("レスポンスタイム：{}".format(response_time))

    while response_time > 6:
        time.sleep(60)

        response_time = measureTimeInMarketOrder()
        print("レスポンスタイム：{}".format(response_time))

    time_delay_end = datetime.datetime.now()
    print("！！！！遅延を脱出しました！！！！({})".format(time_delay_end))
    line.notify("遅延モード終了")


while True:
    # オーダー数、エントリー数、クリア数を初期化
    count_buy_order = 0
    count_sell_order = 0
    entry_count = 0
    clear_count = 0

    # 勝ちと負けの値幅
    win_range_list = []
    lose_range_list = []

    size = 0.001
    ifd_range_percentage = 0.0008
    oco_range_percentage_profit = 0.004
    oco_range_percentage_loss = 0.003

    message = "No entry"

    # オーダースイッチをオフに初期化（-1:オフ, 1:オン）
    order_switch = -1

    # メンテナンス時間を設定
    maintenance_start = datetime.time(4, 15)
    maintenance_end = datetime.time(4, 25)
    maintenance_time = 600

    loop_count = 1
    loop_time = 61
    operation_start_time = time.time()
    operated_time = 0
    while operated_time < 3600:
        sleep_time = 30 - loop_time
        if sleep_time > 0:
            time.sleep(sleep_time)

        # メンテナンス時間なら回避する
        if maintenance_start < datetime.datetime.now().time() < maintenance_end:
            line.notify("メンテナンススタート")

            api.cancelallchildorders(product_code="FX_BTC_JPY")

            clearPosition()

            time.sleep(60)

            clearPosition()

            time.sleep(maintenance_time - 60)

            line.notify("メンテナンス終了")

            # オーダースイッチをオフに初期化
            order_switch = -1

        loop_start_time = time.time()

        health_status = api.gethealth(product_code="FX_BTC_JPY")["status"]
        print("health status: {}".format(health_status))
        if isSuperBusyOrStop(health_status):
            loop_time = time.time() - loop_start_time
            loop_count += 1
            operated_time = time.time() - operation_start_time
            continue

        # 2つ以上のポジションを持ってたら総量チェック(規定値より多かったらクリア)
        positions = api.getpositions(product_code="FX_BTC_JPY")
        pos_count = len(positions)
        if pos_count >= 2:
            size_sum = 0
            for position in positions:
                size_sum += position["size"]

            if size_sum > size:
                clear_count += 1
                print("ポジション持ちすぎだからいったんCLEARしときますね({}回目)".format(clear_count))
                api.cancelallchildorders(product_code="FX_BTC_JPY")

                clearPosition()

                loop_time = time.time() - loop_start_time
                loop_count += 1
                operated_time = time.time() - operation_start_time
            continue

        # 親注文の状態を確認
        order_state = api.getparentorders(product_code="FX_BTC_JPY")[0]["parent_order_state"]

        # stateがCANCELEDかREJECTEDでポジション持ってたらおかしいからとりあえずCLEAR
        # IFが約定してからexecutedに反映されるまでの間にキャンセルしたパターン？
        if order_state == "CANCELED" or order_state == "REJECTED":
            if pos_count != 0:
                clear_count += 1
                print("CANCELEDかREJECTEDなのにポジション持ってたからCLEARするってばよ({}回目)".format(clear_count))
                print(order_state)

                clearPosition()

        elif order_state == "COMPLETED":
            if pos_count != 0:
                print("...COMPLETEDなのにポジありだったよ！...")

            # COMPLETEDでswitchが1なら直近取引の勝敗を確認して表示する
            if order_switch == 1:
                entry_count += 1
                count_order_sum = count_buy_order + count_sell_order

                price_diff, judgement = confirmWinOrLose()

                if judgement == "WIN":
                    win_range_list.append(price_diff)
                else:
                    lose_range_list.append(price_diff)

                win_count, lose_count, win_percentage, sum_profit = calcProfitAndLoss(win_range_list, lose_range_list)
                entry_success_rate = round(((entry_count / count_order_sum) * 100), 1)

                message = "{} 勝 {} 敗, 勝率: {}%, 損益通算: {}円, エントリー成功率: {}%(総エントリー数: {}), クリア数：{}"\
                    .format(win_count, lose_count, win_percentage, sum_profit, entry_success_rate, count_order_sum, clear_count)

                print("-" * 90)
                print("{}: {}円".format(judgement, price_diff))
                print(message)
                print("-" * 90)

                order_switch *= -1

            operated_time = time.time() - operation_start_time
            if operated_time > 3600:
                continue

        # stateがACTIVEの場合
        else:
            # IFのLIMITが約定済みでOCO待ちの状態
            if api.getparentorders(product_code="FX_BTC_JPY")[0]["executed_size"] == size:
                print("Waiting OCO...")
                loop_count += 1
                loop_time = time.time() - loop_start_time
                continue

            # IFのLIMITも約定してないからオーダーキャンセル
            else:
                api.cancelallchildorders(product_code="FX_BTC_JPY")
                order_switch *= -1
                print("エントリーできなかったからオーダーキャンセルするよ")

                # キャンセル時に稼働時間が規定以上だった場合はcontinue
                operated_time = time.time() - operation_start_time
                if operated_time > 3600:
                    continue

        entry_side, compared_price = average.checkSMA()
        if entry_side == "BUY":
            price = public_api.board(product_code="FX_BTC_JPY")["mid_price"]
            start = time.time()

            range_ifd = int(price * ifd_range_percentage)
            range_oco_profit = int(price * oco_range_percentage_profit)
            range_oco_loss = int(price * oco_range_percentage_loss)
            if isinstance(placeIFOCO(entry_side, price), dict):
                order_switch *= -1
                count_buy_order += 1

                print("<BUY ordered: その {} (指値幅:{}, 利確幅:{}, 損切り幅{})>".format(count_buy_order, range_ifd,
                                                                             range_oco_profit, range_oco_loss))

            else:
                print("オーダーが通らなかったよ！")
                print(api.getparentorders(product_code="FX_BTC_JPY")[0]["parent_order_state"])

            elapsed_time = time.time() - start

            print("レスポンスタイム:{}".format(elapsed_time))

            if elapsed_time > 5:
                hedgeDelay()

        elif entry_side == "SELL":
            price = public_api.board(product_code="FX_BTC_JPY")["mid_price"]
            start = time.time()

            range_ifd = int(price * ifd_range_percentage)
            range_oco_profit = int(price * oco_range_percentage_profit)
            range_oco_loss = int(price * oco_range_percentage_loss)
            if isinstance(placeIFOCO(entry_side, price), dict):
                order_switch *= -1
                count_sell_order += 1
                print("<SELL ordered: その {} (指値幅:{}, 利確幅:{}, 損切り幅{})>".format(count_sell_order, range_ifd,
                                                                              range_oco_profit, range_oco_loss))

            else:
                print("オーダーが通らなかったよ！")
                print(api.getparentorders(product_code="FX_BTC_JPY")[0]["parent_order_state"])

            elapsed_time = time.time() - start

            print("レスポンスタイム:{}".format(elapsed_time))

            if elapsed_time > 5:
                hedgeDelay()

        loop_time = time.time() - loop_start_time
        print("{} loop time: {}".format(loop_count, loop_time))

        loop_count += 1
        operated_time = time.time() - operation_start_time

    line.notify(message)



