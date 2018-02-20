import os
import yaml

CONFIG_DIR = os.path.dirname(__file__)
with open(os.path.join(CONFIG_DIR, 'config.yaml'), 'r') as f:
    CONFIG_DATA = yaml.load(f.read())
