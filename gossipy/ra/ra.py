from collections import OrderedDict
import torch
import numpy as np
import math

def w_fully_adv_init(W, mean, std, s):
    n, L = W.shape
    
    r = np.arange(L)
    _W = W.detach().numpy().copy()
    
    for i in range(n):
        mask = np.zeros(L)
        ids = np.random.choice(r, size=L//2, replace=False)
        mask[ids] = 1
        mask = mask.astype(bool)

        N = r[mask]
        P = r[~mask]

        zn = np.random.normal(mean, std, size=(L//2))
        zp = (-s) * zn
        np.random.shuffle(zp)
        _W[i, N] = zn
        _W[i, P] = zp

    W.data = torch.from_numpy(_W)
    
def invert_fully_g(gw, gb, i=None, epsilon=0.00001):
    b = 1. / (gb.detach().numpy()[np.newaxis,:] + epsilon)
    w = gw.detach().numpy().T

    if not i is None:
        x = b[:, i] * w[i, :]
    else:
        x = (np.matmul(b, w))
        print(b.shape, w.shape, x.shape)
    return x

def normalize_img(x):
    x += x.min()
    x -= x.min()
    x /= x.max()
    return x

def select_nn_mus(keys, buff):
    """ get only a subset of a dictonary """
    new_buff = {}
    for key in keys:
        name = key.name
        new_buff[name] = buff[name]
    return new_buff

def modify_filter(model, layer, i, j):
    kernel = model[layer]
    _kernel = kernel.detach().numpy()
    p1 = math.floor(_kernel.shape[0]/2)
    p2 = math.floor(_kernel.shape[1]/2)
    _kernel[:,:,i,j] = 1
    kernel.data = torch.from_numpy(_kernel)
