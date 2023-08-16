# Migration
- dumped db from current app
- uploaded db to running copy
- inspectdb to get models file
    - python3 manage.py inspectdb > models.py
- got rid of large records
- renamed models to legacy
- deleted problematic fields
- imported into our app in legacy app