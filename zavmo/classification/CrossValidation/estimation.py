"""Post-Vectorization Estimation Module"""

import sklearn
import warnings
import numpy as np
import sklearn.svm
import sklearn.tree
import sklearn.ensemble
import sklearn.isotonic
import sklearn.neighbors
import sklearn.naive_bayes
import sklearn.linear_model
import sklearn.neural_network
import sklearn.semi_supervised
import xgboost
from sklearn.base import BaseEstimator, TransformerMixin
from .evaluation import get_scorer

module_options = {
    "naive_bayes": sklearn.naive_bayes.__all__,
    "linear_model": sklearn.linear_model.__all__,
    "semi_supervised": sklearn.semi_supervised.__all__,
    "svm": sklearn.svm.__all__,
    "isotonic": sklearn.isotonic.__all__,
    "tree": sklearn.tree.__all__,
    "ensemble": sklearn.ensemble.__all__,
    "neighbors": sklearn.neighbors.__all__,
    "neural_network": sklearn.neural_network.__all__,
    "xgboost": xgboost
    
}

module_dict_list = [
    {f: module for f in funcmethods} for module, funcmethods in module_options.items() if not module == "xgboost"
]

xgboost_module = module_options.get("xgboost")
if xgboost_module:
    module_dict_list.extend([{f: xgboost_module for f in dir(xgboost_module) if callable(getattr(xgboost_module, f, None))}])

estimator_options = {k: v for element in module_dict_list for k, v in element.items()}


def get_probas_from_decisions(X):
    """
    Reverse decision function values to get \
        pseudo-probabilities between 0 & 1

    Args:
        X: decision function output

    Returns: pseudo-probabilities between 0 & 1
        dtype: float
    """
    return 1 / (1 + np.exp(-X))


def load_estimator(model, estimator_options=estimator_options):
    """
    Load an estimator from sklearn.
    """
    if model in estimator_options:
        if model == "XGBClassifier":
            return getattr(xgboost, model)
        else:
            return getattr(getattr(sklearn, estimator_options.get(model)), model)
    else:
        raise ValueError("{} is not a valid estimator model name".format(model))

class Classifier(BaseEstimator, TransformerMixin):
    """
    Main classifier methods
    """

    def __init__(self, model, is_final=False, **kwargs) -> callable:
        """ """
        self.model = model
        self.is_final = is_final
        self.classifier = load_estimator(model=self.model)(**kwargs)

    def get_params(self, **kwargs) -> dict:
        params = self.classifier.get_params(**kwargs)
        params["model"] = self.model
        params["is_final"] = self.is_final
        return params

    def set_params(self, **kwargs):
        self.model    = kwargs.get("model", "LogisticRegression")
        self.is_final = kwargs.get("is_final", False)
        self.classifier = load_estimator(model=str(self.model))()
        self.classifier.set_params(
            **{k: v for k, v in kwargs.items() if k not in ["model", "is_final"]}
        )

    def fit(self, *args, **kwargs):
        """
        Fit the estimator.
        """
        self.classifier.fit(*args, **kwargs)
        return self

    def get_normalized_decisions(self, X, **kwargs):
        """
        Artificial probabilities - normalized decisions.
            There's no need to fit the estimator for training,
                since we will only use it on the decision-values to classify.
        """
        if hasattr(self.classifier, "decision_function"):
            decisions = self.classifier.decision_function(X, **kwargs)
        elif hasattr(self.classifier, "_decision_function"):
            decisions = self.classifier._decision_function(X, **kwargs)
        else:
            print("No decision function found.")
        positive_proba = get_probas_from_decisions(decisions)
        negative_proba = 1 - positive_proba
        return np.vstack((negative_proba, positive_proba)).T

    def get_coefficient(self, X, **kwargs):
        """
        """
        if hasattr(self.classifier, "coef_"):
            return self.classifier.coef_
        else:
            warnings.warn("No coefficient found.")
            return None

    def transform(self, X, **kwargs):
        """ 
        """
        if self.is_final is True:
            return self.predict(X, **kwargs)
        else:
            return self.predict_proba(X, **kwargs)

    def predict_proba(self, X, **kwargs):
        """
        Predict the probability of each class for each sample.
        """
        # If `predict_proba` is available, use it
        if hasattr(self.classifier, "predict_proba"):
            return self.classifier.predict_proba(X, **kwargs)
        else:
            # Otherwise, use `decision_function`
            if hasattr(self.classifier, "decision_function") or hasattr(
                self.classifier, "_decision_function"
            ):
                return self.get_normalized_decisions(X, **kwargs)
            else:
                warnings.warn("No probability function found. Returning decisions.")
                return self.predict(X, **kwargs)

    def predict(self, X, **kwargs):
        """
        Predict the class for each sample.
            The last layer of the pipeline will use this function.
            As long as the thresholdlayer is called, this function will not be used.
        """
        predictions = self.classifier.predict(X, **kwargs)
        return np.nan_to_num(predictions, nan=0)
