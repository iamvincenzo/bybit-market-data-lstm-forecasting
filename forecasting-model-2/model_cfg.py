""" This file includes Python code licensed under the Apache License 2.0, 
    Copyright (c) 2021 Hong Jing. 
    https://github.com/jinglescode/time-series-forecasting-pytorch. """

""" Config informations. """
config = {
    'data': {
        'window_size': 20, #60,
        'train_split_size': 0.80,
        'path': '../data/market-data.csv',
        'symbol': 'ETHUSDT',
    },
    'plots': {
        'show_plots': True,
        'xticks_interval': 90,
        'color_actual': '#001f3f',
        'color_train': '#3D9970',
        'color_val': '#0074D9',
        'color_pred_train': '#3D9970',
        'color_pred_val': '#0074D9',
        'color_pred_test': '#FF4136',
    },
    'model': {
        'input_size': 3,  # since we are only using 1 feature, close price
        'num_lstm_layers': 2,
        'lstm_size': 32,
        'output_size': 1,
        'dropout': 0.2,
    },
    'training': {
        'device': 'cpu', #'cuda'
        'batch_size': 64,
        'bs_train': 4,
        'bs_test': 1,
        'num_epoch': 20,
        'learning_rate': 0.001,
        'scheduler_step_size': 40,
    }
}
