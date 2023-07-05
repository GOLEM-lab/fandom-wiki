#!/bin/bash

CONF_LIM=$1

python -c "import pandas as pd; 
import sys; 
df = pd.read_csv(sys.stdin,header=0);
df[df.confidence >= $CONF_LIM].to_csv(sys.stdout,index=False)" <&0 