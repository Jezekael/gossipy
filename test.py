import os
from typing import Tuple, Union
import numpy as np
from PIL import Image
import torch

# Define the classes and contexts
CLASSES = {
    "car": 0, "flower": 1, "penguin": 2, "camel": 3, "chair": 4,
    "monitor": 5, "truck": 6, "wheat": 7, "sword": 8, "seal": 9,
    "lion": 10, "fish": 11, "dolphin": 12, "lifeboat": 13, "tank": 14,
    "fishing rod": 15, "sunflower": 16, "cow": 17, "bird": 18, "airplane": 19,
    "shark": 20, "rabbit": 21, "snake": 22, "hot air balloon": 23, "hat": 24,
    "spider": 25, "motorcycle": 26, "tortoise": 27, "dog": 28, "elephant": 29,
    "chicken": 30, "bee": 31, "gun": 32, "fox": 33, "phone": 34, "bus": 35,
    "cat": 36, "sailboat": 37, "cactus": 38, "pumpkin": 39, "train": 40,
    "dragonfly": 41, "ship": 42, "helicopter": 43, "bicycle": 44, "squirrel": 45,
    "bear": 46, "mailbox": 47, "horse": 48, "banana": 49, "mushroom": 50,
    "cauliflower": 51, "whale": 52, "camera": 53, "beetle": 54, "monkey": 55,
    "lemon": 56, "pepper": 57, "sheep": 58, "umbrella": 59
}

# Define the contexts
CONTEXTS = ["autumn", "dim", "grass", "outdoor", "rock", "water"]

def print_directory_structure(folder_path, indent=0):
    """Helper function to print the directory structure for debugging."""
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path):
            print("  " * indent + f"Directory: {item}")
            print_directory_structure(item_path, indent + 1)
        else:
            print("  " * indent + f"File: {item}")

def load_images_from_folder(folder_path, class_mapping, img_size=(224, 224), fraction=1.0):
    images = []
    labels = []
    contexts = []
    total_files = sum([len(files) for r, d, files in os.walk(folder_path)])
    processed_files = 0

    for root, dirs, files in os.walk(folder_path):
        for class_name in dirs:
            class_path = os.path.join(root, class_name)
            if class_name.lower() in class_mapping:
                class_label = class_mapping[class_name.lower()]
                print(f"Processing class: {class_name} with label: {class_label}")
                class_files = os.listdir(class_path)
                num_files_to_load = int(len(class_files) * fraction)
                selected_files = np.random.choice(class_files, num_files_to_load, replace=False)
                for filename in selected_files:
                    img_path = os.path.join(class_path, filename)
                    try:
                        img = Image.open(img_path).convert('RGB')
                        img = img.resize(img_size)  # Resize image
                        images.append(np.array(img))
                        labels.append(class_label)
                        contexts.append("")  # No context for test data
                    except Exception as e:
                        print(f"Error loading image: {img_path}, {e}")
                    processed_files += 1
                    if processed_files % 100 == 0:
                        print(f"Processed {processed_files}/{total_files} files.")

    return images, labels, contexts

def get_NICO(path: str = "./data", as_tensor: bool = True, train_fraction: float = 1.0, test_fraction: float = 1.0) -> Union[Tuple[Tuple[np.ndarray, list, list], Tuple[np.ndarray, list]], Tuple[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor]]]:
    """Returns the NICO++ dataset.

    Parameters
    ----------
    path : str, default="./data"
        Path to the root folder of NICO++ dataset.
    as_tensor : bool, default=True
        If True, returns data as PyTorch tensors, otherwise as numpy arrays.
    train_fraction : float, default=1.0
        Fraction of training data to load (1.0 means all data).
    test_fraction : float, default=1.0
        Fraction of test data to load (1.0 means all data).

    Returns
    -------
    Tuple[Tuple[np.ndarray, list, list], Tuple[np.ndarray, list]] or Tuple[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], Tuple[torch.Tensor, torch.Tensor]]
        Tuple of training and test sets: (X_train, y_train, c_train), (X_test, y_test).
        Here, c_train denotes the context for each image in the training set.
    """
    # Paths to training and test data
    train_folder = os.path.join(path, "NICO++", "track_1", "track_1", "public_dg_0416", "train")
    test_folder = os.path.join(path, "NICO++", "track_2", "track_2", "public_ood_0412_nodomainlabel", "train")

    # Print directory structure for debugging
    print("Training data directory structure:")
    print_directory_structure(train_folder)
    print("Test data directory structure:")
    print_directory_structure(test_folder)

    # Load training data
    print("Loading training data...")
    X_train, y_train, c_train = load_images_from_folder(train_folder, CLASSES, fraction=train_fraction)

    # Load test data (without contexts since they are not provided in the test set)
    print("Loading test data...")
    X_test, y_test, _ = load_images_from_folder(test_folder, CLASSES, fraction=test_fraction)

    # Convert lists to numpy arrays
    X_train = np.array(X_train)
    y_train = np.array(y_train)
    X_test = np.array(X_test)
    y_test = np.array(y_test)

    print(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
    print(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")

    if X_train.size == 0:
        print("No training data found. Please check the training data folder.")
        return None

    if as_tensor:
        # Convert numpy arrays to PyTorch tensors
        X_train = torch.tensor(X_train).float().permute(0, 3, 1, 2) / 255.
        y_train = torch.tensor(y_train)
        c_train = torch.tensor([CONTEXTS.index(c) if c in CONTEXTS else -1 for c in c_train])
        
        X_test = torch.tensor(X_test).float().permute(0, 3, 1, 2) / 255.
        y_test = torch.tensor(y_test)
    else:
        # Leave as numpy arrays
        c_train = [CONTEXTS.index(c) if c in CONTEXTS else -1 for c in c_train]

    return (X_train, y_train, c_train), (X_test, y_test)

# Example usage: Load 10% of training data and 20% of test data
print(get_NICO(train_fraction=0.1, test_fraction=0.2))