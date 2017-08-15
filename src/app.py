#!/usr/bin/env python3
# -*- coding: utf-8 -*-
u"""EquityCalculator"""

import json
import re
import itertools
import time
from deuces import Card, Deck, Evaluator, lookup
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
CARDS_RANK_HEX = {
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "T": "A",
    "J": "B",
    "Q": "C",
    "K": "D",
    "A": "E",
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
    if hands['conditions'] < best_hands['conditions']:
        is_draw = False
        is_best = False
    elif hands['conditions'] > best_hands['conditions']:
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

    best_hands['is_draw'] = is_draw
    best_hands['is_best'] = is_best

    return best_hands


def seven_hand_checker(param_hands):
    u"""
    :param string param_hands: ハンド　+ コミュニティの7枚のカード
    :return int best_hands: ハンドの中で最も強い組み合わせ
    """
    # todo: 適切なライブラリはないか？
    # start_time = time.time()
    global CARDS_RANK

    hands = param_hands.split(',')
    val_hands = []
    for val in hands:
        val_hands.append({"rank": list(val)[0], "suit": list(val)[1]})

    # ハンド + ボードをソートする
    val_hands = sorted(val_hands, key=lambda x: CARDS_SUIT[x['suit']])
    val_hands = sorted(val_hands, key=lambda x: CARDS_RANK[x['rank']], reverse=True)

    best_hands = hand_checker(val_hands)

    # best_hands = None
    # for sorted_hands in sorted_hands_list:
    #     if best_hands is None:
    #         best_hands = hand_checker(sorted_hands)
    #     else:
    #         hands = hand_checker(sorted_hands)
    #         best_hands = get_best_hands(best_hands, hands)

    return best_hands


def hand_checker(param_hands):
    u"""
    ハンドランク判定メソッド
    :param list param_hands: ハンド
    :return dict: 判定結果
    """
    # todo: そもそもハンド + ボード で一気に判定できない？
    global CARDS_RANK
    global CARDS_SUIT
    # start_time = time.time()

    # todo: rank_num の要素数無意味に15個とってしまっている
    rank_nums = [0] * 15
    suit_nums = [0] * 4
    group_counts = [0] * 7
    is_straight = False
    is_flush = False
    is_pair = False
    hands_rank = "0x"

    # ペア判定
    # ランクごとのカードの枚数を取得
    for hands in param_hands:
        rank_nums[CARDS_RANK[hands['rank']]] += 1
        suit_nums[CARDS_SUIT[hands['suit']]] += 1

    for pair in range(2, len(group_counts)):
        group_counts[pair] = rank_nums.count(pair)

    # ペア判定
    if group_counts.count(0) != 7:
        is_pair = True

    # ストレート判定
    for i in range(0, 2):
        if CARDS_RANK[param_hands[i]['rank']] - CARDS_RANK[param_hands[i+4]['rank']] == 4:
            is_straight = True
            break
        # 1番大きい数字がA且つ2番目に大きい数字が5且つペアではない = Wheel
        elif CARDS_RANK[param_hands[i]['rank']] == 14 and CARDS_RANK[param_hands[i+1]['rank']] == 5:
            is_straight = True
            break

    # フラッシュ判定
    if max(group_counts) > 4:
       is_flush = True

    # ハイカード判定
    if is_flush is False and is_straight is False and is_pair is False:
        hands_rank += '2'
        for i in range(0, 4):
            hands_rank += CARDS_RANK_HEX[param_hands[i]['rank']]
        return int(hands_rank, 16)

    # todo:ベンチのため、

    # ロイヤル判定
    # ストフラ
    if is_flush and is_straight:
        hands_rank += '800000'
    # フラッシュ
    elif is_flush:
        hands_rank += '500000'
    # ストレート
    elif is_straight:
        hands_rank += '400000'
    # クアッズ
    elif group_counts[4] > 0:
        hands_rank += '700000'
    # フル
    # トリップス
    elif group_counts[3] > 0:
        hands_rank += '300000'
    # ツーペア
    elif group_counts[2] == 2:
        hands_rank += '200000'
    # ワンペア
    else:
        hands_rank += '100000'

    return int(hands_rank, 16)


def get_hand(hands, community):
    return None


def get_community_simulation(param_com):
    u"""
    ボード生成メソッド
    :param string param_com: ボード
    :return list com_list: ボードとなるハンドの一覧:
    """
    global cards

    # list型への変換は先で行う
    community = param_com.split(',')


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

    community = post_param['community']
    com_sim = get_community_simulation(community)

    # todo: このループ3回やってるんだよなぁ・・・
    for key, value in post_param.items():
        if re.compile("player*").search(key):
            win_count[key] = 0

    for com_val in com_sim:
        hands_compare = []
        draw_players = []
        best_hands = None

        # todo: このループ3回やってるんだよなぁ・・・
        for key, value in post_param.items():
            if re.compile("player*").search(key):
                hands = value["hands"] + ',' + ','.join(com_val)
                hands_rank = seven_hand_checker(hands)
                hands_compare.append(hands_rank)

        for value in hands_compare:
            if best_hands is None:
                best_hands = value
            #
            # else:
            #     hands = value
            #     best_hands = get_best_hands(best_hands, hands)
            #
            #     # ドローのプレイヤーを配列にぶち込む
            #     if best_hands['is_draw'] and best_hands['is_best'] and len(draw_players) == 0:
            #         draw_players.append(best_hands['player'])
            #         draw_players.append(hands['player'])
            #     elif best_hands['is_draw'] and best_hands['is_best']:
            #         draw_players.append(hands['player'])
            #     elif best_hands['is_best']:
            #         draw_players = []

        # winner処理
        # if len(draw_players) == 0:
        #     win_count[best_hands['player']] += 1
        # # ドロー処理
        # else:
        #     for player in draw_players:
        #         win_count[player] += 1 / len(draw_players)

        loop_count += 1

    # todo: このループ3回やってるんだよなぁ・・・
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


@route('/test', method="POST")
def poker_odds_api():
    u"""
    deuces
    :return HTTPResponse:
    """
    global cards
    win_rate = {}
    win_count = {}
    loop_count = 0
    post_param = request.json
    start_time = time.time()

    community = post_param['community']
    community = community.split(',')
    board = []
    for com in community:
        board.append(Card.new(com))

    for key, value in post_param.items():
        if re.compile("player*").search(key):
            hand = []
            for val in value["hands"].split(','):
                hand.append(Card.new(val))
            Card.print_pretty_cards(board + hand)


    # # todo: このループ3回やってるんだよなぁ・・・
    # for key, value in post_param.items():
    #     if re.compile("player*").search(key):
    #         win_count[key] = 0
    #
    # end_time = time.time()
    # interval = end_time - start_time
    # print(str(interval) + "秒")
    # print(loop_count)

    # Responseパラメータを作る
    response_body = json.dumps(win_rate, sort_keys=True, indent=4)
    response = HTTPResponse(status=200, body=response_body)
    response.set_header('Content-Type', 'application/json')

    return response



run(host='localhost', port=8080)