from utils.utils import *
from utils.strategies import *
from utils.align import *
from utils.ensemble import *
from utils.tpsl import *
from utils.backtester import *
import json

def main():
	config = load_yaml('./config.yaml')

	ohlcv_cheby, ohlcv_gmma_1w, ohlcv_gmma_1d, ohlcv_gran = load_ohlcv_data(config)
	
	strat_cheby = StratCheby(ohlcv_cheby, ohlcv_gran, config)
	strat_gmma = MixedStratGMMA(ohlcv_gmma_1w, ohlcv_gmma_1d, ohlcv_gran, config)

	cheby_trades = strat_cheby.run()
	gmma_trades, gmma_values = strat_gmma.run()

	aligner = Aligner(cheby_trades, gmma_trades, config)	
	aligned_cheby_trades, aligned_gmma_trades = aligner.run()

	ensemble = Ensemble(aligned_cheby_trades, aligned_gmma_trades, gmma_values, config)
	ensemble_trades = ensemble.run()

	tpsl = TPSL(config)
	tpsl_trades = tpsl.run(ensemble_trades)

	tpsl_trades.to_csv(f"./output/signals.csv")
	
	bt = Backtester(config)

	results, stats, logs = bt.getBacktestingResults(tpsl_trades)

	results.to_csv("./output/results.csv")
	with open("./output/stats.json", 'w') as f:
		json.dump(stats, f, indent=4)
	logs.to_csv("./output/logs.csv")

	return results, logs

if __name__ == '__main__':
	main()