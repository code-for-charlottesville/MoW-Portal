# Migrate hosts
- In your domain registrar, add two records to your new domain name
  - Create an A record for `portal.cvillemeals.org` to `server ip` (in this case, our server is currently running on 3.81.0.93)


# Data Migration
- command to dump db on old
  - python3 manage.py dumpdata -e contenttypes -e auth.Permission > ../../alex/db.json
- scp db.json to new server
- move db.json into src/data/db.json
- run src/data/parse.py
- make env=prod nuke
- make env=prod deploy
- make ssh
  - ./manage.py test
- make env=prod initialize