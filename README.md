# saharalabs faucet
Daily Claim

# venv
```
# Create venv
python3 -m venv venv
# Activate venv
source venv/bin/activate
# Exit venv
deactivate
```

# Install
```
pip install --upgrade pip
pip install -r requirements.txt
```

# Plugin
```
cd ./extensions/
unzip okx.crx -d okx/
unzip CapMonster.crx -d CapMonster/
```

# Run
```
cp conf.py.sample conf.py
cp datas/purse/purse.csv.sample datas/purse/purse.csv
python sahara_faucet.py
```
