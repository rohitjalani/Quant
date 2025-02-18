from easydict import EasyDict as edict
import pandas as pd
from pathlib import Path
import json
import yaml


def load_json(path):
    with open(path, 'r') as f:
        return edict(json.load(f))

def load_yaml(path):
    with open(path, 'r') as f:
        return edict(yaml.load(f, Loader=yaml.FullLoader))

def load_df(config, tf):
    
    if tf not in config.data.files:
        raise Exception("Invalid timeframe")
    
    data_path = str(Path(config.data.path, config.data.files[tf]))
    df = pd.read_csv(data_path)

    # check if unnamed is there in columns, if so drop it
    if "Unnamed: 0" in df.columns:
        df.drop(columns=["Unnamed: 0"], inplace=True)

    return df


def load_ohlcv_data(config):

    tf_cheby = config.utils.timeframes.strat_cheby
    tf_gmma_1 = config.utils.timeframes.strat_gmma_1
    tf_gmma_2 = config.utils.timeframes.strat_gmma_2
    tf_granularise = config.utils.timeframes.granularise


    df_strat_cheby = load_df(config, tf_cheby)

    df_strat_gmma_1 = load_df(config, tf_gmma_1)

    df_strat_gmma_2 = load_df(config, tf_gmma_2)

    df_strat_granularise = load_df(config, tf_granularise)

    return df_strat_cheby, df_strat_gmma_1, df_strat_gmma_2, df_strat_granularise
