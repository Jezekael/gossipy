import wandb
import torch
import torch.nn.functional as F
from torchvision.transforms import Compose, Normalize
from gossipy.core import AntiEntropyProtocol, CreateModelMode, ConstantDelay, StaticP2PNetwork
from gossipy.data import CustomDataDispatcher, OLDCustomDataDispatcher
from gossipy.data.handler import ClassificationDataHandler
from gossipy.model.handler import TorchModelHandler
from gossipy.node import GossipNode, FederatedGossipNode, AttackGossipNode
from gossipy.simul import AttackGossipSimulator, AttackSimulationReport
from gossipy.model.architecture import *
from gossipy.model.resnet import *
from gossipy.data import get_CIFAR10, get_CIFAR100
from gossipy.topology import create_torus_topology, create_federated_topology, CustomP2PNetwork
from gossipy.attacks.utils import log_results
import networkx as nx
from networkx.generators import random_regular_graph
import os
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:256'

wandb.init(
    project="my-awesome-project",
    config={
        "learning_rate": 0.1,
        "momentum": 0.9,
        "weight_decay": 0.0005,
        "optimizer": "SGD",
        "architecture": "ResNet20",
        "dataset": "CIFAR-10",
        "epochs": 250,
        "batch_size": 64,
        "n_nodes": 4,
        "n_local_epochs": 3,
        "neigbors": 3,
        "test_size": 0.5,
        "factors": 10,
        "beta": 0.99,
        "p_attacker": 0.3,
        "mia": True,
        "mar": True,
        "echo": True,
        "ra": False
    }
)

from torchvision import datasets, transforms

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

from torch import Tensor, tensor
from torchvision import datasets

train_set = datasets.STL10(root='./data', split='train', download=True)
test_set = datasets.STL10(root='./data', split='test', download=True)

train_set = tensor(train_set.data).float().permute(0,1,3,2) / 255.,\
                tensor(train_set.labels)
test_set = tensor(test_set.data).float().permute(0,1,3,2) / 255.,\
            tensor(test_set.labels)

n_classes = max(train_set[1].max().item(), test_set[1].max().item())+1
model = resnet20(n_classes)
wdb = wandb.config

optimizer_params = {
    "lr":  wdb.learning_rate,
    "momentum": wdb.momentum,
    "weight_decay": wdb.weight_decay
}

message = f"Experiment with {wdb.architecture} on {wdb.dataset} dataset (test size : {wdb.test_size}, class distribution = {wdb.beta}). | Attacks: N°Attackers: {int(wdb.n_nodes * wdb.p_attacker)}, MIA: {wdb.mia}, MAR: {wdb.mar}, ECHO: {wdb.echo} | Training: {wdb.n_nodes} nodes, {wdb.n_local_epochs} local epochs, batch size {wdb.batch_size}, number of neigbors {wdb.neigbors} | Model: Optimizer: {wdb.optimizer}, lr {wdb.learning_rate},  momentum: {wdb.momentum}, weight_decay: {wdb.weight_decay} "

Xtr, ytr = ((train_set[0])), ((train_set[1]))
Xte, yte =( (test_set[0])), ((test_set[1]))

data_handler = ClassificationDataHandler(Xtr, ytr, Xte, yte, test_size= wdb.test_size)

'''
assignment_method = 'label_dirichlet_skew'
assignment_params = {
    'beta': wdb.beta
}

data_dispatcher = CustomDataDispatcher(
    data_handler,
    n=wdb.n_nodes * wdb.factors,
    eval_on_user=True,
    auto_assign=False
)

# Assign data using the specified method
data_dispatcher.assign(seed=42, method=assignment_method, **assignment_params)
'''

data_dispatcher = OLDCustomDataDispatcher(data_handler, n=wdb.n_nodes*wdb.factors, eval_on_user=True, auto_assign=True)

topology = StaticP2PNetwork(
    int(data_dispatcher.size() / wdb.factors),
    topology=nx.to_numpy_array(random_regular_graph(wdb.neigbors, wdb.n_nodes, seed=42))
)
nodes = AttackGossipNode.generate(
    data_dispatcher=data_dispatcher,
    p2p_net=topology,
    model_proto=TorchModelHandler(
        net=model,
        optimizer=torch.optim.SGD,
        optimizer_params=optimizer_params,
        criterion=F.cross_entropy,
        create_model_mode=CreateModelMode.MERGE_UPDATE,
        batch_size=wdb.batch_size,
        local_epochs=wdb.n_local_epochs),
    round_len=100,
    sync=False)

print(f"Number of nodes generated: {len(nodes)}")
for i, node in enumerate(nodes):
    print(f"Node {i} created")

for i, node in enumerate(nodes):
    nodes[i].mia = wdb.mia
    nodes[i].mar = wdb.mar
    if i % int(1/(wdb.p_attacker)) == 0:
        nodes[i].echo = wdb.echo
        nodes[i].ra = wdb.ra

simulator = AttackGossipSimulator(
    nodes=nodes,
    data_dispatcher=data_dispatcher,
    delta=100,
    protocol=AntiEntropyProtocol.PUSH,
    online_prob=1,
    drop_prob=0,
    sampling_eval=0,
    mia=wdb.mia,
    mar=wdb.mar,
    ra=wdb.ra
)

report = AttackSimulationReport()
simulator.add_receiver(report)
simulator.init_nodes(seed=42)
simulator.start(n_rounds=wdb.epochs, wall_time_limit=10.5)

log_results(simulator, report, wandb, message)
wandb.finish()