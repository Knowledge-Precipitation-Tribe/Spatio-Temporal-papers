# -*- coding: utf-8 -*-#
'''
# Name:         n麦
# Description:  
# Author:       neu
# Date:         2020/7/28
'''
from os.path import join as pjoin

from data_loader.data_utils import *
from utils.math_graph import *

from keras.layers import Input, Dropout
from keras.models import Model
from keras.optimizers import Adam
from keras.regularizers import l2

from models.layer import *

n = 228
n_his = 12
n_pred = 9

W = weight_matrix(pjoin('./data_loader/data', f'W_228.csv'))
data_file = f'V_228.csv'
n_train, n_val, n_test = 34, 5, 5
PeMS = data_gen(pjoin('./data_loader/data', data_file), (n_train, n_val, n_test), n, n_his + n_pred)
print(f'>> Loading dataset with Mean: {PeMS.mean:.2f}, STD: {PeMS.std:.2f}')