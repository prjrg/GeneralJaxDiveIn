import logging
import pickle
from typing import Optional, Mapping, Any

import haiku as hk
import jax
import jax.numpy as jnp
import jax.random as jr
import jax.nn as jnn
import haiku.initializers as hki
import einops
import functools as ft

import numpy as np
import optax
import pandas as pd

import imageio
import tifffile
import cv2
from PIL import Image

#train = pd.read_csv('/kaggle/input/hubmap-organ-segmentation/train.csv')
train = pd.read_csv('./data/segmentation/train.csv')
#string_to_retrieve_data = lambda x: f"../input/hubmap-organ-segmentation/train_images/{x}.tiff"
def string_to_retrieve_data(x):
    return f"./data/segmentation/train_images/{x}.tiff"

def rle2mask(mask_rle, shape=(3000,3000)):
    s = mask_rle.split()
    starts, lengths = [np.asarray(x, dtype=int) for x in (s[0::2], s[1::2])]
    starts -= 1
    ends = starts + lengths
    img = np.zeros(shape[0]*shape[1], dtype=np.uint8)
    for lo, hi in zip(starts, ends):
        img[lo:hi] = 1
    return img.reshape(shape).T

class TrainLoader:
    def __init__(self):
        self.paths = train["id"].apply(lambda x: string_to_retrieve_data(x)).values.tolist()
        self.img_size = 3000

    def size(self):
        return train.shape[0]

    def get_sample(self, idx):
        path = self.paths[idx]
        image = Image.open(str(path))
        image = image.resize([self.img_size, self.img_size])
        image = np.array(image).astype(float)
        image = (image - image.min()) / (image.max() - image.min())
        

        label = rle2mask(train.rle[idx])

        return image, label


import multiprocessing

batch_size = 8
num_cpus = min([max([1,int(multiprocessing.cpu_count() * 0.8)]), int(batch_size * 0.8)])

tl = TrainLoader()

def compute_el(idx):
    return tl.get_sample(idx)

def get_data(perm):
        pool = multiprocessing.Pool(processes=num_cpus)

        perm = np.array(perm).tolist()
        
        outputs_async = pool.map_async(compute_el, perm)
        pool.close()
        pool.join()
        outputs = outputs_async.get()
        
        x, y = zip(*outputs)

        x = jnp.stack(x, axis=0)

        y = jnp.stack(y, axis=0)

        return x, y


def bgenerator(rng_key, batch_size, num_devices):

    def batch_generator():
        n = tl.size()
        key = rng_key
        kk = batch_size // num_devices
        while True:
            key, k1 = jax.random.split(key)
            perm = jax.random.choice(k1, n, shape=(batch_size,))

            x, y = get_data(perm)

            yield x.reshape(num_devices, kk, *x.shape[1:]), y.reshape(num_devices, kk, *y.shape[1:])

    return batch_generator()

def dice_loss(inputs, gtr, smooth=1e-6):
    s1 = jnp.sum(gtr)
    s2 = jnp.sum(inputs)
    intersect = jnp.sum(jnp.dot(gtr, inputs))
    return jnp.mean(1 - ((2 * intersect + smooth) / (s1 + s2 + smooth)))


class ConvSimplifier(hk.Module):
    def __init__(self):
        super().__init__()
        self.bn = lambda: hk.BatchNorm(True, True, 0.98)

    def __call__(self, x, is_training):
        w_init = hki.VarianceScaling(1.0)
        b_init = hki.Constant(1e-6)
        
        x1 = hk.Conv2D(128, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x)
        x1 = self.bn()(x1, is_training)
        x1 = jnn.gelu(x1)

        x2 = hk.Conv2D(128, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x1)
        x2 = self.bn()(x2, is_training)
        x2 = jnn.gelu(x2)

        x3 = hk.Conv2D(256, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x2)
        x3 = self.bn()(x3, is_training)
        x3 = jnn.gelu(x3)

        x4 = hk.Conv2D(256, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x3)
        x4 = self.bn()(x4, is_training)
        x4 = jnn.gelu(x4)

        x5 = hk.Conv2D(512, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x4)
        x5 = self.bn()(x5, is_training)
        x5 = jnn.gelu(x5)


        x6 = hk.Conv2D(1024, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x5)
        x6 = self.bn()(x6, is_training)
        x6 = jnn.gelu(x6)

        x7 = hk.Conv2D(2048, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x6)
        x7 = self.bn()(x7, is_training)
        x7 = jnn.gelu(x7)

        x8 = hk.Conv2D(2048, 3, 2, padding="SAME", w_init=w_init, b_init=b_init)(x7)
        x8 = self.bn()(x8, is_training)
        x8 = jnn.gelu(x8)

        return x1, x2, x3, x4, x5, x6, x7, x8


class ConvInverse(hk.Module):
    def __init__(self):
        super().__init__()
        self.bn = lambda: hk.BatchNorm(True, True, 0.99)

    def __call__(self, x, is_training):
        w_init = hki.VarianceScaling(1.0)
        b_init = hki.Constant(1e-6)

        x1, x2, x3, x4, x5, x_reduced = x





