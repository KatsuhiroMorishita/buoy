#! /usr/bin/env python3
# -*- coding:utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        buoy
# Purpose:   定水深ブイの制御パラメータを求める。
#
# Author:      morishita
#
# Created:     01/02/2014
# Copyright:   (c) morishita 2014
# Licence:     MIT
#-------------------------------------------------------------------------------


# パラメータ
g = 9.80                    # 重力加速度[m/s^2]
density = 1035              # 周囲流体密度[kg/m^3]
m = 20.0                    # buoy mass [kg]
delta_t = 0.01              # 計算時間ステップ[s]
z_target = 10.0             # 目標深度[m]
z_0 = 0.0                   # 初期深度[m]
delta_V_rate_max = 0.00007  # 体積変化量の時間変化率の限界[m^3/s]. 変数名がおかしい気がしてきた。
delta_V_max = 0.00024       # 最大体積変化量[m^3]
delta_V_min = -0.00016      # 最小体積変化量[m^3]
delta_V_small = abs(delta_V_max)    # 体積変化量の内、小さい方を採用。制御パラメータの上限値の設定に利用する。
if delta_V_small > abs(delta_V_min):
    delta_V_small = abs(delta_V_min)


def frange(begin, end, step):
    """ 指定範囲での等差数列を返す
    """
    ans = []
    n = begin
    while n < end:
        ans.append(n)
        n += step
    return ans

def calc(times, k1, k2):
    """　時間と座標を計算し、その結果を返す
    Return:
        <list<list>>
    """
    ans = []
    z = z_0         # 初期座標[m]
    v = 0.0         # 初速度[m/s]. 流体に対する相対速度ではないので注意.
    delta_V = 0.0

    for t in times:
        # 計算
        delta_z = z - z_target
        delta_V_ideal = k1 * delta_z + k2 * v           # 制御量としての体積変化量[m^3]
        #print(delta_V_ideal)

        if delta_V_ideal > delta_V_max:                 # 制御量の制限
            delta_V_ideal = delta_V_max
        if delta_V_ideal < delta_V_min:
            delta_V_ideal = delta_V_min
        #print(delta_V_ideal)

        diff = delta_V_ideal - delta_V                  # 体積変化率が機械的限界を超えていれば修正
        if abs(diff / delta_t) > delta_V_rate_max:
            #print(diff)
            if diff < 0:
                delta_V -= delta_V_rate_max * delta_t
            elif diff > 0:
                delta_V += delta_V_rate_max * delta_t
        else:
            delta_V = delta_V_ideal

        buoyant_force = density * g * delta_V# - m * g  # 浮力（mgを無視すると、中性浮力からのスタートを仮定したことと同義となる）
        a = (buoyant_force) / m                         # 加速度
        # 計算値の保存
        _ans = [t, z, a, v, delta_V, buoyant_force]
        ans.append(_ans)
        # 更新
        v = v + a * delta_t                             # "v += a * delta_t"と書いても同じ
        z = z + v * delta_t
    return ans

def check_01(result):
    """ 結果の判断
    目標深度との差分の２乗平均を計算し、テキトーな閾値で識別する。
    """
    r = 0
    for a_result in result:
        z = a_result[1]
        r += pow(z_target - z, 2.0)
    r /= len(result)

    msg = "hoge," + str(r)
    if r < 36.0:
        print(r)
        return (True, msg)
    else:
        return (False, msg)

def check_02(result):
    """ 結果の判断
    オーバーシュートを利用する。
    ただし、初期深度が0.0であることが前提です。
    """
    z_max = 0.0
    for a_result in result:
        z = a_result[1]
        if z_max < z:
            z_max = z

    over = abs(z_max - z_target)    # 必ずしもオーバーするとは限らないのだけど、まぁいいよね？
    msg = "over," + str(over)
    if over < 0.5:
        #print(z_max)
        return (True, msg)
    else:
        return (False, msg)

def get_time_constant(result):
    """ 時定数を計算して返す
    """
    z_max = 0.0
    z_th = (z_target - z_0) * 0.95 + z_0 # 本当は0.63くらい
    print(z_th)
    t = 0
    for a_result in result:
        z = a_result[1]
        if z_th < z:
            t = a_result[0]
            break

    return t


def main():
    k1_search_width = 9 * delta_V_small / abs(z_0 - z_target)   # 体積変化の物理的限界を考慮 （制御量が飽和しないための目安）
    k2_search_width = 3 * delta_V_small / 0.5                   # 移動速度の制限を0.5[m/s]  （制御量が飽和しないための目安）
    k1_step = k1_search_width / 10                          # PIDのPの係数の計算ステップ
    k2_step = k2_search_width / 10                          # PIDのDの係数の計算ステップ
    times = frange(0.0, 70.0, delta_t)                     # 演算時間のリスト. frange(計算開始時刻[s], 計算終了時刻[s], 計算時間ステップ[s])
    count = 0
    for k1 in frange(-k1_search_width, 0.0, k1_step):
        for k2 in frange(-k2_search_width, 0.0, k2_step):
            count += 1
            print("now: {0}, {1}".format(k1, k2))
            result = calc(times, k1, k2)                    # 計算
            check_flag, value = check_02(result)            # 良さげならば保存
            if check_flag:                                  # 良さげな結果のみを選別
                print("OK!")
                print(str(value))
                ct = get_time_constant(result)
                # ファイルへ保存
                with open("summary.csv", "a", encoding="utf-8-sig") as fw:
                    fw.write("{0},{1},{2},{3}\n".format(k1, k2, ct, value))
                fname = "log_k1{0:.8f}_k2{1:.8f}.csv".format(k1, k2)
                with open(fname, "w", encoding="utf-8-sig") as fw:  # for log to file
                    for a_result in result:
                        for data in a_result:
                            fw.write(str(data) + ",")
                        fw.write("\n")

if __name__ == '__main__':
    main()
