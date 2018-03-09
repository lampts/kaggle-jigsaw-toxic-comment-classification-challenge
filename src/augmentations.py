import random

import numpy as np


class RandomCrop:

    def __init__(self, min_len=1.0, max_len=1.0):
        self.min_len = min_len
        self.max_len = max_len

    def transform(self, X):
        X = X.copy()
        X['comment_text'] = X['comment_text'].map(self._transform_text)
        return X

    def _transform_text(self, text):
        words = text.split()

        min_len = self.min_len if isinstance(self.min_len, int) else int(np.ceil(self.min_len * len(words)))
        max_len = self.max_len if isinstance(self.max_len, int) else int(np.ceil(self.max_len * len(words)))

        max_len = min(max_len, len(words))
        min_len = min(min_len, max_len)

        length = random.randint(min_len, max_len)
        offset = random.randint(0, len(words) - length)

        return ' '.join(words[offset:offset+length])


class RandomTranslation:

    def __init__(self, prob=0.2):
        self.prob = prob
        self.langs = ['de', 'fr', 'es']

    def transform(self, X):
        replace = np.random.rand(len(X))
        langs = np.random.choice(self.langs, size=len(X))

        res = X.copy()
        for i, r, lang in zip(X.index, replace, langs):
            if r < self.prob:
                res.loc[i, 'comment_text'] = X.loc[i, 'comment_text__%s' % lang]
        return res
