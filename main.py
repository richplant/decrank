from os import listdir

import numpy as np
import pandas as pd
import torch
from scipy import sparse

import dbsetup
import frameset
import preprocess
import skmodels
import collect_env


def import_files():
    """
    Import data from files into mongodb and create merged collections
    """
    importer = dbsetup.Importer('astroturf')

    print("Importing Twitter training set...")
    importer.import_tweets_from_file(col_name='ira_tweets', filename='data/ira_tweets_csv_unhashed.csv')
    importer.import_tweets_from_file(col_name='event_tweets', filename='data/2012_events_twitter.json',
                                     json_type=True, borked_json=False)
    importer.merge_tweets(merge_col='merged_tweets', col_1='ira_tweets', col_2='event_tweets')

    print("Importing Twitter test set...")
    for file in listdir('data/recent_clean_data'):
        importer.import_tweets_from_file(col_name='recent_tweets', filename='data/recent_clean_data/' + file,
                                         json_type=True, borked_json=True)
    for file in listdir('data/recent_ast_data'):
        importer.import_tweets_from_file(col_name='recent_ast_tweets', filename='data/recent_ast_data/' + file)
    importer.merge_tweets(merge_col='recent_merged_tweets', col_1='recent_ast_tweets', col_2='recent_tweets')

    print("Importing Reddit test set...")
    importer.import_reddit_from_file(col_name='ira_reddit', filename='data/comments.csv')
    for file in listdir('data/reddit'):
        importer.import_reddit_from_file(col_name='old_reddit', filename='data/reddit/' + file, json_type=True)
    importer.merge_reddit(merge_col='merged_reddit', col_1='ira_reddit', col_2='old_reddit')


def load(collection):
    """
    Load and format tweet data as Pandas dataframe
    :param collection: Collection name to read from
    :return: Pandas Dataframe
    """
    print("Reading to Dataframe...")
    framer = frameset.Framer('astroturf')
    df = framer.get_frame(collection)
    return df


def process(df, type_str):
    """
    Apply data transformations/dimensionality reduction
    :type df: Pandas dataframe
    :type type_str: training or test data label
    """
    preproc = preprocess.PreProcessor()

    print("Applying transformations...")
    data_arr, labels = preproc.transform(df)
    print("Transformation produced a: {}".format(type(data_arr)))
    print("With shape: {}".format(data_arr.shape))

    print("Saving array of transformed values...")
    sparse.save_npz('{}-data-tf.npz'.format(type_str), data_arr)
    np.savez('{}-label-tf.npz'.format(type_str), labels)

    print("Applying dimensionality reduction...")
    data_lsa = preproc.truncate(data_arr)
    print("Reduction produced a: {}".format(type(data_lsa)))
    print("With shape: {}".format(data_lsa.shape))

    print("Applying class re-sampling...")
    data_rs, label_rs = preproc.balance(data_lsa, labels)
    print("Re-sampling produced a: {}".format(type(data_rs)))
    print("With shape: {}".format(data_rs.shape))
    print("Label shape: {}".format(label_rs.shape))

    print("Saving prepared data...")
    np.savez('{}-data-rs.npz'.format(type_str), data_rs)
    np.savez('{}-label-rs.npz'.format(type_str), label_rs)

    return data_rs, label_rs


def train_sk(data, labels):
    """
    Train model set on data
    :param data: np array of data vectors
    :param labels: np array of label values
    :return: Pandas Dataframe of model scores
    """
    simple_models = skmodels.SkModels()
    scores = simple_models.run_models(data, labels)
    simple_models.save_models('models/sk-models')
    return scores


def main():
    # Pytorch/CUDA bug https://github.com/pytorch/pytorch/issues/27837
    torch.autograd.set_detect_anomaly = True
    collect_env.main()

    # import_files()
    df = load('merged_tweets')
    # df.to_pickle('train-data.zip')

    # df = pd.read_pickle('train-data.zip')
    # df = df.sample(frac=0.001, axis=0)
    # df.to_pickle('sample.zip')

    # df = pd.read_pickle('sample.zip')
    data, labels = process(df, 'train')
    print("Pre-processing complete.")

    print("Running model training...")
    training_scores = train_sk(data, labels)
    print(training_scores)


if __name__ == '__main__':
    main()
