import argparse
import json
import logging
import time
import os
import sys
import pandas as pd
import numpy as np
import yaml

def setup_logging(log_file):
    """Setup structured logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_path):
    """Load and validate config"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    required_keys = ['seed', 'window', 'version']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")
    
    return config

def load_data(input_path):
    """Load and validate CSV data"""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    df = pd.read_csv(input_path)
    
    if df.empty:
        raise ValueError("Input CSV is empty")
    
    if 'close' not in df.columns:
        raise ValueError("Required 'close' column missing")
    
    return df

def process_data(df, seed, window):
    """Main processing logic"""
    np.random.seed(seed)
    
    # Calculate rolling mean (handle NaN for first window-1 rows)
    rolling_mean = df['close'].rolling(window=window).mean()
    
    # Generate signals
    signals = (df['close'] > rolling_mean).astype(int)
    
    # Calculate metrics
    rows_processed = len(df)
    signal_rate = signals.mean()
    
    return rows_processed, signal_rate, signals

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--config', required=True, help='Config YAML file')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--log-file', required=True, help='Log file path')
    args = parser.parse_args()
    
    logger = setup_logging(args.log_file)
    start_time = time.time()
    
    try:
        logger.info("Job started")
        
        # Load config
        config = load_config(args.config)
        logger.info(f"Config loaded: seed={config['seed']}, window={config['window']}, version={config['version']}")
        np.random.seed(config['seed'])
        
        # Load data
        df = load_data(args.input)
        logger.info(f"Data loaded: {len(df)} rows")
        
        # Process data
        logger.info(f"Rolling mean calculated with window={config['window']}")
        rows_processed, signal_rate, signals = process_data(df, config['seed'], config['window'])
        logger.info("Signals generated")
        
        # Calculate final metrics
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Metrics: signal_rate={signal_rate:.4f}, rows_processed={rows_processed}")
        
        # Write metrics
        metrics = {
            "version": config['version'],
            "rows_processed": rows_processed,
            "metric": "signal_rate",
            "value": float(signal_rate),
            "latency_ms": latency_ms,
            "seed": config['seed'],
            "status": "success"
        }
        
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Job completed successfully in {latency_ms}ms")
        print(json.dumps(metrics, indent=2))  # Print to stdout for Docker
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Job failed: {str(e)}")
        
        error_metrics = {
            "version": "v1",
            "status": "error",
            "error_message": str(e)
        }
        
        with open(args.output, 'w') as f:
            json.dump(error_metrics, f, indent=2)
        
        print(json.dumps(error_metrics, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
