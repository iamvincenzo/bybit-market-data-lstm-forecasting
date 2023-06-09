""" This file includes Python code licensed under the Apache License 2.0, 
    Copyright (c) 2021 Hong Jing. 
    https://github.com/jinglescode/time-series-forecasting-pytorch. """

import numpy as np

class Normalizer():
    """ Initialize configurations. """
    def __init__(self):
        self.mu = None
        self.sd = None

    def fit_transform(self, x):
        self.mu = np.mean(x, axis=(0), keepdims=True)
        self.sd = np.std(x, axis=(0), keepdims=True)
        normalized_x = (x - self.mu)/self.sd
        return normalized_x
    
    def transform(self, x):
        normalized_x = (x - self.mu)/self.sd
        return normalized_x

    def inverse_transform(self, x):
        return (x*self.sd) + self.mu