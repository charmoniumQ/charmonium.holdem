import multiprocessing
from pprint import pprint
import threading
from typing import List, Tuple, Dict, Callable, cast

import bluff
import numpy as np
import scipy
import sklearn.tree
from tqdm import tqdm
import matplotlib.pyplot as plt
import graphviz

deck = bluff.Deck()


def int2card(card_id: int) -> bluff.Card:
    assert card_id < len(deck.ranks) * len(deck.suits)
    # card = bluff.Card("2s")
    # card._rank = deck.ranks[card_id % len(deck.ranks)]
    # card._suit = deck.suits[card_id // len(deck.ranks)]
    card = bluff.Card(deck.ranks[card_id % len(deck.ranks)] + deck.suits[card_id // len(deck.ranks)])
    return card

def game(_: int) -> bool:
    deal = list(map(int2card, np.random.permutation(52)[:7]))
    return (
        not bluff.Hand(deal[:6]).is_three_of_a_kind()
        and bluff.Hand(deal).is_three_of_a_kind()
    )
def threes(max_it: int = int(5e4)) -> None:
    pool = multiprocessing.Pool()
    threes = list(tqdm(pool.imap_unordered(game, range(max_it)), total=max_it))
    print(len(list(filter(bool, threes))) / len(threes))

seeded = False
def rank_hand(it: int) -> Tuple[List[int], int]:
    np.random.seed(it)
    hand = list(map(int2card, np.random.permutation(52)[:7]))
    return (
        hand,
        cast(int, bluff.Hand(hand).value),
    )

def create_ranking(max_it: int = int(5e4)) -> None:
    pool = multiprocessing.Pool()
    games = list(tqdm(pool.imap_unordered(rank_hand, range(max_it)), total=max_it))
    x_hands, y_vals = list(zip(*games))
    y_vals = np.array(y_vals)
    y_ranks = (np.arange(len(y_vals)) / len(y_vals) + 0.5 / len(y_vals))[y_vals.argsort().argsort()]
    y_logit = scipy.special.logit(y_ranks)

    assert(all(y_vals[y_ranks.argsort()] == sorted(y_vals)))

    linear_features: Dict[str, Callable[[Tuple[bluff.Card, bluff.Card]], int]] = {
        "suited" : lambda cards: int(cards[0].suit == cards[1].suit),
        "sep"    : lambda cards: int(abs(cards[0].numerical_rank - cards[1].numerical_rank)),
        "pair"   : lambda cards: int(cards[0].numerical_rank == cards[1].numerical_rank),
        "run"    : lambda cards: int(abs(cards[0].numerical_rank - cards[1].numerical_rank) == 1),
        "max"    : lambda cards: int(max([cards[0].numerical_rank, cards[1].numerical_rank])),
        "face"   : lambda cards: int(max([cards[0].numerical_rank, cards[1].numerical_rank]) > 8),
        "ace"    : lambda cards: int(max([cards[0].numerical_rank, cards[1].numerical_rank]) == 12),
        "low_max": lambda cards: int(max([cards[0].numerical_rank, cards[1].numerical_rank]) < 7),
    }
    x_linear_features = np.array([
        [feature_fn(hand) for feature_name, feature_fn in linear_features.items()]
        for hand in x_hands
    ])
    linear_model = sklearn.linear_model.Lasso()
    linear_model.fit(x_linear_features, y_logit)
    print(dict(zip(linear_features.keys(), map(lambda i: f'{i:.3f}', linear_model.coef_))))
    print(np.sqrt(sum((y_logit - linear_model.predict(x_linear_features))**2) / len(y_logit)))

    linear_features2: Dict[str, Callable[[Tuple[bluff.Card, bluff.Card]], int]] = {
        feature_name: feature_fn
        for feature_name, feature_fn in linear_features.items()
        if feature_name in {"suited", "pair", "run", "max"}
    }
    x_linear_features2 = np.array([
        [feature_fn(hand) for feature_name, feature_fn in linear_features2.items()]
        for hand in x_hands
    ])
    linear_model2 = sklearn.linear_model.Lasso()
    linear_model2.fit(x_linear_features2, y_logit)
    print(dict(zip(linear_features2.keys(), map(lambda i: f'{i:.3f}', linear_model2.coef_))))
    print(np.sqrt(sum((y_logit - linear_model2.predict(x_linear_features2))**2) / len(y_logit)))

    linear_features3: Dict[str, Callable[[Tuple[bluff.Card, bluff.Card]], int]] = {
        feature_name: feature_fn
        for feature_name, feature_fn in linear_features.items()
        if feature_name in {"pair", "max"}
    }
    x_linear_features3 = np.array([
        [feature_fn(hand) for feature_name, feature_fn in linear_features3.items()]
        for hand in x_hands
    ])
    linear_model3 = sklearn.linear_model.Lasso()
    linear_model3.fit(x_linear_features3, y_logit)
    print(dict(zip(linear_features3.keys(), map(lambda i: f'{i:.3f}', linear_model3.coef_))))
    print(np.sqrt(sum((y_logit - linear_model3.predict(x_linear_features3))**2) / len(y_logit)))

    tree_features: Dict[str, Callable[[Tuple[bluff.Card, bluff.Card]], int]] = {
        feature_name: feature_fn
        for feature_name, feature_fn in linear_features.items()
        if feature_name in {"suited", "sep", "max"}
    }
    x_tree_features = np.array([
        [feature_fn(hand) for feature_name, feature_fn in tree_features.items()]
        for hand in x_hands
    ])

    tree_model = sklearn.tree.DecisionTreeRegressor(max_depth=3)
    tree_model.fit(x_tree_features, y_logit)
    print(np.sqrt(sum((y_logit - tree_model.predict(x_tree_features))**2) / len(y_logit)))
    graphviz.Source(sklearn.tree.export_graphviz(
        tree_model,
        out_file=None,
        feature_names=list(tree_features.keys()),
        filled=True,
        rounded=True,
        special_characters=True
    )).view()
