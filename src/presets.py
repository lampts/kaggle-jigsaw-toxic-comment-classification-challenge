from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import FunctionTransformer, Imputer
from sklearn.pipeline import make_pipeline, make_union
from sklearn.metrics import roc_auc_score

from scipy.special import expit

from src.util.estimators import MultiProba, SimpleAverage, WeightedAverage, OnExtendedData, Pipeline, Bagged
from src.util.preprocessors import OnColumn, DropColumns, SelectColumns, AvgGroupsColumns, Union
from src.meta import input_file
from src import augmentations, meta

import src.models.keras as keras_models
import src.models.tensorflow as tf_models
import src.models.boosting as boost_models
from src.models.rotation_forest import RotationForest

import lightgbm as lgb

from kgutil.models.keras import KerasRNN

from hyperopt import hp
import numpy as np

from keras.optimizers import Adam, SGD


api_columns = ['UNSUBSTANTIAL', 'OBSCENE', 'LIKELY_TO_REJECT', 'SEVERE_TOXICITY', 'TOXICITY', 'INFLAMMATORY', 'ATTACK_ON_AUTHOR', 'SPAM', 'INCOHERENT', 'ATTACK_ON_COMMENTER']


def param_search_space(**space):
    def decorator(fn):
        fn.param_search_space = space
        return fn
    return decorator


def features(*features):
    def decorator(fn):
        fn.features = features
        return fn
    return decorator


def submodels(*submodels):
    def decorator(fn):
        fn.submodels = submodels
        return fn
    return decorator


## Test models

@features('clean1')
def test_rnn():
    return KerasRNN(
        num_epochs=1, batch_size=3000, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=8,
            rnn_layers=[8],
            mlp_layers=[]
        )
    )


@features('clean1', 'num2')
def test_rnn_feats():
    return KerasRNN(
        num_epochs=1, batch_size=3000, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=8,
            rnn_layers=[8],
            mlp_layers=[]
        )
    )


@features('clean1', 'sentiment1')
def test_rnn_ext():
    return OnExtendedData(KerasRNN(
        num_epochs=1, batch_size=3000, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=8,
            rnn_layers=[8],
            mlp_layers=[]
        )
    ))


@features('clean1')
def test_tf():
    return tf_models.TfModel(
        num_epochs=1, batch_size=3000,
        model_opts=dict(emb_size=8, rnn_size=8)
    )


@features('multilang_clean4_corrected_fasttext')
def test_rnn_aug():
    return keras_models.AugmentedModel(
        num_epochs=3, batch_size=3000, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        train_augmentations=[augmentations.RandomCrop(min_len=0.5, max_len=100)],
        predict_augmentations=[augmentations.RandomCrop(min_len=0.5, max_len=100)],
        predict_passes=2,
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=8,
            rnn_layers=[8],
            mlp_layers=[]
        )
    )

## L1 models


def basic_lr():
    return make_pipeline(
        OnColumn('comment_text', CountVectorizer(max_features=1000, min_df=5)),
        MultiProba(LogisticRegression())
    )


def lr2():
    return make_pipeline(
        OnColumn('comment_text', make_union(
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=10000),
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=50000)
        )),
        MultiProba(LogisticRegression())
    )


@features('clean1', 'num1')
def lr3():
    return make_pipeline(
        make_union(
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=10000)),
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=50000)),
            DropColumns(['comment_text']),
        ),
        MultiProba(LogisticRegression())
    )


@features('clean2', 'num1')
def lr3_cl2():
    return make_pipeline(
        make_union(
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=10000)),
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=50000)),
            DropColumns(['comment_text']),
        ),
        MultiProba(LogisticRegression())
    )


@features('clean1', 'num1', 'num2', 'sentiment1')
def lr3_more_feats():
    return make_pipeline(
        make_union(
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=10000)),
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=50000)),
            DropColumns(['comment_text']),
        ),
        MultiProba(LogisticRegression())
    )


@features('clean1', 'num1')
def lr3_more_ngrams():
    return make_pipeline(
        make_union(
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=10000)),
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=60000)),
            DropColumns(['comment_text']),
        ),
        MultiProba(LogisticRegression())
    )


@features('clean2', 'num1', 'num2', 'sentiment1')
def lr4():
    return make_pipeline(
        make_union(
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=10000)),
            OnColumn('comment_text', TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=60000)),
            DropColumns(['comment_text']),
        ),
        MultiProba(LogisticRegression())
    )


def lgb_tst():
    return make_pipeline(
        OnColumn('comment_text', make_union(
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=100),
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=500)
        )),
        boost_models.LgbOnKBestModel()
    )


def lgb1():
    return make_pipeline(
        OnColumn('comment_text', make_union(
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=50000),
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=50000)
        )),
        boost_models.LgbOnKBestModel()
    )


@features('atanas')
def lgb2():
    return make_pipeline(
        OnColumn('comment_text', make_union(
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=50000),
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=50000)
        )),
        boost_models.LgbOnKBestModel()
    )


@features('multilang_clean4')
def lgb3():
    return make_pipeline(
        OnColumn('comment_text', make_union(
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='word',
                token_pattern=r'\w{1,}',
                stop_words='english',
                ngram_range=(1, 1),
                max_features=50000),
            TfidfVectorizer(
                sublinear_tf=True,
                strip_accents='unicode',
                analyzer='char',
                stop_words='english',
                ngram_range=(2, 6),
                max_features=50000)
        )),
        boost_models.LgbOnKBestModel(params={'learning_rate': 0.1}, rounds={
            'toxic': 300,
            'severe_toxic': 100,
            'obscene': 160,
            'threat': 160,
            'insult': 140,
            'identity_hate': 160
        })
    )


@param_search_space(
    text_emb_size=hp.quniform('text_emb_size', 8, 32, 4),
    rnn_layer_size=hp.quniform('rnn_layer_size', 4, 16, 4),
    mlp_layer_size=hp.quniform('mlp_layer_size', 4, 16, 4),
    mlp_dropout=hp.uniform('mlp_dropout', 0.0, 0.7),
)
def basic_rnn(text_emb_size=32, rnn_layer_size=32, mlp_layer_size=64, mlp_dropout=0.3):
    return KerasRNN(
        num_epochs=10, batch_size=2000, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=int(text_emb_size),
            rnn_layers=[int(rnn_layer_size)],
            mlp_dropout=mlp_dropout, mlp_layers=[int(mlp_layer_size)]
        )
    )


def rnn_pretrained():
    return KerasRNN(
        num_epochs=5, batch_size=200, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=300, text_emb_file=input_file('glove.42B.300d.txt'), text_emb_trainable=False, text_emb_dropout=0.2,
            rnn_layers=[32],
            mlp_dropout=0.3, mlp_layers=[64]
        )
    )


@param_search_space(
    text_emb_dropout=hp.uniform('text_emb_dropout', 0.1, 0.6),
    rnn_layer_size=hp.quniform('rnn_layer_size', 16, 64, 16),
    rnn_bidi=hp.choice('rnn_bidi', [True, False]),
    rnn_pooling=hp.choice('rnn_pooling', [None, 'avg', 'max', 'avgmax']),
    mlp_layer_size=hp.quniform('mlp_layer_size', 32, 128, 32),
    mlp_layer_num=hp.quniform('mlp_layer_num', 1, 2, 1),
    mlp_dropout=hp.uniform('mlp_dropout', 0.1, 0.6),
)
def rnn_pretrained_2(text_emb_dropout=0.2, rnn_layer_size=32, rnn_bidi=True, rnn_pooling='avgmax', mlp_layer_size=64, mlp_layer_num=1, mlp_dropout=0.3):
    return KerasRNN(
        num_epochs=10, batch_size=200, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=300, text_emb_file=input_file('glove.42B.300d.txt'), text_emb_trainable=False, text_emb_dropout=text_emb_dropout,
            rnn_layers=[int(rnn_layer_size)], rnn_bidi=rnn_bidi, rnn_pooling=rnn_pooling,
            mlp_dropout=mlp_dropout, mlp_layers=[int(mlp_layer_size)] * int(mlp_layer_num)
        )
    )


def rnn_pretrained_3(text_emb_dropout=0.29, rnn_layer_size=32, rnn_bidi=True, rnn_pooling='avgmax', mlp_layer_size=96, mlp_layer_num=1, mlp_dropout=0.16):
    return KerasRNN(
        num_epochs=10, batch_size=500, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=300, text_emb_file=input_file('glove.42B.300d.txt'), text_emb_trainable=False, text_emb_dropout=text_emb_dropout,
            rnn_layers=[int(rnn_layer_size)], rnn_bidi=rnn_bidi, rnn_pooling=rnn_pooling,
            mlp_dropout=mlp_dropout, mlp_layers=[int(mlp_layer_size)] * int(mlp_layer_num)
        )
    )


def cudnn_lstm_1():
    return KerasRNN(
        num_epochs=20, batch_size=500, external_metrics=dict(roc_auc=roc_auc_score),
        compile_opts=None,
        model_fn=keras_models.cudnn_lstm_1,
        model_opts=dict(
            text_emb_size=25, text_emb_file=input_file('glove.twitter.27B.25d.txt'), text_emb_trainable=False
        )
    )


def cudnn_lstm_2():
    return KerasRNN(
        num_epochs=30, batch_size=800, external_metrics=dict(roc_auc=roc_auc_score),
        early_stopping_opts=dict(patience=3),
        compile_opts=None,
        model_fn=keras_models.cudnn_lstm_1,
        model_opts=dict(
            lr=1e-3,
            rnn_layers=[64, 64], rnn_dropout=0.15,
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_dropout=0.25
        )
    )


@features('clean1', 'num1')
def rnn_pretrained_4(text_emb_dropout=0.3, rnn_layer_size=32, rnn_layer_num=2, rnn_bidi=True, rnn_pooling='avgmax', mlp_layer_size=96, mlp_layer_num=1, mlp_dropout=0.15):
    return KerasRNN(
        num_epochs=20, batch_size=500, external_metrics=dict(roc_auc=roc_auc_score),
        early_stopping_opts=dict(patience=3),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_trainable=False, text_emb_dropout=text_emb_dropout,
            rnn_layers=[int(rnn_layer_size)] * int(rnn_layer_num), rnn_bidi=rnn_bidi, rnn_pooling=rnn_pooling, rnn_cell='gru', rnn_dropout=0.1, rnn_cudnn=True,
            mlp_dropout=mlp_dropout, mlp_layers=[int(mlp_layer_size)] * int(mlp_layer_num)
        )
    )


@features('clean1', 'num1')
def rnn_pretrained_5(text_emb_dropout=0.3, rnn_layer_size=48, rnn_layer_num=2, rnn_bidi=True, rnn_pooling='avgmax', rnn_dropout=0.15, mlp_layer_size=96, mlp_layer_num=2, mlp_dropout=0.2):
    return KerasRNN(
        num_epochs=30, batch_size=500, external_metrics=dict(roc_auc=roc_auc_score),
        max_text_len=200,
        early_stopping_opts=dict(patience=3),
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_opts=dict(
            out_activation='sigmoid',
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_trainable=False, text_emb_dropout=text_emb_dropout,
            rnn_layers=[int(rnn_layer_size)] * int(rnn_layer_num), rnn_bidi=rnn_bidi, rnn_pooling=rnn_pooling, rnn_cell='gru', rnn_dropout=rnn_dropout, rnn_cudnn=True,
            mlp_dropout=mlp_dropout, mlp_layers=[int(mlp_layer_size)] * int(mlp_layer_num)
        )
    )


def cudnn_lstm_2_ext():
    return OnExtendedData(max_len=70, decay=0.7, model=KerasRNN(
        num_epochs=30, batch_size=800, external_metrics=dict(roc_auc=roc_auc_score),
        early_stopping_opts=dict(patience=3),
        compile_opts=None,
        model_fn=keras_models.cudnn_lstm_1,
        model_opts=dict(
            lr=1e-3,
            rnn_layers=[64, 64], rnn_dropout=0.15,
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_dropout=0.25
        )
    ))


def cudnn_lstm_3_ext():
    return OnExtendedData(max_len=70, decay=0.7, n_samples=80000, model=KerasRNN(
        num_epochs=30, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post',
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.cudnn_lstm_1,
        model_opts=dict(
            lr=1e-3,
            rnn_layers=[64, 64], rnn_dropout=0.15,
            mlp_layers=[96], mlp_dropout=0.3,
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_dropout=0.25
        )
    ))


def bigru_gmp_1():
    return KerasRNN(
        num_epochs=50, batch_size=800, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='gmp',
            out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.4
        )
    )


@features('clean2_corrected_fasttext')
def bigru_gmp_2():
    return KerasRNN(
        num_epochs=50, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='gmp',
            out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5
        )
    )


@features('clean2_corrected_fasttext')
def bigru_sterby_2():
    return KerasRNN(
        num_epochs=50, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.4,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5
        )
    )


@features('clean2_corrected_fasttext', 'num1')
def bigru_sterby_2_num():
    return KerasRNN(
        num_epochs=50, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.35,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5
        )
    )


@features('clean2_corrected_fasttext', 'num1', 'sentiment1')
def bigru_sterby_2_num_sent():
    return KerasRNN(
        num_epochs=50, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.35,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5
        )
    )


@features('clean2_corrected_fasttext', 'num1', 'num2', 'sentiment1')
def bigru_sterby_2_num_sent_longer():
    return KerasRNN(
        num_epochs=50, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        num_text_words=50000, max_text_len=150,
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.35,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5
        )
    )


@param_search_space(
    out_dropout=hp.uniform('out_dropout', 0.2, 0.6),
    text_emb_dropout=hp.uniform('text_emb_dropout', 0.3, 0.7),
    lr=hp.loguniform('lr', -9.2, -4.6),
    rnn_size=hp.quniform('rnn_size', 32, 128, 16),
)
@features('clean2_corrected_fasttext', 'num1', 'num2', 'sentiment1')
def bigru_sterby_2_num_sent_longer_rand(out_dropout=0.35, text_emb_dropout=0.5, lr=1e-3, rnn_size=80):
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=500), dict(num_epochs=10, batch_size=1000), dict(num_epochs=40, batch_size=2000)],
        external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        num_text_words=50000, max_text_len=150,
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=lr,
            rnn_size=rnn_size, rnn_pooling='sterby',
            out_dropout=out_dropout,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=text_emb_dropout, text_emb_rand_std=0.3,
        )
    )


@features('clean2_corrected_fasttext')
def bigru_sterby_2_ext():
    return OnExtendedData(max_len=70, decay=0.8, n_samples=40000, model=KerasRNN(
        num_epochs=50, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.4,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5
        )
    ))


@features('clean2_corrected_fasttext', 'num1')
def bigru_sterby_3():
    return KerasRNN(
        num_epochs=50, batch_size=1000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_2,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.35, num_layer_size=16,
            text_emb_fix_size=300, text_emb_fix_file=input_file('crawl-300d-2M.vec'), text_emb_free_size=8, text_emb_dropout=0.5
        )
    )


@features('clean2_bpe50k', 'num1', 'num2', 'sentiment1')
def bigru_sterby_4_bpe50k():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=500), dict(num_epochs=10, batch_size=1000), dict(num_epochs=40, batch_size=2000)],
        external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        max_text_len=150,
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.35,
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op50000.d300.w2v.txt'), text_emb_dropout=0.5, text_emb_rand_std=0.3,
        )
    )


@features('clean2_bpe25k', 'num1')
def bigru_sterby_4_bpe25k():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=500), dict(num_epochs=10, batch_size=1000), dict(num_epochs=40, batch_size=2000)],
        external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', text_tokenizer_opts=dict(filters='', lower=False),
        max_text_len=150,
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.35,
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op25000.d300.w2v.txt'), text_emb_dropout=0.5, text_emb_rand_std=0.3,
        )
    )


@features('clean2_bpe10k', 'num1', 'num2', 'sentiment1')
def bigru_sterby_4_bpe10k():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=500), dict(num_epochs=10, batch_size=1000), dict(num_epochs=40, batch_size=2000)],
        external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        max_text_len=150,
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.35,
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op10000.d300.w2v.txt'), text_emb_dropout=0.5, text_emb_rand_std=0.3,
        )
    )


def bigru_cnn_1():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=2, batch_size=512)],
        external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('glove.42B.300d.txt'), text_emb_dropout=0.4
        )
    )


@features('clean2')
def bigru_cnn_2():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=5, batch_size=256), dict(num_epochs=40, batch_size=512)],
        external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.2, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.4
        )
    )


@features('clean2_no_punct')
def bigru_cnn_3():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=10, batch_size=1024)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.3, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        )
    )


@features('clean2_no_punct')
def bigru_rcnn_1():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=10, batch_size=1024)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_rcnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, rnn_dense_activation='relu', out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        )
    )


@features('clean2_expand_no_punct', 'num1', 'ind1')
def bigru_rcnn_2():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=10, batch_size=1024)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_rcnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, rnn_dense_activation='relu', out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        )
    )


@features('clean2_expand_no_punct', 'num1', 'ind1')
def bigru_rcnn_3():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=20, batch_size=1024)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_rcnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3,
            mlp_layers=[64], mlp_dropout=0.2, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        )
    )


@features('clean2_expand_no_punct_lemmatize', 'num1', 'ind1')
def bigru_rcnn_4():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=20, batch_size=1024)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_rcnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3,
            mlp_layers=[64], mlp_dropout=0.2, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        )
    )


@features('clean2_expand_no_punct_lemmatize', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_4():
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.3, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        )
    )


@param_search_space(
    out_dropout=hp.uniform('out_dropout', 0.2, 0.6),
    text_emb_dropout=hp.uniform('text_emb_dropout', 0.3, 0.7),
    lr=hp.loguniform('lr', -9.2, -4.6),
    rnn_size=hp.quniform('rnn_size', 32, 128, 16),
)
@features('clean2_expand_no_punct_lemmatize', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_sterby_5(out_dropout=0.35, text_emb_dropout=0.5, lr=1e-3, rnn_size=80):
    return KerasRNN(
        train_schedule=[dict(num_epochs=3, batch_size=500), dict(num_epochs=10, batch_size=1000), dict(num_epochs=40, batch_size=2000)],
        external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        num_text_words=50000, max_text_len=200,
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=lr,
            rnn_size=rnn_size, rnn_pooling='sterby',
            out_dropout=out_dropout,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=text_emb_dropout, text_emb_rand_std=0.3,
        )
    )


@features('clean2_no_punct', 'num1')
def bigru_cnn_5_aug():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre',
        num_text_words=100000, max_text_len=100,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.2, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomCrop(min_len=0.9, max_len=100)],
        predict_augmentations=[augmentations.RandomCrop(min_len=0.9, max_len=100)],
        predict_passes=4,
    )



@features('clean2_corrected_fasttext', 'num1')
def bigru_sterby_2_num_aug():
    return keras_models.AugmentedModel(
        num_epochs=50, batch_size=1000, predict_batch_size=2048, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.4, text_emb_rand_std=0.1
        ),
        train_augmentations=[augmentations.RandomCrop(min_len=0.9, max_len=100)],
        predict_augmentations=[augmentations.RandomCrop(min_len=0.9, max_len=100)],
        predict_passes=8,
    )


@features('multilang_clean3_corrected_fasttext', 'num1')
def bigru_sterby_2_num_aug2():
    return keras_models.AugmentedModel(
        num_epochs=50, batch_size=1000, predict_batch_size=2048, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=5e-4,
            rnn_size=80, rnn_pooling='sterby',
            out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.4, text_emb_rand_std=0.05
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3)],
    )


@features('multilang_clean3_corrected_fasttext', 'num1')
def bigru_sterby_3_num_aug2():
    return keras_models.AugmentedModel(
        num_epochs=50, batch_size=1000, predict_batch_size=2048, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=5e-4,
            rnn_size=128, rnn_pooling='sterby',
            out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.4, text_emb_rand_std=0.05
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3)],
    )


@features('multilang_clean3_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_4_aug2():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.3, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3)],
    )


@features('multilang_clean3_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_4_aug3():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=150,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.3, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3), augmentations.RandomCrop(min_len=0.9, max_len=150)],
        predict_augmentations=[augmentations.RandomCrop(min_len=0.9, max_len=150)],
        predict_passes=8,
    )


@features('multilang_clean3_corrected_fasttext', 'num1')
def bigru_sterby_3_num_aug3():
    return keras_models.AugmentedModel(
        num_epochs=50, batch_size=1000, predict_batch_size=2048, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=5e-4,
            rnn_size=128, rnn_pooling='sterby',
            out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.4, text_emb_rand_std=0.05
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3), augmentations.RandomCrop(min_len=0.9, max_len=150)],
        predict_augmentations=[augmentations.RandomCrop(min_len=0.9, max_len=150)],
        predict_passes=8,
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_4_aug4():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.3, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_5_aug4():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=160, rnn_dropout=0.3, out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.5, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3), augmentations.RandomCrop(min_len=1.0, max_len=200)],
        predict_augmentations=[augmentations.RandomCrop(min_len=1.0, max_len=200)],
        predict_passes=8,
    )


@features('multilang_clean4_corrected_fasttext', 'num1')
def bigru_sterby_3_num_aug4():
    return keras_models.AugmentedModel(
        num_epochs=50, batch_size=1000, predict_batch_size=2048, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=5e-4,
            rnn_size=128, rnn_pooling='sterby',
            out_dropout=0.3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.4, text_emb_rand_std=0.05
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_4_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=128, rnn_dropout=0.3, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_5_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=144, rnn_dropout=0.3, out_dropout=0.2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_6_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_bpe50k', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_6_bpe50k_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=80, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2,
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op50000.d300.w2v.txt'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('atanas', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_6_atanas_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=64, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_bpe50k', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_7_bpe50k_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2, conv_activation='elu',
            num_layers=[32], num_dropout=0.2, num_activation='elu',
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op50000.d300.w2v.txt'), text_emb_dropout=0.4, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_7_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2, conv_activation='elu',
            num_layers=[32], num_dropout=0.2, num_activation='elu',
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('atanas', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_7_atanas_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2, conv_activation='elu',
            num_layers=[32], num_dropout=0.2, num_activation='elu',
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomConcat(0.1)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_sterby_2_aug6(out_dropout=0.35, text_emb_dropout=0.5, lr=1e-3, rnn_size=128):
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=500), dict(num_epochs=10, batch_size=1000), dict(num_epochs=40, batch_size=2000)],
        predict_batch_size=4000, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post',
        num_text_words=50000, max_text_len=150,
        early_stopping_opts=dict(patience=6),
        compile_opts=None,
        model_fn=keras_models.bigru_1,
        model_opts=dict(
            lr=lr,
            rnn_size=rnn_size, rnn_pooling='sterby',
            out_dropout=out_dropout,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=text_emb_dropout, text_emb_rand_std=0.3,
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_bpe50k', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_8_bpe50k_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=5, batch_size=128), dict(num_epochs=5, batch_size=256), dict(num_epochs=5, batch_size=512), dict(num_epochs=5, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2, conv_activation='elu',
            num_layers=[32], num_dropout=0.2, num_activation='elu',
            mlp_layers=[64], mlp_dropout=0.2, mlp_activation='elu',
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op50000.d300.w2v.txt'), text_emb_dropout=0.4, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_9_aug6_twitter():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2, conv_activation='elu',
            num_layers=[32], num_dropout=0.2, num_activation='elu',
            mlp_layers=[32], mlp_dropout=0.2, mlp_activation='elu',
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_dropout=0.3, text_emb_rand_std=0.2
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_twitter', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_9_aug6_twitter2():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2, conv_activation='elu',
            num_layers=[32], num_dropout=0.2, num_activation='elu',
            mlp_layers=[32], mlp_dropout=0.2, mlp_activation='elu',
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_dropout=0.3, text_emb_rand_std=0.2
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_dpcnn_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.dpcnn,
        model_opts=dict(
            lr=1e-3,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_bpe50k', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_dpcnn_bpe50k_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=300,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.dpcnn,
        model_opts=dict(
            lr=1e-3,
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op50000.d300.w2v.txt'), text_emb_dropout=0.4, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.35), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_dpcnn_aug7_pre():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.dpcnn,
        model_opts=dict(
            lr=1e-3, filter_nr=80,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.4), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_bpe50k', 'num1', 'num2', 'ind1', 'sentiment1')
def dpcnn_bpe50k_aug7_pre():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=25, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=300,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.dpcnn,
        model_opts=dict(
            lr=1e-3, filter_nr=96,
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op50000.d300.w2v.txt'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.4), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_twitter', 'num1', 'num2', 'ind1', 'sentiment1')
def dpcnn_twitter_aug7_pre():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=15, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=200,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.dpcnn,
        model_opts=dict(
            lr=1e-3, filter_nr=96,
            text_emb_size=200, text_emb_file=input_file('glove.twitter.27B.200d.txt'), text_emb_dropout=0.3, text_emb_rand_std=0.2
        ),
        train_augmentations=[augmentations.RandomTranslation(0.4), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_corrected_fasttext', 'num1', 'num2', 'ind1', 'sentiment1')
def dpcnn_fasttext_aug7_pre():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=25, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='pre', text_padding='pre', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=100000, max_text_len=300,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.dpcnn,
        model_opts=dict(
            lr=1e-3, filter_nr=128,
            text_emb_size=300, text_emb_file=input_file('crawl-300d-2M.vec'), text_emb_dropout=0.45, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.4), augmentations.RandomConcat(0.05)],
    )


@features('multilang_clean4_bpe50k', 'num1', 'num2', 'ind1', 'sentiment1')
def bigru_cnn_9_bpe50k_aug6():
    return keras_models.AugmentedModel(
        train_schedule=[dict(num_epochs=3, batch_size=128), dict(num_epochs=4, batch_size=256), dict(num_epochs=4, batch_size=512), dict(num_epochs=4, batch_size=1024), dict(num_epochs=10, batch_size=2048)],
        predict_batch_size=1024, external_metrics=dict(roc_auc=roc_auc_score),
        text_truncating='post', text_padding='post', ignore_columns=['comment_text__de', 'comment_text__fr', 'comment_text__es'],
        num_text_words=50000, max_text_len=300,
        early_stopping_opts=dict(patience=5),
        compile_opts=None,
        model_fn=keras_models.bigru_cnn_1,
        model_opts=dict(
            lr=1e-3,
            rnn_size=96, rnn_dropout=0.3, out_dropout=0.2, rnn_layers=2, conv_activation='elu',
            mlp_layers=[64], mlp_dropout=0.2, mlp_activation='elu',
            text_emb_size=300, text_emb_file=input_file('en.wiki.bpe.op50000.d300.w2v.txt'), text_emb_dropout=0.4, text_emb_rand_std=0.3
        ),
        train_augmentations=[augmentations.RandomTranslation(0.3), augmentations.RandomConcat(0.1)],
    )


# L2


@submodels('cudnn_lstm_2', 'rnn_pretrained_3')
def l2_lr():
    return make_pipeline(
        DropColumns(['comment_text']),
        FunctionTransformer(expit),
        MultiProba(LogisticRegression())
    )


@submodels('cudnn_lstm_2', 'rnn_pretrained_3')
def l2_avg():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels('cudnn_lstm_2', 'rnn_pretrained_4')
def l2_avg2():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels('cudnn_lstm_2', 'rnn_pretrained_4')
def l2_ker1():
    return KerasRNN(
        num_epochs=5, batch_size=2000, external_metrics=dict(roc_auc=roc_auc_score),
        ignore_columns=['comment_text'],
        compile_opts=dict(loss='binary_crossentropy', optimizer='sgd'),
        model_fn=keras_models.stack1,
        model_opts=dict(
            l2=1e-6
        )
    )


@submodels('cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4')
def l2_wavg1():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.4, 0.2, 0.4]),
    )


@submodels('lr2', 'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4')
def l2_wavg2():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.15, 0.35, 0.1, 0.4]),
    )


@submodels('lr2', 'lr3', 'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4')
def l2_wavg3():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.05, 0.1, 0.35, 0.1, 0.4]),
    )


@submodels('lr2', 'lr3', 'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1')
def l2_wavg4():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.05, 0.1, 0.3, 0.1, 0.4, 0.4], renorm=True),
    )


@submodels('lr2', 'lr3', 'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1')
def l2_avg3():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels('lr2', 'lr3', 'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2')
def l2_avg4():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels('lr2', 'lr3', 'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num')
def l2_avg5():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k'
)
def l2_avg6():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k'
)
def l2_avg7():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3'
)
def l2_avg8():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5'
)
def l2_avg9():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5'
)
def l2_lr2():
    return make_pipeline(
        DropColumns(['comment_text']),
        FunctionTransformer(expit),
        MultiProba(LogisticRegression(C=1e-2))
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5'
)
def l2_ker2():
    return KerasRNN(
        num_epochs=15, batch_size=2000, external_metrics=dict(roc_auc=roc_auc_score),
        ignore_columns=['comment_text'],
        compile_opts=dict(loss='binary_crossentropy', optimizer='sgd'),
        model_fn=keras_models.stack1,
        model_opts=dict(
            l2=1e-6, shared=False
        )
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5'
)
def l2_ker3():
    return KerasRNN(
        num_epochs=150, batch_size=2000, external_metrics=dict(roc_auc=roc_auc_score),
        ignore_columns=['comment_text'],
        compile_opts=dict(loss='binary_crossentropy', optimizer='sgd'),
        model_fn=keras_models.stack2,
        model_opts=dict(
            l2=1e-6, shared=False
        )
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
)
def l2_avg10():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
    'bigru_cnn_4_aug2',
)
def l2_avg11():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
    'bigru_cnn_4_aug2',
)
def l2_lgb1():
    return make_pipeline(
        DropColumns(['comment_text']),
        MultiProba(lgb.LGBMClassifier(
            max_depth=3, metric="auc",
            n_estimators=125, num_leaves=10, boosting_type="gbdt",
            learning_rate=0.1, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.8, bagging_freq=5,
            reg_lambda=0.2
        )))


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
    'bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_rcnn_1', 'bigru_rcnn_3',
)
def l2_avg12():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
    'bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_rcnn_1', 'bigru_rcnn_3',
    'bigru_cnn_4_aug4',
)
def l2_avg13():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
    'bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_rcnn_1', 'bigru_rcnn_3',
    'bigru_cnn_4_aug4', 'bigru_cnn_5_aug4', 'bigru_sterby_3_num_aug4',
)
def l2_avg14():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
    'bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_rcnn_1', 'bigru_rcnn_3',
    'bigru_cnn_4_aug4', 'bigru_cnn_5_aug4', 'bigru_sterby_3_num_aug4',
    'bigru_cnn_4_aug6', 'bigru_cnn_6_aug6',
)
def l2_avg15():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'bigru_sterby_4_bpe50k', 'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',

)
def l2_avg16():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'bigru_sterby_4_bpe50k', 'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
)
def l2_lgb_group_tst():
    return make_pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2']),
            ('bpe', ['bigru_sterby_4_bpe50k']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_5', 'bigru_sterby_2_num_sent_longer_rand']),
        ]),
        MultiProba(lgb.LGBMClassifier(
            max_depth=3, metric="auc",
            n_estimators=250, num_leaves=10, boosting_type="gbdt",
            learning_rate=0.05, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.8, bagging_freq=5,
            reg_lambda=0.2
        )))


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'bigru_sterby_4_bpe50k', 'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
)
def l2_group_avg_tst():
    return make_pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2']),
            ('bpe', ['bigru_sterby_4_bpe50k']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_5', 'bigru_sterby_2_num_sent_longer_rand']),
        ]),
        SimpleAverage())


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4', 'bigru_gmp_1', 'bigru_sterby_2',
    'bigru_sterby_2_num', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_4_bpe50k',
    'bigru_cnn_3', 'bigru_cnn_4', 'bigru_sterby_5',
    'bigru_rcnn_4', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2',
    'bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_rcnn_1', 'bigru_rcnn_3',
    'bigru_cnn_4_aug4', 'bigru_cnn_5_aug4', 'bigru_sterby_3_num_aug4',
    'bigru_cnn_4_aug6', 'bigru_cnn_6_aug6',
)
def l2_ker_tst():
    return KerasRNN(
        num_epochs=150, batch_size=2000, external_metrics=dict(roc_auc=roc_auc_score),
        ignore_columns=['comment_text'],
        compile_opts=dict(loss='binary_crossentropy', optimizer='adam'),
        model_fn=keras_models.stack2,
        model_opts=dict(
            l2=1e-6, shared=False
        )
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2',
    'bigru_sterby_4_bpe50k', 'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6',
)
def l2_avg17():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6',
)
def l2_avg18():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6',
)
def l2_avg19():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
)
def l2_avg20():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
)
def l2_group_lgb20_b10():
    return Pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
            ('lgb', ['lgb1', 'lgb2', 'lgb3']),
            ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_5', 'bigru_sterby_2_num_sent_longer_rand']),
            ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6']),
        ]),
        Bagged(10,  boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50)))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
)
def l2_group_rf20():
    return make_pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
            ('lgb', ['lgb1', 'lgb2', 'lgb3']),
            ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_5', 'bigru_sterby_2_num_sent_longer_rand']),
            ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6']),
        ]),
        MultiProba(RandomForestClassifier(500, max_depth=5, n_jobs=-1)))


@submodels('l2_avg20', 'l2_group_lgb20_b10')
def l3_avg1():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6', 'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter',
)
def l2_avg21():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels('l2_avg21', 'l2_group_lgb20_b10')
def l3_avg2():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6', 'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter',
)
def l2_group_ker21():
    return Pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
            ('lgb', ['lgb1', 'lgb2', 'lgb3']),
            ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_5', 'bigru_sterby_2_num_sent_longer_rand']),
            ('g5', ['bigru_cnn_9_aug6_twitter']),
            ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6']),
        ]),
        KerasRNN(
            num_epochs=150, batch_size=2000, external_metrics=dict(roc_auc=roc_auc_score),
            ignore_columns=['comment_text'],
            compile_opts=dict(loss='binary_crossentropy', optimizer=SGD(1e-1)),
            model_fn=keras_models.stack2,
            model_opts=dict(
                l2=1e-3, shared=False, hid_size=16,
            )
        ))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6', 'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_sterby_2_aug6'
)
def l2_avg22():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
)
def l2_group_rot20():
    return make_pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
            ('lgb', ['lgb1', 'lgb2', 'lgb3']),
            ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_5', 'bigru_sterby_2_num_sent_longer_rand']),
            ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6']),
        ]),
        RotationForest(5, MultiProba(RandomForestClassifier(10, max_depth=5, n_jobs=-1))))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6', 'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6',
)
def l2_avg23():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels('l2_avg23', 'l2_group_lgb20_b10')
def l3_avg3():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
)
def l2_group_lgb23_b10():
    return Pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
            ('lgb', ['lgb1', 'lgb2', 'lgb3']),
            ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
            ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6']),
        ]),
        Bagged(20,  boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50)))


@submodels('l2_avg23', 'l2_group_lgb23_b10')
def l3_avg4():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre',
)
def l2_group_rot24():
    return make_pipeline(
        AvgGroupsColumns(columns=meta.target_columns, groups=[
            ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
            ('lgb', ['lgb1', 'lgb2', 'lgb3']),
            ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
            ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
            ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
            ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
            ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
            ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
            ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6']),
        ]),
        RotationForest(20, MultiProba(DecisionTreeClassifier(max_depth=5))))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6', 'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre',
)
def l2_avg24():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels('l2_avg24', 'l2_group_lgb23_b10')
def l3_avg5():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre',
)
def l2_group_lgb24_tst0():
    return Pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre']),
            ]),
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre',
)
@features('num1', 'num2', 'ind1', 'sentiment1')
def l2_group_lgb24_tst1():
    return Pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre']),
            ]),
            SelectColumns(['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'])
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre',
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api1')
def l2_group_lgb24_tst2():
    return Pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre']),
            ]),
            SelectColumns([
                'cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos',
                'UNSUBSTANTIAL', 'OBSCENE', 'LIKELY_TO_REJECT', 'SEVERE_TOXICITY', 'TOXICITY', 'INFLAMMATORY', 'ATTACK_ON_AUTHOR', 'SPAM', 'INCOHERENT', 'ATTACK_ON_COMMENTER',
            ])
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre',
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api2_raw')
def l2_group_lgb24_tst3():
    return Pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre']),
            ]),
            SelectColumns([
                'cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos',
                'UNSUBSTANTIAL', 'OBSCENE', 'LIKELY_TO_REJECT', 'SEVERE_TOXICITY', 'TOXICITY', 'INFLAMMATORY', 'ATTACK_ON_AUTHOR', 'SPAM', 'INCOHERENT', 'ATTACK_ON_COMMENTER',
            ])
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels('l2_avg24', 'l2_group_lgb24_tst2')
def l3_avg6_api():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre',
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api1')
def l2_group_lgb24_api_b20():
    return Pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre']),
            ]),
            SelectColumns([
                'cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos',
                'UNSUBSTANTIAL', 'OBSCENE', 'LIKELY_TO_REJECT', 'SEVERE_TOXICITY', 'TOXICITY', 'INFLAMMATORY', 'ATTACK_ON_AUTHOR', 'SPAM', 'INCOHERENT', 'ATTACK_ON_COMMENTER',
            ])
        ),
        Bagged(20, boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50)))


@submodels('l2_avg24', 'l2_group_lgb24_api_b20')
def l3_avg7_api():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([
            [0.01, 0.1, 0.1, 0.1, 0.1, 0.1],
            [0.99, 0.9, 0.9, 0.9, 0.9, 0.9]
        ]),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6', 'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
def l2_avg25():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1')
def l2_group_lgb25_feats():
    return Pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'])
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1')
def l2_group_lgb25_feats_b5():
    return Pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'])
        ),
        Bagged(5, boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50)))


@submodels('l2_avg23', 'l2_avg24', 'l2_group_lgb23_b10', 'l2_group_lgb25_feats', 'l2_group_lgb25_feats_b5')
def l3_avg8():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.2, 0.2, 0.2, 0.2, 0.2]),
    )


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api3')
def l2_group_lgb25_api3():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c] for c in api_columns], [])
            )
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api3')
def l2_group_lgb25_api3_2():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c] for c in api_columns], [])
            )
        ),
        boost_models.LgbModel(params=dict(
            max_depth=4, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.015, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api3')
def l2_group_rgf25_api3():
    from rgf.sklearn import RGFClassifier

    return make_pipeline(
        make_union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c] for c in api_columns], [])
            )
        ),
        FunctionTransformer(np.nan_to_num, validate=False),
        MultiProba(RGFClassifier(max_leaf=400, algorithm="RGF_Sib", test_interval=100, verbose=True)))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api3_2')
def l2_group_lgb25_api3_3():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c, '%s_mean' % c, '%s_std' % c] for c in api_columns], [])
            )
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api3_2')
def l2_group_xgb25_api3_3():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c, '%s_mean' % c, '%s_std' % c] for c in api_columns], [])
            )
        ),
        boost_models.XgbModel(params=dict(
            min_child_weight=8,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api3_2')
def l2_group_et25_api3_3():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c, '%s_mean' % c, '%s_std' % c] for c in api_columns], [])
            )
        ),
        FunctionTransformer(lambda x: x.fillna(-1), validate=False),
        MultiProba(ExtraTreesClassifier(500, max_depth=8, n_jobs=-1)))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api3_2')
def l2_group_lr25_api3_3():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c, '%s_mean' % c] for c in api_columns], [])
            )
        ),
        Imputer(),
        MultiProba(LogisticRegression(class_weight='balanced', penalty='l1'), n_jobs=-1))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api2')
def l2_group_lgb25_api2():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c, '%s_mean' % c, '%s_std' % c] for c in api_columns], [])
            )
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.9, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=800,
            insult=1000,
            identity_hate=1000
        ), verbose_eval=50))


@submodels(
    'lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams',
    'lgb1', 'lgb2', 'lgb3',
    'bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6',
    'rnn_pretrained_3', 'bigru_cnn_6_aug6', 'bigru_cnn_4_aug6', 'bigru_sterby_2', 'bigru_cnn_5_aug4', 'bigru_rcnn_1', 'cudnn_lstm_2', 'bigru_cnn_4_aug3', 'bigru_rcnn_3', 'bigru_gmp_1', 'bigru_rcnn_4', 'bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug4', 'bigru_sterby_3_num_aug2', 'rnn_pretrained_4', 'bigru_cnn_4_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_4_aug2', 'bigru_cnn_3', 'bigru_sterby_2_num', 'bigru_sterby_5',
    'bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_aug6', 'bigru_cnn_7_atanas_aug6',
    'bigru_cnn_8_bpe50k_aug6', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_bpe50k_aug6', 'bigru_sterby_2_aug6',
    'bigru_dpcnn_aug7_pre', 'dpcnn_bpe50k_aug7_pre', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre'
)
@features('num1', 'num2', 'ind1', 'sentiment1', 'api2')
def l2_group_lgb25_api2_2():
    return Pipeline(
        Union(
            AvgGroupsColumns(columns=meta.target_columns, groups=[
                ('lr', ['lr2', 'lr3', 'lr3_cl2', 'lr3_more_ngrams']),
                ('lgb', ['lgb1', 'lgb2', 'lgb3']),
                ('bpe', ['bigru_sterby_4_bpe50k', 'bigru_cnn_6_bpe50k_aug6', 'bigru_cnn_7_bpe50k_aug6', 'bigru_cnn_8_bpe50k_aug6', 'dpcnn_bpe50k_aug7_pre']),
                ('g0', ['cudnn_lstm_2', 'rnn_pretrained_3', 'rnn_pretrained_4']),
                ('g1', ['bigru_gmp_1', 'bigru_sterby_2', 'bigru_sterby_2_num', 'bigru_sterby_2_num_aug', 'bigru_sterby_3_num_aug2', 'bigru_sterby_3_num_aug4']),
                ('g2', ['bigru_rcnn_1', 'bigru_rcnn_3', 'bigru_rcnn_4', 'bigru_cnn_3', 'bigru_sterby_5', 'bigru_cnn_9_aug6_twitter', 'bigru_cnn_9_aug6_twitter2', 'bigru_dpcnn_aug6', 'bigru_dpcnn_aug7_pre']),
                ('g3', ['bigru_cnn_4_aug2', 'bigru_cnn_4_aug3', 'bigru_cnn_4_aug4', 'bigru_cnn_4_aug6', 'bigru_cnn_5_aug4', 'bigru_cnn_5_aug6', 'bigru_cnn_6_aug6', 'bigru_cnn_7_aug6']),
                ('g4', ['bigru_cnn_4', 'bigru_sterby_2_num_sent_longer_rand', 'bigru_sterby_2_aug6']),
                ('atanas', ['bigru_cnn_6_atanas_aug6', 'bigru_cnn_7_atanas_aug6', 'dpcnn_twitter_aug7_pre', 'dpcnn_fasttext_aug7_pre']),
            ]),
            SelectColumns(
                ['cap_ratio', 'exq_ratio', 'mean_sent_len', 'mean_sent_len_words', 'mean_word_len', 'num_sents', 'num_words', 'uniq_word_ratio', 'ant_slash_n', 'raw_word_len', 'raw_char_len', 'nb_upper', 'nb_fk', 'nb_sk', 'nb_dk', 'nb_you', 'nb_mother', 'nb_ng', 'start_with_columns', 'has_timestamp', 'has_date_long', 'has_date_short', 'has_http', 'has_mail', 'has_emphasize_equal', 'has_emphasize_quotes', 'compound', 'neg', 'neu', 'pos'] +
                sum([['%s_summary' % c, '%s_min' % c, '%s_max' % c, '%s_mean' % c, '%s_std' % c] for c in api_columns], [])
            )
        ),
        boost_models.LgbModel(params=dict(
            max_depth=3, metric="auc",
            num_leaves=7, boosting_type="gbdt",
            learning_rate=0.02, feature_fraction=0.45, colsample_bytree=0.45,
            bagging_fraction=0.92, bagging_freq=5,
            reg_lambda=0.3,
        ), rounds=dict(
            toxic=1000,
            severe_toxic=800,
            obscene=800,
            threat=500,
            insult=1000,
            identity_hate=500
        ), verbose_eval=50))


@submodels('l2_group_lgb24_tst2', 'l2_group_lgb25_api3_2', 'l2_group_lgb25_api3', 'l2_group_lgb25_api3_3', 'l2_group_et25_api3_3', 'l2_group_lgb25_api2')
def l3_avg9_api():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.15, 0.1, 0.3, 0.4, 0.05, 1.0], renorm=True),
    )


@submodels('l2_group_lgb24_tst2', 'l2_group_lgb25_api3_2', 'l2_group_lgb25_api3', 'l2_group_lgb25_api3_3', 'l2_group_et25_api3_3', 'l2_group_lgb25_api2', 'l2_group_lgb25_api2_2')
def l3_avg10_api():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.15, 0.1, 0.3, 0.4, 0.05, 0.5, 0.4], renorm=True),
    )


@submodels('l2_group_lgb24_tst2', 'l2_group_lgb25_api3_2', 'l2_group_lgb25_api3', 'l2_group_lgb25_api3_3', 'l2_group_et25_api3_3')
def l3_avg11_api():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.15, 0.1, 0.3, 0.4, 0.05], renorm=True),
    )


@submodels('l2_group_lgb24_tst2', 'l2_group_lgb25_api2', 'l2_group_lgb25_api2_2')
def l3_avg12_api():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.2, 0.5, 0.4], renorm=True),
    )


@submodels('l2_group_lgb24_tst2', 'l2_group_lgb25_api3_2', 'l2_group_lgb25_api3', 'l2_group_lgb25_api3_3', 'l2_group_et25_api3_3', 'l2_group_lgb25_api2', 'l2_group_lgb25_api2_2')
def l3_avg13_api():
    return make_pipeline(
        DropColumns(['comment_text']),
        WeightedAverage([0.2, 0.1, 0.3, 0.4, 0.05, 0.3, 0.2], renorm=True),
    )


@submodels('l3_avg8', 'l3_avg9_api')
def l4_avg1():
    return make_pipeline(
        DropColumns(['comment_text']),
        SimpleAverage(),
    )
