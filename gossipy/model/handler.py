from __future__ import annotations
import copy
import torch
import numpy as np
from typing import Any, Callable, Tuple, Dict
from sklearn.metrics import accuracy_score, roc_auc_score, recall_score, f1_score, precision_score
from .. import Sizeable, CreateModelMode, EqualityMixin
from . import TorchModel

__all__ = ["ModelHandler", "TorchModelHandler"]


class ModelHandler(Sizeable, EqualityMixin):
    def __init__(self,
                 create_model_mode: CreateModelMode=CreateModelMode.UPDATE):
        self.model = None
        self.mode = create_model_mode
        self.n_updates = 0

    def init(self, *args, **kwargs) -> None:
        raise NotImplementedError()

    def _update(self, data: Any) -> None:
        raise NotImplementedError()

    def _merge(self, other_model_handler: ModelHandler) -> None:
        raise NotImplementedError()

    def __call__(self,
                 recv_model: Any,
                 data: Any,
                 *args,
                 **kwargs) -> None:
        if self.mode == CreateModelMode.UPDATE:
            recv_model._update(data)
            self.model = copy.deepcopy(recv_model.model)
            self.n_updates = recv_model.n_updates
        elif self.mode == CreateModelMode.MERGE_UPDATE:
            self._merge(recv_model)
            self._update(data)
        elif self.mode == CreateModelMode.UPDATE_MERGE:
            self._update(data)
            recv_model._update(data)
            self._merge(recv_model)
        else:
            raise ValueError("Unknown create model mode %s" %str(self.mode))

    def evaluate(self, *args, **kwargs) -> Any:
        raise NotImplementedError()

    def copy(self) -> Any:
        return copy.deepcopy(self)
    
    def get_size(self) -> int:
        return self.model.get_size() if self.model is not None else 0


class TorchModelHandler(ModelHandler):
    def __init__(self,
                 net: TorchModel,
                 optimizer: torch.optim.Optimizer,
                 criterion: Callable[[torch.Tensor, torch.Tensor], torch.Tensor],
                 l2_reg: float=0.01,
                 learning_rate: float=0.001,
                 create_model_mode: CreateModelMode=CreateModelMode.UPDATE,
                 copy_model=True):
        super(TorchModelHandler, self).__init__(create_model_mode)
        self.model = copy.deepcopy(net) if copy_model else net
        self.optimizer = optimizer(self.model.parameters(),
                                   lr=learning_rate,
                                   weight_decay=l2_reg)
        self.criterion = criterion

    def init(self) -> None:
        self.model.init_weights()

    def _update(self, data: Tuple[torch.Tensor, torch.Tensor]) -> None:
        x, y = data
        self.model.train()
        y_pred = self.model(x)
        loss = self.criterion(y_pred, y)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.n_updates += 1

    def _merge(self, other_model_handler: TorchModelHandler) -> None:
        dict_params1 = self.model.state_dict()
        dict_params2 = other_model_handler.model.state_dict()

        for key in dict_params1:
            dict_params2[key] = (dict_params1[key] + dict_params2[key]) / 2.

        self.model.load_state_dict(dict_params2)

    def evaluate(self,
                 data: Tuple[torch.Tensor, torch.Tensor]) -> Dict[str, int]:
        x, y = data
        self.model.eval()
        scores = self.model(x)

        if y.dim() == 1:
            y_true = y.cpu().numpy().flatten()
        else:
            y_true = torch.argmax(y, dim=-1).cpu().numpy().flatten()

        pred = torch.argmax(scores, dim=-1)
        y_pred = pred.cpu().numpy().flatten()
        
        res = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "f1_score": f1_score(y_true, y_pred, zero_division=0)
        }

        if scores.shape[1] == 2:
            auc_scores = scores[:, 1].detach().cpu().numpy().flatten()
            if len(set(y_true)) == 2:
                res["auc"] = roc_auc_score(y_true, auc_scores).astype(float)
            else:
                res["auc"] = 0.5 #TODO: warning
        return res