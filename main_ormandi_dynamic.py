from gossipy import set_seed
from gossipy.core import AntiEntropyProtocol, CreateModelMode, StaticP2PNetwork, ConstantDelay, UniformDynamicP2PNetwork
from gossipy.node import GossipNode
from gossipy.model.handler import PegasosHandler
from gossipy.model.nn import AdaLine
from gossipy.data import load_classification_dataset, DataDispatcher
from gossipy.data.handler import ClassificationDataHandler
from gossipy.simul import GossipSimulator, DynamicGossipSimulator, SimulationReport
from gossipy.utils import plot_evaluation
import networkx as nx
from networkx.generators import random_regular_graph

# AUTHORSHIP
__version__ = "0.0.1"
__author__ = "Mirko Polato"
__copyright__ = "Copyright 2022, gossipy"
__license__ = "MIT"
__maintainer__ = "Mirko Polato, PhD"
__email__ = "mak1788@gmail.com"
__status__ = "Development"
#

set_seed(42)
X, y = load_classification_dataset("spambase", as_tensor=True)
y = 2 * y - 1  # convert 0/1 labels to -1/1

data_handler = ClassificationDataHandler(X, y, test_size=.1)
data_dispatcher = DataDispatcher(data_handler, n=100, eval_on_user=False, auto_assign=True)
# topology = StaticP2PNetwork(data_dispatcher.size(), topology=nx.to_numpy_array(random_regular_graph(3,100, seed=42)))

topology = UniformDynamicP2PNetwork(data_dispatcher.size(),
                                    topology=nx.to_numpy_array(random_regular_graph(3, 100, seed=42)))

model_handler = PegasosHandler(net=AdaLine(data_handler.size(1)),
                               learning_rate=.01,
                               create_model_mode=CreateModelMode.MERGE_UPDATE)

# For loop to repeat the simulation
nodes = GossipNode.generate(data_dispatcher=data_dispatcher,
                            p2p_net=topology,
                            model_proto=model_handler,
                            round_len=100,
                            sync=False)

simulator = DynamicGossipSimulator(
    nodes=nodes,
    data_dispatcher=data_dispatcher,
    delta=100,
    protocol=AntiEntropyProtocol.PUSH,
    delay=ConstantDelay(0),
    online_prob=1,  # Approximates the average online rate of the STUNner's smartphone traces
    drop_prob=0,  # 0.1 Simulate the possibility of message dropping,
    sampling_eval=.2,
    peer_sampling_period=10
)

report = SimulationReport()
simulator.add_receiver(report)
simulator.init_nodes(seed=42)
simulator.start(n_rounds=10000)

plot_evaluation([[ev for _, ev in report.get_evaluation(False)]], "Overall test results")
# plot_evaluation([[ev for _, ev in report.get_evaluation(True)]], "User-wise test results")
