
import operator
import functools
import pandas as pd
import numpy as np
import sklearn.model_selection


def convert_dict(d, prefix):
    """
    Convert a nested dictionary to a flat dictionary
    """

    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            prefix_fmt = f"{prefix}__{k}".strip("__")
            result.update(convert_dict(v, prefix_fmt))
        elif isinstance(v, list):
            prefix_fmt = f"{prefix}__{k}".strip("__")
            result[prefix_fmt] = v
    return result


def convert_nested_params(configuration):
    """
    Convert a nested CV configuration to a flat dictionary
    """

    return convert_dict(configuration, "")


def count_hyperparameters(param_grid):
    """
    Count hyperparameter grid of type list-or-dict
    """

    def count_dict_params(param_dict):
        """
        Count hyperparameter grid of type dict
        """
        num_configurations = functools.reduce(
            operator.mul, [len(p) for p in param_dict.values()], 1
        )
        return num_configurations

    if isinstance(param_grid, dict):
        num_params = count_dict_params(param_grid)
    elif isinstance(param_grid, list):
        num_params = sum([count_dict_params(pdict) for pdict in param_grid])
    else:
        num_params = None
    return num_params


class CrossValidator:
    """
    Cross-validation methods
    """

    def __init__(
        self,
        model_pipe,
        search_parameters,
        cv_method="GridSearchCV",
        scoring="f1",
        cv=3,
        refit=False,
        **kwargs,
    ):
        """
        Needs a valid `cv_method` from `sklearn.model_selection`
        Configure the cross-validation object
        """

        self.cross_validation = getattr(sklearn.model_selection, cv_method)
        self.cross_validation = self.cross_validation(
            model_pipe,
            search_parameters,
            scoring=scoring,
            cv=cv,
            refit=refit,
            **kwargs,
        )

    def fit(self, X, Y, **kwargs):
        """
        Fit the cross-validation object
        """
        self.cross_validation.fit(X, Y, **kwargs)

        self.refit_string = self.cross_validation.refit  

        self.n_splits = self.cross_validation.n_splits_
        print(self.refit_string)
        if not self.refit_string:
            self.refit_string = "score"
        self.rank_column = "rank_test_" + self.refit_string  

        self.best_parameters = self.get_best_params()
        self.param_df = self.get_cv_results()

        self.cv_scores = self.param_df.loc[
            self.param_df[self.rank_column] == 1,
            [f"split{i}_test_{self.refit_string}" for i in range(self.n_splits)],
        ].to_dict("records")[0]
        
        avg_cv_score = np.mean(list(self.cv_scores.values()))
        self.cv_scores.update({"avg_test_score": avg_cv_score})

    def get_cv_scores(self):
        """
        Get the cross-validation scores
        """
        return self.cv_scores.copy()

    def get_cv_results(self):
        """
        Get the cross-validation results as a dataframe
        """
        self.param_df = pd.DataFrame(self.cross_validation.cv_results_)
        self.param_df = self.param_df.sort_values(
            by=self.rank_column, ignore_index=True
        )
        return self.param_df.copy()

    def predict(self, X):
        """
        Predict using the best estimator
        """
        return self.cross_validation.predict(X)

    def get_best_params(self):
        """
        Get the best parameters
        """
        return self.cross_validation.best_params_