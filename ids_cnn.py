# -*- coding: utf-8 -*-
"""IDS_CNN_new_new.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1LuBk84GRbG2XdOTlqvhFZgWsVAAlroE2
"""

# remove these lines if not running on notebooks
#%matplotlib notebook
run_from_notebook = False

from google.colab import drive
drive.mount('/content/drive')

"""## Import the required packages
Insert here all the packages you require, so in case they are not found an error will be shown before any other operation is performed.
"""

# import the required packages
import os
from os.path import exists
import time
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import pandas as pd
import csv
import glob
from zipfile import ZipFile
from torch.utils.data import Dataset, DataLoader
from torchsampler import ImbalancedDatasetSampler #pip install torchsampler
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import math
from sklearn.metrics import f1_score

path_to_file = 'MachineLearningCVE'
file_exists = exists(path_to_file)

if file_exists :
    print(f'The file {path_to_file} exists')

else :
   with ZipFile('/content/drive/MyDrive/IDS_CNN/MachineLearningCSV.zip', 'r') as zipObj:
      
      zipObj.extractall()

gpu_info = !nvidia-smi
gpu_info = '\n'.join(gpu_info)
if gpu_info.find('failed') >= 0:
  print('Not connected to a GPU')
else:
  print(gpu_info)

from psutil import virtual_memory
ram_gb = virtual_memory().total / 1e9
print('Your runtime has {:.1f} gigabytes of available RAM\n'.format(ram_gb))

if ram_gb < 20:
  print('Not using a high-RAM runtime')
else:
  print('You are using a high-RAM runtime!')

"""## Set hyperparameters and options
Set here your hyperparameters (to be used later in the code), so that you can run and compare different experiments operating on these values. 
<br>_Note: a better alternative would be to use command-line arguments to set hyperparameters and other options (see argparse Python package)_
"""

# hyperparameters
batch_size = 32
learning_rate = 0.001
epochs = 100
momentum = 0.1
lr_step_size = 1000   # if < epochs, we are using decaying learning rate
lr_gamma = 0.1
data_augmentation = True
dropout = 0.1
activation = nn.ReLU()
block_dim = 10
input_dim = 78*block_dim
num_classes = 2

# make visible only one GPU at the time
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # <-- should be the ID of the GPU you want to use

# options
device = "cuda:0"           # put here "cuda:0" if you want to run on GPU
monitor_display = True      # whether to display monitored performance plots
display_first_n = 0         # how many samples/batches are displayed
num_workers = 4             # how many workers (=threads) for fetching data
pretrained = False          # whether to test a pretrained model (to be loaded) or train a new one
display_errors = True       # whether to display errors (only in pretrained mode)

"""## Define the model architecture
Define here your network.
<br>_Note: a better alternative would be to have a pool of network architectures defined in a python file (module) that one could import_
"""

class IDSNet(nn.Module):
    def __init__(self,block_dim,num_classes,device):
        super(IDSNet, self).__init__()
        # kernel
        self.block_dim = block_dim
        self.num_classes = num_classes

        conv_layers = []
        conv_layers.append(nn.Conv1d(in_channels=78,out_channels=64,kernel_size=3,padding=1)) # ;input_dim,64
        conv_layers.append(nn.BatchNorm1d(64))
        conv_layers.append(nn.ReLU(True))

        conv_layers.append(nn.Conv1d(in_channels=64,out_channels=128,kernel_size=3,padding=1)) #(input_dim,128)
        conv_layers.append(nn.BatchNorm1d(128))
        conv_layers.append(nn.ReLU(True))

        self.conv = nn.Sequential(*conv_layers).to(device)

        fc_layers = []
        fc_layers.append(nn.Linear(block_dim*128,num_classes))
        self.classifier = nn.Sequential(*fc_layers).to(device)

    def forward(self, x):
        x = self.conv(x)
        x = torch.flatten(x,1)
        x = self.classifier(x)
        return x

class IDSNet2(nn.Module):
    def __init__(self,block_dim,num_classes,device):
        super(IDSNet2, self).__init__()
        # kernel
        self.block_dim = block_dim
        self.num_classes = num_classes
        
        
        self.layers = nn.Sequential(
            nn.Linear(block_dim*78, num_classes),

        )

    def forward(self, x):
      x = torch.flatten(x,1)
      x = self.layers(x)
      return x

"""## Create the building blocks for training
Create an instance of the network, the loss function, the optimizer, and learning rate scheduler.
"""

net = IDSNet(block_dim=block_dim,num_classes= num_classes, device=device)


# create loss function
criterion = nn.CrossEntropyLoss()

# create Adam optimizer
optimizer = optim.Adam(net.parameters(),lr=learning_rate)

# create learning rate scheduler
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=lr_step_size, gamma=lr_gamma)

# experiment ID
experiment_ID = "%s_%s_%s_bs(%d)lr(%.4f_%d_%.1f)m(%.1f)e(%d)act(%s)xavier(yes)da(%s)do(%.1f)BN" % (type(net).__name__, type(criterion).__name__, type(optimizer).__name__,
                batch_size, learning_rate, lr_step_size, lr_gamma, momentum, epochs, type(activation).__name__, data_augmentation, dropout)

"""## Load csv data
Load data in multiple CSV file 
"""

#read in all csv file

base_dir = "MachineLearningCVE"


all_files = glob.glob(os.path.join(base_dir, "*.csv"))

data = pd.concat((pd.read_csv(f) for f in all_files), ignore_index = True)


print("Finished reading in {} entires".format(str(data.shape[0])))

"""## Cleaning Data

"""

data.rename(columns=lambda x: x.lower().lstrip()
          .rstrip().replace(" ", "_"), inplace=True)
data.columns

data.info()

#Checking for NULL values:

print('Null values in the dataset are: ',len(data[data.isnull().any(1)]))

data.replace([np.inf, -np.inf], np.nan, inplace=True)
data.dropna(inplace=True)
data.reset_index(drop=True, inplace=True)

data.head()

"""## Conversion of Classification
These blocks convert Multiclass classification in binary classification
"""

label_binary = []
for i in data['label'].values:
    if i=='BENIGN':
        label_binary.append(1)
    else:
        label_binary.append(0)
print(len(label_binary))
print(label_binary[:10])

data['label_binary'] = label_binary
data.head()

data.drop('label', axis=1, inplace=True)
print('Shape of the data is:')
print(data.shape)
print('='*80)
print('Features of the dataset:')
print(data.columns)

data.head()

"""## Visualizes the data"""

data["label_binary"].value_counts()

data["label_binary"].value_counts(normalize=True)

data[data["label_binary"] != "1"]["label_binary"].value_counts().plot(kind='bar')

path_to_file = 'dataset.csv'
file_exists = exists(path_to_file)

if file_exists :
    print(f'The file {path_to_file} exists')

else :
    data.to_csv('dataset.csv', index=False)

"""## Dataset Generator"""

class CsvDataset(Dataset) :
    def __init__(self, file_name, block_dim, transform = None) :

        #read csv file and load row data into variables
        file_out = pd.read_csv(file_name)
        self.x = file_out.iloc[1:, 0:78].values
        self.y = file_out.iloc[1:, 78].values

        self.block_dim = block_dim
        
        
        self.num_sample = math.floor(len(self.x)/block_dim)

        self.data_sample = []
        
        for i in range(self.num_sample):
            sample = self.x[i*block_dim]
            

            for j in range(i*block_dim, (i*block_dim)+self.block_dim-1) :
                sample = np.concatenate((sample, self.x[j]), axis=0)
            
            self.data_sample.append(sample)     


        self.transform = transform
        
        self.targets = [] 

        for i in range(self.num_sample) :
            target = 1

            for j in range(i*block_dim, (i*block_dim)+block_dim-1) :
                if self.y[j] == 0 :
                    target = 0
                    break
            
            self.targets.append(target)

        self.targets = torch.tensor(self.targets)
            

    def __len__(self) :
        return self.num_sample

    def __getitem__(self, index) :
        sample = self.data_sample[index]
        sample = np.reshape(sample, (-1, block_dim))

        if self.transform:
            sample = self.transform(sample)

        target = self.targets[index]

        return sample, target

path1_to_file = 'test_dataset.csv'
file1_exists = exists(path1_to_file)

path2_to_file = 'x_test.csv'
file2_exists = exists(path2_to_file)

path3_to_file = 'y_test.csv'
file3_exists = exists(path3_to_file)

if file1_exists:
  if file2_exists and file3_exists:
    print(f'The files {path2_to_file}, {path3_to_file}  exist')
  else :
    file_out = pd.read_csv("test_dataset.csv")
    x = file_out.iloc[1:, 0:78].values
    y = file_out.iloc[1:, 78].values
    np.savetxt("x_test.csv", x, delimiter=",")
    np.savetxt("y_test.csv", y, delimiter=",")

else:
  print('Execute only for debug')

path1_to_file = 'train_dataset.csv'
file1_exists = exists(path1_to_file)

path2_to_file = 'x_train.csv'
file2_exists = exists(path2_to_file)

path3_to_file = 'y_train.csv'
file3_exists = exists(path3_to_file)

if file1_exists:
  if file2_exists and file3_exists:
    print(f'The files {path2_to_file}, {path3_to_file}  exist')
  else :
    file_out = pd.read_csv("train_dataset.csv")
    x = file_out.iloc[1:, 0:78].values
    y = file_out.iloc[1:, 78].values
    np.savetxt("x_train.csv", x, delimiter=",")
    np.savetxt("y_train.csv", y, delimiter=",")

else:
  print('Execute only for debug')

"""## Create Datasets

This includes training/validation split, where possible. In our example, MNIST does not have a validation set, so we use the test set as validation set (warning: see comments in the code).
Note: in general, you might need to implement your own Dataset in a separate Python file, and then import it in this file in order to create the dataset. The training/validation/test data split is also on your own, you may consider to embed it in your Dataset class
"""

train = data.iloc[1:1979514, :]
test = data.iloc[1979514:, :]

path1_to_file = 'train_dataset.csv'
file1_exists = exists(path1_to_file)

path2_to_file = 'test_dataset.csv'
file2_exists = exists(path2_to_file)


if file1_exists and file2_exists:
    print(f'The files {path1_to_file}, {path2_to_file}  exist')

else :
  train = data.iloc[1:1979514, :]
  test = data.iloc[1979514:, :]
  train.to_csv('train_dataset.csv', index=False)
  test.to_csv('test_dataset.csv', index=False)

dataset_train = CsvDataset(file_name='train_dataset.csv', block_dim = block_dim)
dataset_valid = CsvDataset(file_name='test_dataset.csv', block_dim = block_dim)

train["label_binary"].value_counts()

train["label_binary"].value_counts(normalize=True)

train[train["label_binary"] != "1"]["label_binary"].value_counts().plot(kind='bar')

test["label_binary"].value_counts()

test["label_binary"].value_counts(normalize=True)

test[test["label_binary"] != "1"]["label_binary"].value_counts().plot(kind='bar')

sample,target = dataset_train[1]

print(len(sample))
print(sample)
sample.shape
print(target)

"""## Data Scaler

"""

# Standardizing
def apply_scaler(X, scaler):
    X_tmp = []
    for x in X:
        x_shape = x.shape
        X_tmp.append(scaler.transform(x.flatten()[:,np.newaxis]).reshape(x_shape))
    X_tmp = np.array(X_tmp)
    return X_tmp

scaler = StandardScaler()
scaler.fit(np.vstack(dataset_train.data_sample).flatten()[:,np.newaxis].astype(float))
dataset_train.data_sample = apply_scaler(dataset_train.data_sample, scaler)
dataset_valid.data_sample = apply_scaler(dataset_valid.data_sample, scaler)

"""## Define data transforms
Data transforms are applied sample-wise at _batch generation_ time: they are _not_ applied until you use a Dataloader and fetch data from it. In general, they serve to transform your data into what the neural network expects. Data should be _at least_ converted to tensors whose shape corresponds to network input, and possibly normalized so as to be 0-centered roughly in the [-1,1] range. 

In this example, we also apply a transform to the targets (labels), so as to have one-hot tensor that can be compared with network outputs using the loss function.

Optionally, we may also apply data augmentation (on the training set, only).
"""

class Convert(object):
    def __call__(self, sample):
      return torch.from_numpy(sample).float()

# define data transform for train
transform_train = Convert()

# define data transform for validation
transform_valid = Convert()

# set data and target transforms on both datasets
dataset_train.transform = transform_train
dataset_valid.transform = transform_valid

sample, target = dataset_train[1]

print(sample.size())
print(sample)
print(target)

"""## Create data loaders
Dataloaders are in-built PyTorch objects that serve to sample batches from datasets. 
"""

# create data loaders
# NOTE 1: shuffle helps training
# NOTE 2: in test mode, batch size can be as high as the GPU can handle (faster, but requires more GPU RAM)

dataloader_train = torch.utils.data.DataLoader(
    dataset_train,
    sampler=ImbalancedDatasetSampler(dataset_train, labels=dataset_train.targets),
    batch_size=batch_size,
    num_workers=num_workers,
    pin_memory=True
)

dataloader_valid = torch.utils.data.DataLoader(
    dataset_valid, 
    batch_size=batch_size, 
    num_workers=num_workers, 
    pin_memory=True
)

"""## Define train function
It is preferable (but not mandatory) to embed training (1 epoch) code into a function, and call that function later during the training phase, at each epoch.
"""

# define train function (1 epoch)
# returns average loss and accuracy
def train(dataset, dataloader):

    # switch to train mode
    net.train()

    # reset performance measures
    loss_sum = 0.0
    #correct = 0

    train_targets = []
    train_outputs = []


    # 1 epoch = 1 complete loop over the dataset
    for batch in dataloader:

        # get data from dataloader
        inputs, targets = batch

        # move data to device
        inputs, targets = inputs.to(device, non_blocking=True), targets.to(device, non_blocking=True)

        # zero the parameter gradients
        optimizer.zero_grad()

        # forward pass
        outputs = net(inputs)

        # calculate loss
        loss = criterion(outputs, targets)

        # loss gradient backpropagation
        loss.backward()

        # net parameters update
        optimizer.step()

        # accumulate loss
        loss_sum += loss.item()

       

    

        # accumulate correct outputs (for accuracy calculation)
        outputs_max = torch.argmax(outputs, dim=1)
        targets_max = targets #torch.argmax(targets, dim=1)
        #correct += outputs_max.eq(targets_max).sum().float().detach().cpu().numpy()

        train_outputs.append(outputs_max)
        train_targets.append(targets_max)

        #print(train_outputs)
        #print(train_targets)

    # step learning rate scheduler
    scheduler.step()

   

    train_outputs = torch.cat(train_outputs)
    train_targets = torch.cat(train_targets)

    train_outputs = train_outputs.detach().cpu().numpy()
    train_targets = train_targets.detach().cpu().numpy()

    # return average loss and accuracy
    return loss_sum / len(dataloader), f1_score(train_outputs, train_targets, average='binary')

"""## Define test function
It is preferable (but not mandatory) to embed the test code into a function, and call that function whenever needed. For instance, during training for validation at each epoch, or after training for testing, or for deploying the model.
"""

# define test function
# returns predictions
def test(dataset, dataloader):

    # switch to test mode
    net.eval()  

    # initialize predictions
    predictions = torch.zeros(len(dataset), dtype=torch.int64)
    sample_counter = 0

    # do not accumulate gradients (faster)
    with torch.no_grad():

        # test all batches
        for batch in dataloader:

            # get data from dataloader [ignore labels/targets as they are not used in test mode]
            inputs = batch[0]

            # move data to device
            inputs = inputs.to(device, non_blocking=True)

            # forward pass
            outputs = net(inputs)

            # store predictions
            outputs_max = torch.argmax(outputs, dim=1)
            for output in outputs_max:
                predictions[sample_counter] = output
                sample_counter += 1

    return predictions

"""## Train a new model or test a pretrained one
The code below also includes visual loss/accuracy monitoring during training, both on training and validation sets. 
"""

# pretrained model not available --> TRAIN a new one and save it
if not pretrained:
    
    # reset performance monitors
    losses = []
    train_accuracies = []
    valid_accuracies = []
    ticks = []
    
    # move net to device
    net.to(device)
    
    # start training
    for epoch in range(1, epochs+1):

        # measure time elapsed
        t0 = time.time()
        
        # train
        avg_loss, accuracy_train = train(dataset_train, dataloader_train)

        # test on validation
        predictions = test(dataset_valid, dataloader_valid)
        #accuracy_valid = 100. * predictions.eq(dataset_valid.targets).sum().float() / len(dataset_valid)
        accuracy_valid = f1_score(predictions,dataset_valid.targets, average='binary')            
        # update performance history
        losses.append(avg_loss)
        train_accuracies.append(accuracy_train)
        valid_accuracies.append(accuracy_valid)
        ticks.append(epoch)
            


        # print or display performance
        if not monitor_display:    
            print ("\nEpoch %d\n"
                "...TIME: %.1f seconds\n"
                "...loss: %g (best %g at epoch %d)\n"
                "...training accuracy: %.2f%% (best %.2f%% at epoch %d)\n"
                "...validation accuracy: %.2f%% (best %.2f%% at epoch %d)" % (
                epoch,
                time.time()-t0,
                avg_loss, min(losses), ticks[np.argmin(losses)],
                accuracy_train, max(train_accuracies), ticks[np.argmax(train_accuracies)],
                accuracy_valid, max(valid_accuracies), ticks[np.argmax(valid_accuracies)]))
            
        else:
            fig, ax1 = plt.subplots(figsize=(12, 8), num=1)
            ax1.set_xticks(np.arange(0, epochs+1, step=epochs/10.0))
            ax1.set_xlabel('Epochs')
            ax1.set_ylabel(type(criterion).__name__, color='blue')
            ax1.set_ylim(0.0001, 1)
            ax1.tick_params(axis='y', labelcolor='blue')
            ax1.set_yscale('log')
            ax1.plot(ticks, losses, 'b-', linewidth=1.0, aa=True, 
                label='Training (best at ep. %d)' % ticks[np.argmin(losses)])
            ax1.legend(loc="lower left")
            ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
            ax2.set_ylabel('F1Score', color='red')
            ax2.set_ylim(0.5, 1)
            ax2.set_yticks(np.arange(0.5, 1, step=0.02))
            ax2.tick_params(axis='y', labelcolor='red')
            ax2.plot(ticks, train_accuracies, 'r-', linewidth=1.0, aa=True, 
                label='Training (%.2f, best %.2f at ep. %d)' % (accuracy_train, max(train_accuracies), ticks[np.argmax(train_accuracies)]))
            ax2.plot(ticks, valid_accuracies, 'r--', linewidth=1.0, aa=True, 
                label='Validation (%.2f, best %.2f at ep. %d)' % (accuracy_valid, max(valid_accuracies), ticks[np.argmax(valid_accuracies)]))
            ax2.legend(loc="lower right")
            plt.xlim(0, epochs+1)
            # this works if running from notebooks
            if run_from_notebook:
                fig.show()
                fig.canvas.draw()
            # this works if running from console
            else:
                plt.draw()
                #plt.pause(0.001)
                plt.show()
           # plt.savefig(experiment_ID + ".png", dpi=300)
            fig.clear()

        # save model if validation performance has improved
        if (epoch-1) == np.argmax(valid_accuracies):
            torch.save({
                'net': net,
                'accuracy': max(valid_accuracies),
                'epoch': epoch
            }, experiment_ID + ".tar")

# pretrained model available -> load it and test
else:

    # load pretrained model
    checkpoint = torch.load(experiment_ID + ".tar", map_location=lambda storage, loc: storage)
    net = checkpoint['net']
    print ("Loaded pretrained model\n...trained for %d epochs\n...reached accuracy %.2f" % (checkpoint['epoch'], checkpoint['accuracy']))

    # move net to device
    net.to(device)

    # test
    predictions = test(dataset_valid, dataloader_valid)
    accuracy = 100. * predictions.eq(dataset_valid.targets).sum().float() / len(dataset_valid)
    print ("Accuracy on test set is %.2f" % accuracy)

    # display errors
    if display_errors:

        # predictions / target comparisons = 1 for match, 0 for mismatch
        # we subtract 1, so we have 0 for match, -1 for mismatch
        # nonzero elements are thus all mismatches
        errors = torch.nonzero(~predictions.eq(dataset_valid.targets))

        # get errors samples and convert them to torch tensors
        error_samples = torch.zeros(len(errors), 1, 28, 28)
        conversion = Convert()
        for i, e in enumerate(errors):
            error_samples[i] = conversion(dataset_valid.data[e.item()])

        # make a grid of images and show
        img = torchvision.utils.make_grid(error_samples, nrow=20)
        img = img/255       # move data to [0,1] since pyplot expects float images to be in [0,1]
        npimg = img.numpy() # convert to numpy, since pyplot expects numpy images
        plt.imshow(np.transpose(npimg, (1, 2, 0)))  # CHW to WHC reshape
        plt.title('Errors')
        plt.show()