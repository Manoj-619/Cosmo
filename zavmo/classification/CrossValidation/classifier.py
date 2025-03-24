
from sklearn.pipeline import Pipeline
from tempfile import mkdtemp
from .crossval import CrossValidator, count_hyperparameters
from .estimation import Classifier

class Model:
    """
    Main NLP Class for Model Training and Prediction.
    """
    def __init__(self,enable_caching=False,):
        if enable_caching is True:
            self.cache_dir = mkdtemp(prefix="zavmo_")
        else:
            self.cache_dir = None
        self.estimation_steps = []

    def add_classifier(self, name="LogisticRegression", **kwargs):
        """
        Add a classifier to the pipeline
        Args:
            name (str): Name of the classifier method. Any classifier from sklearn can be used
            **kwargs: Keyword arguments for the classifier
        """
        self.estimation_steps.append(("Classifier", Classifier(name, **kwargs)))

    def compile(self):
        """
        Compile the model
        """
        self.steps = [
           *self.estimation_steps,  
            ]
        #### Create the pipeline
        self.model = Pipeline(self.steps, memory=self.cache_dir)
        if len(self.post_estimation_steps)==0:
            self.model.set_params(Classifier__is_final=True)
        else:
            self.model.set_params(Classifier__is_final=False)

    def set_params(self, **kwargs):
        """
        Set the parameters of the model

        """
        self.model.set_params(**kwargs)

    def get_params(self):
        """
        Get the parameters of the model
        """
        params = self.model.get_params()
        return params.copy()
        
    def cross_validate_fit(
        self,
        X,
        Y,
        cv_method="GridSearchCV",
        search_parameters={},
        scoring="f1",
        cv_splits=5,
        refit=False,
        **kwargs,
    ):
        """
        Cross validate the model and fit it
        Args:
            X (pd.DataFrame): Dataframe of features
            Y (pd.Series): Series of labels
            cv_method (str): Cross validation method
            search_parameters (dict): Search parameters for GridSearchCV
            scoring (str): Scoring method for GridSearchCV
            cv (int): Number of folds for GridSearchCV
            n_iter (int): Number of iterations for RandomizedSearchCV
            refit (bool): Whether to refit the model
            **kwargs: Keyword arguments for the model
        
        Returns:
            cv_scores (dict): Cross validation scores
        """
        print(
            f".......{count_hyperparameters(search_parameters)} hyperparameters configurations possible.....\r",
            end="",
        )

        self.cv = CrossValidator(
            model_pipe=self.model,
            cv_method=cv_method,
            search_parameters=search_parameters,
            scoring=scoring,
            cv=cv_splits,
            refit=refit,
            **kwargs,
        )
        self.cv.fit(X, Y)
        self.set_params(**self.cv.get_best_params())
        self.model.fit(X, Y)
        return self.cv.get_cv_scores()