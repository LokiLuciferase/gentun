#!/usr/bin/env python
"""
Machine Learning models compatible with the Genetic Algorithm implemented using xgboost
"""
import os

import numpy as np
import xgboost as xgb

from .generic_models import GentunModel


class XgboostModel(GentunModel):
    @staticmethod
    def oof_getter_callback(out_dict):
        """Obtain preds and true values for each tree out of fold prediction in the xgb.cv function."""
        def callback(env):
            cv_preds = []
            cv_trues = []
            for i in range(len(env.cvfolds)):
                cv_preds.append(np.array(env.cvfolds[i].bst.predict(env.cvfolds[i].dtest)))
                cv_trues.append(np.array(env.cvfolds[i].dtest.get_label()))
            where_to_add = out_dict.setdefault('cv', [])
            where_to_add.append({'cv_preds': cv_preds,
                                 'cv_trues': cv_trues})
        return callback

    def __init__(self, x_train, y_train, hyperparameters,
                 y_weights=None, booster='gbtree', objective='reg:linear',
                 eval_metric='rmse', kfold=5, num_class=None,
                 num_boost_round=5000, early_stopping_rounds=100,
                 missing=np.nan, nthread=8):
        super(XgboostModel, self).__init__(x_train, y_train)
        self.y_weights = y_weights
        self.nthread = min(os.cpu_count(), nthread)
        self.params = {
            'booster': booster,
            'objective': objective,
            'eval_metric': eval_metric,
            'nthread': self.nthread,
            'silent': 1
        }
        if num_class is not None:
            self.params['num_class'] = num_class
        self.params.update(hyperparameters)
        self.eval_metric = eval_metric
        self.kfold = kfold
        self.num_class = num_class
        self.num_boost_round = num_boost_round
        self.early_stopping_rounds = early_stopping_rounds
        self.missing = missing
        self.best_ntree_limit = None
        self.oof_dict = None

    def cross_validate(self):
        """Train model using k-fold cross validation and
        return mean value of validation metric.
        """
        d_train = xgb.DMatrix(self.x_train, label=self.y_train,
                              weight=self.y_weights,
                              missing=self.missing,
                              nthread=self.nthread)
        # xgb calls its k-fold cross-validation parameter 'nfold'
        oof_history = {}
        cv_result = xgb.cv(
            self.params, d_train, num_boost_round=self.num_boost_round,
            early_stopping_rounds=self.early_stopping_rounds, nfold=self.kfold,
            callbacks=[XgboostModel.oof_getter_callback(oof_history)]
        )
        self.best_ntree_limit = len(cv_result)
        self.oof_dict = oof_history['cv'][self.best_ntree_limit]
        return cv_result['test-{}-mean'.format(self.eval_metric)].values[-1]
