# -*- coding: utf-8 -*-#
'''
# Name:         math_graph
# Description:  
# Author:       neu
# Date:         2020/7/28
'''

import numpy as np
import pandas as pd
from scipy.sparse.linalg import eigs

import scipy.sparse as sp
from scipy.sparse.linalg.eigen.arpack import eigsh, ArpackNoConvergence


def weight_matrix(file_path, sigma2=0.1, epsilon=0.5, scaling=True):
    '''
    Load weight matrix function.
    加载权重矩阵
    :param file_path: str, the path of saved weight matrix file.
    :param sigma2: float, scalar of matrix W.
    :param epsilon: float, thresholds to control the sparsity of matrix W.
    :param scaling: bool, whether applies numerical scaling on W.
    :return: np.ndarray, [n_route, n_route].
    '''
    try:
        W = pd.read_csv(file_path, header=None).values
    except FileNotFoundError:
        print(f'ERROR: input file was not found in {file_path}.')

    # check whether W is a 0/1 matrix.
    if set(np.unique(W)) == {0, 1}:
        print('The input graph is a 0/1 matrix; set "scaling" to False.')
        scaling = False

    if scaling:
        # 根据真实距离计算邻接矩阵
        n = W.shape[0]
        W = W / 10000.
        W2, W_mask = W * W, np.ones([n, n]) - np.identity(n)
        # refer to Eq.10
        return np.exp(-W2 / sigma2) * (np.exp(-W2 / sigma2) >= epsilon) * W_mask
    else:
        return W


# 对邻接矩阵进行归一化处理
def normalize_adj(adj, symmetric=True):
    # 如果邻接矩阵为对称矩阵，得到对称归一化邻接矩阵
    # D^(-1/2) * A * D^(-1/2)
    if symmetric:
        # A.sum(axis=1)：计算矩阵的每一行元素之和，得到节点的度矩阵D
        # np.power(x, n)：数组元素求n次方，得到D^(-1/2)
        # sp.diags()函数根据给定的对象创建对角矩阵，对角线上的元素为给定对象中的元素
        d = sp.diags(np.power(np.array(adj.sum(1)), -0.5).flatten(), 0)
        # tocsr()函数将矩阵转化为压缩稀疏行矩阵
        a_norm = adj.dot(d).transpose().dot(d).tocsr()
    # 如果邻接矩阵不是对称矩阵，得到随机游走正则化拉普拉斯算子
    # D^(-1) * A
    else:
        d = sp.diags(np.power(np.array(adj.sum(1)), -1).flatten(), 0)
        a_norm = d.dot(adj).tocsr()
    return a_norm


# 在邻接矩阵中加入自连接
def preprocess_adj(adj, symmetric=True):
    adj = adj + sp.eye(adj.shape[0])
    # 对加入自连接的邻接矩阵进行对称归一化处理
    adj = normalize_adj(adj, symmetric)
    return adj


# 对拉普拉斯矩阵进行归一化处理
def normalized_laplacian(adj, symmetric=True):
    # 对称归一化的邻接矩阵，D ^ (-1/2) * A * D ^ (-1/2)
    adj_normalized = normalize_adj(adj, symmetric)
    # 得到对称规范化的图拉普拉斯矩阵，L = I - D ^ (-1/2) * A * D ^ (-1/2)
    laplacian = sp.eye(adj.shape[0]) - adj_normalized
    return laplacian


def scaled_laplacian(W):
    '''
    Normalized graph Laplacian function.
    归一化图拉普拉斯矩阵
    :param W: np.ndarray, [n_route, n_route], weighted adjacency matrix of G.
    :return: np.matrix, [n_route, n_route].
    '''
    # d ->  diagonal degree matrix
    n, d = np.shape(W)[0], np.sum(W, axis=1)
    # L -> graph Laplacian
    L = -W
    L[np.diag_indices_from(L)] = d
    for i in range(n):
        for j in range(n):
            if (d[i] > 0) and (d[j] > 0):
                L[i, j] = L[i, j] / np.sqrt(d[i] * d[j])
    # lambda_max \approx 2.0, the largest eigenvalues of L.
    lambda_max = eigs(L, k=1, which='LR')[0][0].real
    return np.mat(2 * L / lambda_max - np.identity(n))


# 重新调整对称归一化的图拉普拉斯矩阵，得到其简化版本
def rescale_laplacian(laplacian):
    try:
        print('Calculating largest eigenvalue of normalized graph Laplacian...')
        # 计算对称归一化图拉普拉斯矩阵的最大特征值
        largest_eigval = eigsh(laplacian, 1, which='LM', return_eigenvectors=False)[0]
    # 如果计算过程不收敛
    except ArpackNoConvergence:
        print('Eigenvalue calculation did not converge! Using largest_eigval=2 instead.')
        largest_eigval = 2

    # 调整后的对称归一化图拉普拉斯矩阵，L~ = 2 / Lambda * L - I
    scaled_laplacian = (2. / largest_eigval) * laplacian - sp.eye(laplacian.shape[0])
    return scaled_laplacian


def first_approx(W, n):
    '''
    1st-order approximation function.
    1阶近似函数
    :param W: np.ndarray, [n_route, n_route], weighted adjacency matrix of G.
    :param n: int, number of routes / size of graph.
    :return: np.ndarray, [n_route, n_route].
    '''
    A = W + np.identity(n)
    d = np.sum(A, axis=1)
    sinvD = np.sqrt(np.mat(np.diag(d)).I)
    # refer to Eq.5
    return np.mat(np.identity(n) + sinvD * A * sinvD)


# 计算直到k阶的切比雪夫多项式
def chebyshev_polynomial(X, k):
    # 返回一个稀疏矩阵列表
    """Calculate Chebyshev polynomials up to order k. Return a list of sparse matrices."""
    print("Calculating Chebyshev polynomials up to order {}...".format(k))

    T_k = list()
    T_k.append(sp.eye(X.shape[0]).tocsr())  # T0(X) = I
    T_k.append(X)  # T1(X) = L~

    # 定义切比雪夫递归公式
    def chebyshev_recurrence(T_k_minus_one, T_k_minus_two, X):
        """
        :param T_k_minus_one: T(k-1)(L~)
        :param T_k_minus_two: T(k-2)(L~)
        :param X: L~
        :return: Tk(L~)
        """
        # 将输入转化为csr矩阵（压缩稀疏行矩阵）
        X_ = sp.csr_matrix(X, copy=True)
        # 递归公式：Tk(L~) = 2L~ * T(k-1)(L~) - T(k-2)(L~)
        return 2 * X_.dot(T_k_minus_one) - T_k_minus_two

    for i in range(2, k + 1):
        T_k.append(chebyshev_recurrence(T_k[-1], T_k[-2], X))

    # 返回切比雪夫多项式列表
    return T_k

def cheb_poly_approx(L, Ks, n):
    '''
    Chebyshev polynomials approximation function.
    切比雪夫多项式近似
    :param L: np.matrix, [n_route, n_route], graph Laplacian.
    :param Ks: int, kernel size of spatial convolution.
    :param n: int, number of routes / size of graph.
    :return: np.ndarray, [n_route, Ks*n_route].
    '''
    L0, L1 = np.mat(np.identity(n)), np.mat(np.copy(L))

    if Ks > 1:
        L_list = [np.copy(L0), np.copy(L1)]
        for i in range(Ks - 2):
            Ln = np.mat(2 * L * L1 - L0)
            L_list.append(np.copy(Ln))
            L0, L1 = np.matrix(np.copy(L1)), np.matrix(np.copy(Ln))
        # L_lsit [Ks, n*n], Lk [n, Ks*n]
        return np.concatenate(L_list, axis=-1)
    elif Ks == 1:
        return np.asarray(L0)
    else:
        raise ValueError(f'ERROR: the size of spatial kernel must be greater than 1, but received "{Ks}".')



# 将稀疏矩阵转化为元组表示
def sparse_to_tuple(sparse_mx):
    if not sp.isspmatrix_coo(sparse_mx):
        # 将稀疏矩阵转化为coo矩阵形式
        # coo矩阵采用三个数组分别存储行、列和非零元素值的信息
        sparse_mx = sparse_mx.tocoo()
    # np.vstack()函数沿着数组的某条轴堆叠数组
    # 获取非零元素的位置索引
    coords = np.vstack((sparse_mx.row, sparse_mx.col)).transpose()
    # 获取矩阵的非零元素
    values = sparse_mx.data
    # 获取矩阵的形状
    shape = sparse_mx.shape
    return coords, values, shape