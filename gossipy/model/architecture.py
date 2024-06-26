import torch
import torch.nn as nn
import torch.nn.functional as F
from gossipy.model import TorchModel


class ResNet20(TorchModel):
    def __init__(self, num_classes=10):
        super(ResNet20, self).__init__()
        self.in_planes = 16
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.layer1 = self.make_layer(16, 16, 3)
        self.layer2 = self.make_layer(16, 32, 3, stride=2)
        self.layer3 = self.make_layer(32, 64, 3, stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(64, num_classes)
        self.init_weights()

    def make_layer(self, in_channels, out_channels, num_blocks, stride=1):
        layers = []
        layers.append(nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1))
        layers.append(nn.BatchNorm2d(out_channels))
        layers.append(nn.ReLU(inplace=True))
        for _ in range(1, num_blocks):
            layers.append(nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1))
            layers.append(nn.BatchNorm2d(out_channels))
            layers.append(nn.ReLU(inplace=True))
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        log = False
        if torch.isnan(x).any() and log:
            print("NaN detected after conv1")
        x = self.layer1(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after layer1")
        x = self.layer2(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after layer2")
        x = self.layer3(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after layer3")
        x = self.avgpool(x)  # Use the avgpool layer here
        if torch.isnan(x).any() and log:
            print("NaN detected after avgpool")
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after fc")
        return x

    def init_weights(self):  # Rename the method
        def _init(m: nn.Module):
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        self.apply(_init)
    
    def __repr__(self) -> str:
        return "Resnet20"

def resnet20(num_classes):
    return ResNet20(num_classes=num_classes)

class CIFAR10Net(TorchModel):
    def __init__(self, num_classes=10):
        super().__init__()
        self.fc1 = nn.Linear(32 * 32 * 3, 128)  # Adjusted input size to match the output of convolutions
        self.fc2 = nn.Linear(128, 10)

    def init_weights(self, *args, **kwargs) -> None:
        def _init_weights(m: nn.Module):
            if isinstance(m, nn.Linear) or isinstance(m, nn.Conv2d):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
        self.apply(_init_weights)

    def forward(self, x):
      
        x = x.view(-1, 32 * 32 * 3)
        x = F.leaky_relu(self.fc1(x))
        # x = F.relu(self.fc1(x))

        x = self.fc2(x)
        x = F.leaky_relu(x)
        return x

    def __repr__(self) -> str:
        return "CIFAR10Net(size=%d)" % self.get_size()

    def print_model_info(self):
        print("Model architecture:", self)
        print("Model parameters:")
        for name, param in self.named_parameters():
            print(f" - {name}: {param.size()}")
            print(f"{name}: {param.dtype}")
#-------------------------------------------------- TESTING ---------------------------------------------------#

class NewResNet20(TorchModel):
    def __init__(self, num_classes=10):
        super(ResNet20, self).__init__()
        self.in_planes = 16
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.layer1 = self.make_layer(16, 16, 5)  # Increased number of blocks
        self.layer2 = self.make_layer(16, 32, 5, stride=2)  # Increased number of blocks
        self.layer3 = self.make_layer(32, 64, 5, stride=2)  # Increased number of blocks
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(64, num_classes)
        self.init_weights()

    def make_layer(self, in_channels, out_channels, num_blocks, stride=1):
        layers = []
        layers.append(nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1))
        layers.append(nn.BatchNorm2d(out_channels))
        layers.append(nn.ReLU(inplace=True))
        for _ in range(1, num_blocks):
            layers.append(nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1))
            layers.append(nn.BatchNorm2d(out_channels))
            layers.append(nn.ReLU(inplace=True))
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        log = False
        if torch.isnan(x).any() and log:
            print("NaN detected after conv1")
        x = self.bn1(x)
        x = self.layer1(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after layer1")
        x = self.layer2(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after layer2")
        x = self.layer3(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after layer3")
        x = self.avgpool(x)  # Use the avgpool layer here
        if torch.isnan(x).any() and log:
            print("NaN detected after avgpool")
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        if torch.isnan(x).any() and log:
            print("NaN detected after fc")
        return x

    def init_weights(self):  # Rename the method
        def _init(m: nn.Module):
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        self.apply(_init)
    
    def __repr__(self) -> str:
        return "ResNet20"

def newresnet20(num_classes):
    return ResNet20(num_classes=num_classes)
