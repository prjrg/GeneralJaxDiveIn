import pickle

import pandas as pd
import tensorflow as tf
import numpy as np

import einops

import matplotlib.pyplot as plt

def load_dataset(filename='../data/digits/train.csv', filename1='../data/digits/test.csv'):
    train_data = pd.read_csv(filename)
    test = pd.read_csv(filename1).values[:, :]

    train_y = train_data.values[:, 0]
    train_x = train_data.values[:, 1:]

    train_x = (train_x - 128.0) / 255.0
    test = (test - 128.0) / 255.0

    train_x = train_x.reshape((-1, 28, 28, 1))
    test_x = test.reshape((-1, 28, 28, 1))

    return train_x, train_y, test_x


upscale = 96

train_x, train_y, test_x = load_dataset()

train_res = np.zeros((train_x.shape[0], upscale, upscale, 1))

for i in range(train_res.shape[0]):
    train_res[i, :, :, :] = np.array(tf.image.resize(tf.convert_to_tensor([train_x[i]]), size=(upscale, upscale)))

test_res = np.zeros((test_x.shape[0], upscale, upscale, 1))

for j in range(test_res.shape[0]):
    test_res[j, :, :, :] = np.array(tf.image.resize(tf.convert_to_tensor([test_x[j]]), size=(upscale, upscale)))


img10 = ((train_res[9, :, :, :] * 255.0) + 128.0).astype(np.uint8)

plt.imshow(img10)
plt.show()



