#!/user/bin/env python3
# -*- coding: utf-8 -*-
u"""EquityCalculator"""

import json
import re
import itertools
import time
from bottle import route, run, request, HTTPResponse

cards = []
CARDS_SUIT = {
    "s": 0,
    "h": 1,
    "d": 2,
    "c": 3
}
CARDS_RANK = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "T": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}
HAND_CONDITIONS ={
    0: "High Card",
    1: "One Pair",
    2: "Two Pair",
    3: "Three of a Kind",
    4: "Straight",
    5: "Flush",
    6: "Full House",
    7: "Four of a Kind",
    8: "Straight Flush",
    9: "Royal Flush",
}


def gen_cards():
    u"""
    デッキ構築メソッド
    """
    global cards
    nums = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K"]
    suits = ["s", "h", "d", "c"]
    cards = []
    for suit in suits:
        for num in nums:
            cards.append(num + suit)


def remove_cards(post_param):
    u"""
    :param list post_param:　ハンド + ボード
    """
    global cards

    for key, value in post_param.items():
        if re.compile("player*").search(key):
            hands = value["hands"].split(',')
            for hand in hands:
                cards.remove(hand)

        if key == "community" and (len(value) or value is None):
            community = value.split(',')
            for com in community:
                cards.remove(com)



def get_best_hands(best_hands, hands):
    u"""
    :param list best_hands: 今までのベストハンド
    :param list hands: 比較対象のハンド
    :return list best_hands: ハンド + ボード
    """

    is_draw = True
    is_best = True

    # ハンドランクで判定
    if hands['conditions'] > best_hands['conditions']:
        best_hands = hands
        is_draw = False
        is_best = True
    # 同一ランクの場合、役の数値->キッカーの数値で判定
    elif hands['conditions'] == best_hands['conditions']:
        # 役の数値で判定
        for i in range(0, len(hands['conditions_rank'])):
            if hands['conditions_rank'][i] > best_hands['conditions_rank'][i]:
                best_hands = hands
                is_draw = False
                is_best = True
                break
            elif hands['conditions_rank'][i] < best_hands['conditions_rank'][i]:
                is_draw = False
                is_best = False
                break
        # キッカーで判定
        if is_draw:
            for i in range(0, len(hands['kicker_rank'])):
                # 役の数値
                if hands['kicker_rank'][i] > best_hands['kicker_rank'][i]:
                    best_hands = hands
                    is_draw = False
                    is_best = True
                    break
                elif hands['kicker_rank'][i] < best_hands['kicker_rank'][i]:
                    is_draw = False
                    is_best = False
                    break

    elif hands['conditions'] < best_hands['conditions']:
        is_draw = False
        is_best = False

    best_hands['is_draw'] = is_draw
    best_hands['is_best'] = is_best

    return best_hands


def seven_hand_checker(param_hands):
    u"""
    :param list param_hands: ハンド　+ コミュニティの7枚のカード
    :return list best_hands: ハンドの中で最も強い組み合わせ
    """
    global CARDS_RANK
    val_hands = []
    for val in param_hands:
        val_hands.append({"rank": list(val)[0], "suit": list(val)[1]})

    # ハンド + ボードをソートする
    val_hands = sorted(val_hands, key=lambda x: CARDS_SUIT[x['suit']])
    val_hands = sorted(val_hands, key=lambda x: CARDS_RANK[x['rank']], reverse=True)

    sorted_hands_list = list(itertools.combinations(val_hands, 5))

    best_hands = None
    for sorted_hands in sorted_hands_list:
        if best_hands is None:
            best_hands = hand_checker(sorted_hands)
        else:
            hands = hand_checker(sorted_hands)
            best_hands = get_best_hands(best_hands, hands)

    return best_hands


def hand_checker(param_hands):
    u"""
    ハンドランク判定メソッド
    :param list param_hands: ハンド
    :return dict: 判定結果
    """
    global CARDS_RANK
    rank_nums = [0] * 15
    suit_nums = [0] * 4
    group_counts = [0] * 5
    is_straight = False
    is_flush = False
    hands_rank = {
        "conditions": 0,
        "conditions_rank": [],
        "kicker_rank": [],
    }

    # ペア判定
    # ランクごとのカードの枚数を取得
    for hands in param_hands:
        rank_nums[CARDS_RANK[hands['rank']]] += 1

    # ペア判定結果
    for pair in range(2, len(group_counts)):
        group_counts[pair] = rank_nums.count(pair)

    # ペアなしの判定
    if group_counts.count(0) == 5:
        # ストレート判定
        if CARDS_RANK[param_hands[0]['rank']] - CARDS_RANK[param_hands[4]['rank']] == 4:
            is_straight = True
        # 1番大きい数字がA且つ2番目に大きい数字が5且つペアではない = Wheel
        elif CARDS_RANK[param_hands[0]['rank']] == 14 and CARDS_RANK[param_hands[1]['rank']] == 5:
            is_straight = True

        # フラッシュ判定
        for hands in param_hands:
            suit_nums[CARDS_SUIT[hands['suit']]] += 1

        if suit_nums.count(5) > 0:
            is_flush = True

        # ロイヤル判定
        if is_flush and is_straight and CARDS_RANK[param_hands[4]['rank']] == 14:
            hands_rank['conditions'] = 9
            hands_rank['conditions_rank'] = [CARDS_RANK[param_hands[0]['rank']]]
            hands_rank['kicker_rank'] = []
        # ストフラ
        elif is_flush and is_straight:
            hands_rank['conditions'] = 8
            hands_rank['conditions_rank'] = [CARDS_RANK[param_hands[0]['rank']]]
            hands_rank['kicker_rank'] = []
        # フラッシュ
        elif is_flush:
            hands_rank['conditions'] = 5
            hands_rank['conditions_rank'] = sorted([i for i, x in enumerate(rank_nums) if x == 1], reverse=True)
            hands_rank['kicker_rank'] = []
        # ストレート
        elif is_straight:
            hands_rank['conditions'] = 4
            hands_rank['conditions_rank'] = [CARDS_RANK[param_hands[0]['rank']]]
            hands_rank['kicker_rank'] = []
        # ハイカード
        else:
            hands_rank['conditions'] = 0
            hands_rank['conditions_rank'] = sorted([i for i, x in enumerate(rank_nums) if x == 1], reverse=True)
            hands_rank['kicker_rank'] = []
    # ペア系判定
    else:
        # クアッズ
        if group_counts[4] > 0:
            hands_rank['conditions'] = 7
            hands_rank['conditions_rank'] = [rank_nums.index(4)]
            hands_rank['kicker_rank'] = [rank_nums.index(1)]
        # フルハウス
        elif group_counts[3] > 0 and group_counts[2] > 0:
            hands_rank['conditions'] = 6
            hands_rank['conditions_rank'] = [rank_nums.index(3), rank_nums.index(2)]
            hands_rank['kicker_rank'] = []
        # トリップス
        elif group_counts[3] > 0:
            hands_rank['conditions'] = 3
            hands_rank['conditions_rank'] = [rank_nums.index(3)]
            hands_rank['kicker_rank'] = [i for i, x in enumerate(rank_nums) if x == 1]
        # ツーペア
        elif group_counts[2] == 2:
            hands_rank['conditions'] = 2
            hands_rank['conditions_rank'] = sorted([i for i, x in enumerate(rank_nums) if x == 2], reverse=True)
            hands_rank['kicker_rank'] = [rank_nums.index(1)]
        # ワンペア
        elif group_counts[2] == 1:
            hands_rank['conditions'] = 1
            hands_rank['conditions_rank'] = [rank_nums.index(2)]
            hands_rank['kicker_rank'] = sorted([i for i, x in enumerate(rank_nums) if x == 1], reverse=True)

    return hands_rank


def get_hand(hands, community):
    return None


def get_community_simulation(community):
    global cards

    com_list = []
    if len(community[0]) == 0:
        gen_list = list((itertools.combinations(cards, 5)))
    else:
        gen_list = list((itertools.combinations(cards, (5 - len(community)))))

    for gen_val in gen_list:
        list_val = list(gen_val)
        if len(community[0]) == 0:
            com_list.append(list_val)
        else:
            com_list.append(community + list_val)

    return com_list

@route('/', method="POST")
def equity_calculator():
    u"""
    rootメソッド
    :return HTTPResponse:
    """
    global cards
    win_rate = {}
    win_count = {}
    loop_count = 0
    post_param = request.json
    start_time = time.time()

    # デッキを生成
    gen_cards()
    # すでに使われいているカードをデッキから排除
    remove_cards(post_param)

    community = post_param['community'].split(',')
    com_sim = get_community_simulation(community)

    for key, value in post_param.items():
        if re.compile("player*").search(key):
            win_count[key] = 0

    for com_val in com_sim:
        hands_compare = []
        draw_players = []
        best_hands = None

        for key, value in post_param.items():
            if re.compile("player*").search(key):
                hands = value["hands"].split(',') + com_val
                #print(hands)
                hands_rank = seven_hand_checker(hands)
                hands_rank['player'] = key
                hands_rank['is_best'] = True
                hands_rank['is_draw'] = True
                hands_compare.append(hands_rank)
                # win_count[key] = 0

        for value in hands_compare:
            if best_hands is None:
                best_hands = value

            else:
                hands = value
                best_hands = get_best_hands(best_hands, hands)

                # ドローのプレイヤーを配列にぶち込む
                if best_hands['is_draw'] and best_hands['is_best'] and len(draw_players) == 0:
                    draw_players.append(best_hands['player'])
                    draw_players.append(hands['player'])
                elif best_hands['is_draw'] and best_hands['is_best']:
                    draw_players.append(hands['player'])
                elif best_hands['is_best']:
                    draw_players = []

        # winner処理
        if len(draw_players) == 0:
            win_count[best_hands['player']] += 1
        # ドロー処理
        else:
            for player in draw_players:
                win_count[player] += 1 / len(draw_players)

        loop_count += 1

    for key, value in post_param.items():
        if re.compile("player*").search(key):
            win_rate[key] = round(win_count[key]/loop_count, 4)

    end_time = time.time()
    interval = end_time - start_time
    print(str(interval) + "秒")
    print(loop_count)

    # Responseパラメータを作る
    response_body = json.dumps(win_rate, sort_keys=True, indent=4)
    response = HTTPResponse(status=200, body=response_body)
    response.set_header('Content-Type', 'application/json')

    return response

run(host='localhost', port=8080)