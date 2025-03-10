# zavmo-api
Zavmo backend API, built with django - for managing user profiles, LLM messages, stage transitions etc.

---
# Docker Setup
```
docker compose up --build --force-recreate --detach
```
# Stop
```
docker compose down --remove-orphans
```

# Enter container
```
docker exec -it zavmo_app /bin/bash
cd zavmo
```

## Check logs
```
docker logs -f zavmo_app
```
## Delete all volumes
```
docker system prune -a --volumes
```

## For loading static data from excel to django models
```
python manage.py save_data assets/static_data/JDs_NOS_OFQUAL.xlsx
```

### For dev

```
python delete_migrations.py
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --noinput
python manage.py runserver
```


## TODO

- **Centrica Tasks**
  - Centrica GitHub branch setup
  - Centrica new models
  - Setting up structure for Centrica corporate flow

- **xAPI Exploration**
  - Explore and review xAPI
  - Testing by saving dummy information using xAPI

- **Infrastructure**
  - Redis Insight whitelisting
  - Dev server backend setup

- **Documentation Review**
  - Review NOS documents