import os
import json
import pickle
import sys
import traceback
import pandas as pd
from sklearn import tree


def train_model(train_data_path, hyperparameters = {}):
    # Reads training data up to a DataFrame
    input_files = [ os.path.join(train_data_path, file) for file in os.listdir(train_data_path) ]
    if len(input_files) == 0:
        raise ValueError('There is no training data')
    raw_data = [ pd.read_csv(file, header=None) for file in input_files ]
    train_data = pd.concat(raw_data)

    # labels are in the first column
    train_y = train_data.iloc[:,0]
    train_X = train_data.iloc[:,1:]

    # Here we only support a single hyperparameter. Note that hyperparameters are always passed in as
    # strings, so we need to do any necessary conversions.
    max_leaf_nodes = hyperparameters.get('max_leaf_nodes', None)
    if max_leaf_nodes is not None:
        max_leaf_nodes = int(max_leaf_nodes)

    # Now use scikit-learn's decision tree classifier to train the model.
    clf = tree.DecisionTreeClassifier(max_leaf_nodes=max_leaf_nodes)
    clf = clf.fit(train_X, train_y)
    return clf


def save_model(model_path, model):
    with open(os.path.join(model_path, 'decision-tree-model.pkl'), 'wb') as out:
        pickle.dump(model, out)


def load_model(model_path):
    with open(os.path.join(model_path, 'decision-tree-model.pkl'), 'rb') as inp:
        model = pickle.load(inp)    
        return model


def predict(csv_data, model):
    data = pd.read_csv(csv_data, header=None)
    
    # Drop first column, since sample notebook uses training data to show case predictions
    data.drop(data.columns[[0]], axis=1, inplace=True)

    predictions = model.predict(data)
    return predictions
