#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import numpy as np
from numpy import array

from pyspark.mllib.common import callMLlibFunc, inherit_doc
from pyspark.mllib.linalg import SparseVector, _convert_to_vector

__all__ = ['LabeledPoint', 'LinearModel', 'LinearRegressionModel', 'RidgeRegressionModel',
           'LinearRegressionWithSGD', 'LassoWithSGD', 'RidgeRegressionWithSGD']


class LabeledPoint(object):

    """
    The features and labels of a data point.

    :param label: Label for this data point.
    :param features: Vector of features for this point (NumPy array, list,
        pyspark.mllib.linalg.SparseVector, or scipy.sparse column matrix)
    """

    def __init__(self, label, features):
        self.label = float(label)
        self.features = _convert_to_vector(features)

    def __reduce__(self):
        return (LabeledPoint, (self.label, self.features))

    def __str__(self):
        return "(" + ",".join((str(self.label), str(self.features))) + ")"

    def __repr__(self):
        return "LabeledPoint(%s, %s)" % (self.label, self.features)


class LinearModel(object):

    """A linear model that has a vector of coefficients and an intercept."""

    def __init__(self, weights, intercept):
        self._coeff = _convert_to_vector(weights)
        self._intercept = float(intercept)

    @property
    def weights(self):
        return self._coeff

    @property
    def intercept(self):
        return self._intercept

    def __repr__(self):
        return "(weights=%s, intercept=%r)" % (self._coeff, self._intercept)


@inherit_doc
class LinearRegressionModelBase(LinearModel):

    """A linear regression model.

    >>> lrmb = LinearRegressionModelBase(np.array([1.0, 2.0]), 0.1)
    >>> abs(lrmb.predict(np.array([-1.03, 7.777])) - 14.624) < 1e-6
    True
    >>> abs(lrmb.predict(SparseVector(2, {0: -1.03, 1: 7.777})) - 14.624) < 1e-6
    True
    """

    def predict(self, x):
        """
        Predict the value of the dependent variable given a vector x
        containing values for the independent variables.
        """
        x = _convert_to_vector(x)
        return self.weights.dot(x) + self.intercept


@inherit_doc
class LinearRegressionModel(LinearRegressionModelBase):

    """A linear regression model derived from a least-squares fit.

    >>> from pyspark.mllib.regression import LabeledPoint
    >>> data = [
    ...     LabeledPoint(0.0, [0.0]),
    ...     LabeledPoint(1.0, [1.0]),
    ...     LabeledPoint(3.0, [2.0]),
    ...     LabeledPoint(2.0, [3.0])
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), initialWeights=np.array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> data = [
    ...     LabeledPoint(0.0, SparseVector(1, {0: 0.0})),
    ...     LabeledPoint(1.0, SparseVector(1, {0: 1.0})),
    ...     LabeledPoint(3.0, SparseVector(1, {0: 2.0})),
    ...     LabeledPoint(2.0, SparseVector(1, {0: 3.0}))
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), initialWeights=array([1.0]))
    >>> abs(lrm.predict(array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    """


# train_func should take two parameters, namely data and initial_weights, and
# return the result of a call to the appropriate JVM stub.
# _regression_train_wrapper is responsible for setup and error checking.
def _regression_train_wrapper(train_func, modelClass, data, initial_weights):
    first = data.first()
    if not isinstance(first, LabeledPoint):
        raise ValueError("data should be an RDD of LabeledPoint, but got %s" % first)
    initial_weights = initial_weights or [0.0] * len(data.first().features)
    weights, intercept = train_func(data, _convert_to_vector(initial_weights))
    return modelClass(weights, intercept)


class LinearRegressionWithSGD(object):

    @classmethod
    def train(cls, data, iterations=100, step=1.0, miniBatchFraction=1.0,
              initialWeights=None, regParam=0.0, regType=None, intercept=False):
        """
        Train a linear regression model on the given data.

        :param data:              The training data.
        :param iterations:        The number of iterations (default: 100).
        :param step:              The step parameter used in SGD
                                  (default: 1.0).
        :param miniBatchFraction: Fraction of data to be used for each SGD
                                  iteration.
        :param initialWeights:    The initial weights (default: None).
        :param regParam:          The regularizer parameter (default: 0.0).
        :param regType:           The type of regularizer used for training
                                  our model.

                                  :Allowed values:
                                     - "l1" for using L1 regularization (lasso),
                                     - "l2" for using L2 regularization (ridge),
                                     - None for no regularization

                                     (default: None)

        @param intercept:         Boolean parameter which indicates the use
                                  or not of the augmented representation for
                                  training data (i.e. whether bias features
                                  are activated or not). (default: False)
        """
        def train(rdd, i):
            return callMLlibFunc("trainLinearRegressionModelWithSGD", rdd, int(iterations),
                                 float(step), float(miniBatchFraction), i, float(regParam),
                                 regType, bool(intercept))

        return _regression_train_wrapper(train, LinearRegressionModel, data, initialWeights)


@inherit_doc
class LassoModel(LinearRegressionModelBase):

    """A linear regression model derived from a least-squares fit with an
    l_1 penalty term.

    >>> from pyspark.mllib.regression import LabeledPoint
    >>> data = [
    ...     LabeledPoint(0.0, [0.0]),
    ...     LabeledPoint(1.0, [1.0]),
    ...     LabeledPoint(3.0, [2.0]),
    ...     LabeledPoint(2.0, [3.0])
    ... ]
    >>> lrm = LassoWithSGD.train(sc.parallelize(data), initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> data = [
    ...     LabeledPoint(0.0, SparseVector(1, {0: 0.0})),
    ...     LabeledPoint(1.0, SparseVector(1, {0: 1.0})),
    ...     LabeledPoint(3.0, SparseVector(1, {0: 2.0})),
    ...     LabeledPoint(2.0, SparseVector(1, {0: 3.0}))
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    """


class LassoWithSGD(object):

    @classmethod
    def train(cls, data, iterations=100, step=1.0, regParam=0.01,
              miniBatchFraction=1.0, initialWeights=None):
        """Train a Lasso regression model on the given data."""
        def train(rdd, i):
            return callMLlibFunc("trainLassoModelWithSGD", rdd, int(iterations), float(step),
                                 float(regParam), float(miniBatchFraction), i)

        return _regression_train_wrapper(train, LassoModel, data, initialWeights)


@inherit_doc
class RidgeRegressionModel(LinearRegressionModelBase):

    """A linear regression model derived from a least-squares fit with an
    l_2 penalty term.

    >>> from pyspark.mllib.regression import LabeledPoint
    >>> data = [
    ...     LabeledPoint(0.0, [0.0]),
    ...     LabeledPoint(1.0, [1.0]),
    ...     LabeledPoint(3.0, [2.0]),
    ...     LabeledPoint(2.0, [3.0])
    ... ]
    >>> lrm = RidgeRegressionWithSGD.train(sc.parallelize(data), initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(np.array([1.0])) - 1) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    >>> data = [
    ...     LabeledPoint(0.0, SparseVector(1, {0: 0.0})),
    ...     LabeledPoint(1.0, SparseVector(1, {0: 1.0})),
    ...     LabeledPoint(3.0, SparseVector(1, {0: 2.0})),
    ...     LabeledPoint(2.0, SparseVector(1, {0: 3.0}))
    ... ]
    >>> lrm = LinearRegressionWithSGD.train(sc.parallelize(data), initialWeights=array([1.0]))
    >>> abs(lrm.predict(np.array([0.0])) - 0) < 0.5
    True
    >>> abs(lrm.predict(SparseVector(1, {0: 1.0})) - 1) < 0.5
    True
    """


class RidgeRegressionWithSGD(object):

    @classmethod
    def train(cls, data, iterations=100, step=1.0, regParam=0.01,
              miniBatchFraction=1.0, initialWeights=None):
        """Train a ridge regression model on the given data."""
        def train(rdd, i):
            return callMLlibFunc("trainRidgeModelWithSGD", rdd, int(iterations), float(step),
                                 float(regParam), float(miniBatchFraction), i)

        return _regression_train_wrapper(train, RidgeRegressionModel, data, initialWeights)


def _test():
    import doctest
    from pyspark import SparkContext
    import pyspark.mllib.regression
    globs = pyspark.mllib.regression.__dict__.copy()
    globs['sc'] = SparkContext('local[4]', 'PythonTest', batchSize=2)
    (failure_count, test_count) = doctest.testmod(globs=globs, optionflags=doctest.ELLIPSIS)
    globs['sc'].stop()
    if failure_count:
        exit(-1)

if __name__ == "__main__":
    _test()
