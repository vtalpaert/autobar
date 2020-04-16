# script to run on startup
cd /home/pi/autobar

# fetch latest code
git pull origin master
pip3 install -r requirements.txt
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --noinput
# could install fixtures eventually

# run server
python3 manage.py runserver 0.0.0.0:8000 --noreload
