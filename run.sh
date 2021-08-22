# py -m venv seleenv
python -m venv seleenv

# seleenv\Scripts\activate
source seleenv/bin/activate

sudo python3 -m pip install --upgrade pip
sudo python3 -m pip install selenium Pillow pyderman

sudo python3 nowc.py
