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

## For building neo4j
```
docker run --name neo4j -p 7474:7474 -p 7687:7687 -d -e NEO4J_AUTH=username/password neo4j:latest
```
## For running redis
```
docker network create zavmonetwork
docker rm -f redis-stack && docker run -d --name redis-stack --network zavmonetwork -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
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