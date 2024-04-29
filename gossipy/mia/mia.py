from sklearn.utils import resample
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import numpy as np
import copy
from typing import Tuple, Dict, List
from sklearn.metrics import accuracy_score, roc_auc_score, recall_score, f1_score, precision_score
import os

def mia_for_each_nn(simulation, attackerNode, class_specific: bool = False):
    idx = attackerNode.idx
    nn = sorted(attackerNode.p2p_net.get_peers(idx), key=lambda x: int(x))
    model = copy.deepcopy(attackerNode.model_handler.model)
    mia_results = [[], []] if class_specific else []
    for node in simulation.nodes.values():
        if node.idx in nn:
            data = node.data
            train_data, test_data = data
            device = node.model_handler.device
            if class_specific:
                num_classes = max(train_data[1].max().item(), test_data[1].max().item())+1
                results= mia_best_th_class(model, train_data, test_data, num_classes, device)
                mia_results[0].append(results[0])
                mia_results[1].append(results[1])

            else:
                mia_results.append(mia_best_th(model, train_data, test_data, device))

    mia_results ={
        "loss_mia": np.mean(mia_results[0]),
        "entropy_mia": np.mean(mia_results[1])
    
    }
    return mia_results

def mia_best_th(model, train_data, test_data, device, nt=150):
    
    def search_th(train, test):
        thrs = np.linspace(min(train.min(), test.min()), max(train.max(), test.max()), nt)
        R = np.zeros_like(thrs)

        for i, th in enumerate(thrs):
            tp = (train < th).sum()
            tn = (test >= th).sum()
            acc = (tp + tn) / (len(train) + len(test))  # Correcting the calculation for accuracy
            R[i] = acc

        return R.max()

    model.eval()
    Ltrain, Ptrain, Ytrain = evaluate(model, device, train_data)
    Ltest, Ptest, Ytest = evaluate(model, device, test_data)
    model.train()

    # it takes a subset of results on test set with size equal to the one of the training test 
    n = min(Ptest.shape[0], Ptrain.shape[0])
    Ptrain = Ptrain[:n]
    Ytrain = Ytrain[:n]
    Ltrain = Ltrain[:n]

    loss_mia = search_th(Ltrain, Ltest)

    Etrain = compute_modified_entropy(Ptrain, Ytrain)
    Etest = compute_modified_entropy(Ptest, Ytest)

    ent_mia = search_th(Etrain, Etest)

    #print(f" Loss: {loss_mia}, Enthropy: {ent_mia}")

    return loss_mia, ent_mia

def mia_best_th_class(model, train_data, test_data, num_class, device, nt=200):
    
    def search_th(train, test, train_label, test_label, num_classes):
        thrs = np.linspace(min(train.min(), test.min()), max(train.max(), test.max()), nt)
        R = np.zeros((num_classes, len(thrs)))  # Initialize array for class-specific thresholds
        train_c = []
        test_c = []

        for c in range(num_classes):
            for i in range(min(len(train), len(test))):
                if train_label[i] == c:
                    train_c.append(train[i])
                if test_label[i] == c:
                    test_c.append(test[i])
            # Resample the training and testing data to have an equal size in each class
            train_c = resample(train_c, replace=False, n_samples=min(int(sum(train_label == c)), int(sum(test_label == c))))
            test_c = resample(test_c, replace=False, n_samples=min(int(sum(train_label == c)), int(sum(test_label == c))))

            for i, th in enumerate(thrs):
                # Count true positives and true negatives for each class
                tp = (train_c < th).sum()
                tn = (test_c >= th).sum()
                acc = (tp + tn) / (len(train_c) + len(test_c))

                R[c, i] = acc

        return R.max(axis=1)

    model.eval()
    Ltrain, Ptrain, Ytrain = evaluate(model, device, train_data)
    Ltest, Ptest, Ytest = evaluate(model, device, test_data)
    model.train()

    # it takes a subset of results on test set with size equal to the one of the training test
    n = min(Ptest.shape[0], Ptrain.shape[0])
    
    Ptrain = Ptrain[:n]
    Ytrain = Ytrain[:n]
    Ltrain = Ltrain[:n]

    th_indices_loss = search_th(Ltrain, Ltest, Ytrain, Ytest, num_class,)  # Class-specific thresholds for loss
    th_indices_ent = search_th(compute_modified_entropy(Ptrain, Ytrain), compute_modified_entropy(Ptest, Ytest), Ytrain, Ytest, num_class,)  # Class-specific thresholds for entropy

    return th_indices_loss, th_indices_ent

def compute_modified_entropy(p, y, epsilon=0.00001):
    """ Computes label informed entropy from 'Systematic evaluation of privacy risks of machine learning models' USENIX21 """
    assert len(y) == len(p)
    n = len(p)

    entropy = np.zeros(n)

    for i in range(n):
        pi = p[i]
        yi = y[i]
        for j, pij in enumerate(pi):
            if j == yi:
                # right class
                entropy[i] -= (1-pij)*np.log(pij+epsilon)
            else:
                entropy[i] -= (pij)*np.log(1-pij+epsilon)

    return entropy

def evaluate(model, device, data: Tuple[torch.Tensor, torch.Tensor]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:

    x, y = data
    model = model.to("cuda:0" if torch.cuda.is_available() else "cpu")
    x, y = x.to(device), y.to(device)

    losses = []
    preds = []
    labels = []

    for idx in range(len(x)):
        with torch.no_grad():
            scores = model(x[idx].unsqueeze(0))
            loss = torch.nn.functional.cross_entropy(scores, y[idx].unsqueeze(0))

            # Collect probability scores instead of class predictions
            prob_scores = torch.nn.functional.softmax(scores, dim=-1).cpu().numpy()
            label = y[idx].cpu().numpy()

            losses.append(loss.cpu().numpy())
            preds.append(prob_scores.reshape(1, -1))  # Store probability scores
            labels.append(label.reshape(1, -1))  # Ensure labels are added as arrays

    losses = np.array(losses)
    preds = np.concatenate(preds) if preds else np.array([])
    labels = np.concatenate(labels) if labels else np.array([])
    model = model.to("cpu")
    return losses, preds, labels

def compute_consensus_distance(nodes) -> float:
    num_nodes = len(nodes)
    consensus_distance = 0.0

    for node_v in nodes.values():
        local_params_v = node_v.model_handler.model.state_dict()
        pairwise_distance = 0.0

        for node_u in nodes.values():
            if node_u.idx != node_v.idx:  # Exclude self-comparison
                local_params_u = node_u.model_handler.model.state_dict()
                distance = sum((local_params_v[key] - local_params_u[key]).pow(2).sum().item() for key in local_params_v)
                pairwise_distance += distance / (num_nodes ** 2 - num_nodes)

        consensus_distance += pairwise_distance

    return consensus_distance

def compute_gen_errors(Simul, nodes) -> float:
    aggregated_acc_train = []
    aggregated_acc_test = []
    gen_error = []

    for _, node in nodes.items():
        acc_train = node.evaluate(node.data[0])["accuracy"]
        aggregated_acc_train.append(acc_train)
        if node.has_test():
            if Simul.data_dispatcher.has_test():
                acc_test = node.evaluate(node.data[1])["accuracy"]
                #acc_test = node.evaluate(self.data_dispatcher.get_eval_set())["accuracy"]
            else:
                acc_test = node.evaluate(node.data[1])["accuracy"]
            aggregated_acc_test.append(acc_test)

    # Compute the generalization error based on aggregated accuracies
    if aggregated_acc_train and aggregated_acc_test:
        avg_acc_train = sum(aggregated_acc_train) / len(aggregated_acc_train)
        avg_acc_test = sum(aggregated_acc_test) / len(aggregated_acc_test)
        gen_error_value = (avg_acc_train - avg_acc_test) / (avg_acc_test + avg_acc_train)
        gen_error.append(gen_error_value)
    else:
        gen_error.append(0)

    return gen_error
def get_gen_errors(acc_train, acc_test) -> float:
    return (acc_train - acc_test) / (acc_test + acc_train)

def assign_model_params(source_model, target_model):
    device = next(target_model.parameters()).device
    source_state_dict = source_model.state_dict()
    target_model.load_state_dict(source_state_dict, strict=False)
    target_model.to(device)
