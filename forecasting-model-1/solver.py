""" This file includes Python code licensed under the MIT License, 
    Copyright (c) 2018 Bjarte Mehus Sunde. 
    https://github.com/Bjarten/early-stopping-pytorch. """

import os
import torch
import numpy as np
import configparser
from tqdm import tqdm
import torch.nn as nn
import torch.optim as optim

from model import LSTMModel
from PlottingUtils import Visualizer
from pytorchtools import EarlyStopping


conf_path = './model_config_files/'

class Solver(object):
    """ Initialize configurations. """
    def __init__(self, device, input_size, minmaxscaler, train_dataloader, val_dataloader, test_dataloader=None):
        super(Solver, self).__init__()
        ################### READING PARAMETERS ####################
        config = configparser.ConfigParser()
        config.read(conf_path + 'model_config.cfg')

        mod_name = config['MODELINFO']['model_name']
        self.checkpoint_path = config['MODELINFO']['checkpoint_path']

        self.epochs = int(config['TRAINPARAMS']['epochs'])
        opt = config['TRAINPARAMS']['opt']
        lr = float(config['TRAINPARAMS']['lr'])
        self.early_stopping = int(config['TRAINPARAMS']['early_stopping'])

        hidden_size = int(config['MODELPARAMS']['hidden_size'])
        num_layers = int(config['MODELPARAMS']['num_layers'])
        output_size = int(config['MODELPARAMS']['output_size'])

        resume_train = int(config['TASK']['resume_train'])
        make_prediction = int(config['TASK']['make_prediction'])
        self.print_every = int(config['TASK']['print_every'])
        ##########################################################

        self.model_name = f'{mod_name}.pt'        
        
        self.device = device
        self.input_size = input_size
        self.train_dataloader = train_dataloader
        self.val_dataloader= val_dataloader
        self.test_dataloader = test_dataloader

        self.mm = minmaxscaler

        self.vz = Visualizer()

        self.set_seed(42)
        
        # Model definition
        self.model = LSTMModel(self.device, self.input_size, hidden_size, 
                               num_layers, output_size).to(self.device)
        
        print(f'\nNetwork:\n\n {self.model}\n')

        for name, p in self.model.named_parameters():
            print('%-32s %s' % (name, tuple(p.shape)))

        # load a pretrained model
        if resume_train == 1 or make_prediction == 1:
            self.load_model(device)
        
        # Loss definition
        self.criterion = nn.MSELoss()

        # Optimizer definition
        if opt == "SGD":
            self.optimizer = optim.SGD(self.model.parameters(), 
                                       lr=lr, momentum=0.9)
        elif opt == "Adam":
            self.optimizer = optim.Adam(self.model.parameters(), 
                                        lr=lr, betas=(0.9, 0.999))

    """ Helper function used to set random-seed. """
    def set_seed(self, seed=42):
        np.random.seed(seed)
        torch.manual_seed(seed)

    """ Helper function used to save the model. """
    def save_model(self):
        # if you want to save the model
        check_path = os.path.join(self.checkpoint_path, self.model_name)
        torch.save(self.model.state_dict(), check_path)
        print('\nModel saved!\n')

    """ Helper function used to load the model. """
    def load_model(self, device):
        # function to load the model
        check_path = os.path.join(self.checkpoint_path, self.model_name)
        self.model.load_state_dict(torch.load(check_path,
                                              map_location=torch.device(device)))
        print('\nModel loaded!\n')

    """ Training function. """
    def train(self):
        print('\nStarting the training...\n')

        avg_train_losses = []
        avg_test_losses = []

        train_y_trues = np.array([], dtype=np.float64)
        train_preds = np.array([], dtype=np.float64)

        check_path = os.path.join(self.checkpoint_path, self.model_name)
        # initialize the early_stopping object
        early_stopping = EarlyStopping(patience=self.early_stopping, 
                                       verbose=True, path=check_path)
        early_stp = False

        self.model.train()

        for epoch in range(self.epochs): # loop over the dataset multiple times
            # record the training and test losses for each batch in this epoch
            train_losses = []
            test_losses = []
            metrics = []

            loop = tqdm(enumerate(self.train_dataloader),
                        total=len(self.train_dataloader), leave=True)
                        
            for batch_idx, (X_batch, y_batch) in loop:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device) 

                # Inizializzazione del gradiente
                self.optimizer.zero_grad()
                
                # Forward pass
                y_pred = self.model(X_batch)

                # Calcolo della loss
                loss = self.criterion(y_pred, y_batch)
                
                # Backward pass
                loss.backward()
                
                # Aggiornamento dei pesi
                self.optimizer.step()

                train_losses.append(loss.item())

                train_y_trues = np.concatenate((y_batch.detach().numpy(), train_y_trues), axis=None)
                train_preds = np.concatenate((y_pred.detach().numpy(), train_preds), axis=None)
        
                if batch_idx % self.print_every == self.print_every - 1:                    
                    # used to check model improvement
                    self.test(test_losses, metrics)

                    batch_avg_train_loss = np.average(train_losses)
                    batch_avg_test_loss = np.average(test_losses)
                    batch_avg_metric = np.average(metrics)

                    avg_train_losses.append(batch_avg_train_loss)
                    avg_test_losses.append(batch_avg_test_loss)

                    print(f'\n\nEpoch: {epoch + 1}/{self.epochs}, ' 
                          f'Batch: {batch_idx + 1}/{len(self.train_dataloader)}, '
                          f'train-loss: {batch_avg_train_loss:.4f}, '
                          f'test-loss: {batch_avg_test_loss:.4f}, '
                          f'metrics: {batch_avg_metric}')
                    
                    self.plot_results(avg_train_losses, avg_test_losses, train_y_trues, train_preds)
                    
                    train_losses = []
                    test_losses = []
                    metrics = []

                    # early_stopping needs the validation loss to check if it has decresed, 
                    # and if it has, it will make a checkpoint of the current model
                    early_stopping(batch_avg_test_loss, self.model)

                    # evaluation on test-set
                    if self.test_dataloader is not None:
                         eval_loss, eval_metric = self.evaluate_on_test_set()
                         
                         print(f'\n\nEpoch: {epoch + 1}/{self.epochs}, '
                               f'Batch: {batch_idx + 1}/{len(self.train_dataloader)}, '
                               f'eval_loss: {eval_loss:.4f}, '
                               f'eval_metric: {eval_metric:.4f}')

                    if early_stopping.early_stop:
                        print('\nEarly stopping...')
                        early_stp = True
                        break

            if early_stp:
                break

            # save at the end of each epoch only if earlystopping = False
            self.save_model()  

        print('\n\nTraining finished...')
                    
    """ Evaluation of the model. """
    def test(self, test_losses, metrics):
        print('\n\nStarting the validation...\n')

        val_y_trues = np.array([], dtype=np.float64)
        val_preds = np.array([], dtype=np.float64)

        # put net into evaluation mode
        self.model.eval()  
        
        # no need to calculate the gradients for our outputs
        with torch.no_grad():
            test_loop = tqdm(enumerate(self.val_dataloader),
                             total=len(self.val_dataloader), leave=True)

            for _, (X_test, y_test) in test_loop:
                X_test = X_test.to(self.device)
                y_test = y_test.to(self.device)
                y_test_pred = self.model(X_test.detach())

                val_y_trues = np.concatenate((y_test.detach().numpy(), 
                                              val_y_trues), axis=None)
                val_preds = np.concatenate((y_test_pred.detach().numpy(), 
                                            val_preds), axis=None)

                test_loss = self.criterion(y_test_pred, y_test)     
                metric = torch.sqrt(test_loss)

                test_losses.append(test_loss.item())
                metrics.append(metric.item())

            self.vz.plot_predictions(self.mm.inverse_transform(val_y_trues.reshape(-1, 1)), 
                                     self.mm.inverse_transform(val_preds.reshape(-1, 1)), 
                                     'validation')           
        
        # put again the model in trainining-mode
        self.model.train()  

    """ Helper function used to evaluate the model in test set. """
    def evaluate_on_test_set(self):
        print('\n\nEvaluation on test set...\n')

        eval_y_trues = np.array([], dtype=np.float64)
        eval_preds = np.array([], dtype=np.float64)

        self.model.eval()

        with torch.no_grad():
            eval_losses = []
            metrics = []

            eval_loop = tqdm(enumerate(self.test_dataloader),
                             total=len(self.test_dataloader), leave=True)

            for _, (X_eval, y_eval) in eval_loop:
                X_eval = X_eval.to(self.device)
                y_eval = y_eval.to(self.device)
                y_eval_pred = self.model(X_eval.detach())

                # self.compute_confidence(y_eval_pred)

                eval_y_trues = np.concatenate((y_eval.detach().numpy(), eval_y_trues), axis=None)
                eval_preds = np.concatenate((y_eval_pred.detach().numpy(), eval_preds), axis=None)

                eval_loss = self.criterion(y_eval_pred, y_eval)                
                metric = torch.sqrt(eval_loss)     

                eval_losses.append(eval_loss.item())
                metrics.append(metric.item())

            avg_loss = np.average(eval_losses)
            avg_metric = np.average(metrics)

            self.vz.plot_predictions(self.mm.inverse_transform(eval_y_trues.reshape(-1, 1)), 
                                     self.mm.inverse_transform(eval_preds.reshape(-1, 1)), 
                                     'evaluation')
        
        self.model.train()

        return avg_loss, avg_metric

    """ Helper function used to plot some results. """
    def plot_results(self, avg_train_losses, avg_test_losses, y_trues, predictions):
        print('\nPlotting losses...')

        self.vz.plot_loss(avg_train_losses, avg_test_losses)

        self.vz.plot_predictions(self.mm.inverse_transform(y_trues.reshape(-1, 1)), 
                                 self.mm.inverse_transform(predictions.reshape(-1, 1)), 
                                 'training')

    """ Helper function used to compute the confidence 
        interval of model's prediction. """
    def compute_confidence(self, model_output):
        # Calcolo dell'intervallo di confidenza del 95%
        lower_bound = torch.quantile(model_output, 0.025, dim=0)
        upper_bound = torch.quantile(model_output, 0.975, dim=0)

        print("\nLower bound:", lower_bound.item()) # Stampa il valore inferiore dell'intervallo
        print("Upper bound:", upper_bound.item()) # Stampa il valore superiore dell'intervallo

        # return lower_bound, upper_bound

    """ Helper function to do. """
    def make_prediction(self, X):
        pass
        