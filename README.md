# zavmo-api
Zavmo backend API, built with django - for managing user profiles, LLM messages, stage transitions etc.

---
# Docker Setup
```
docker-compose up --build --force-recreate --detach
```
# Stop
```
docker-compose down --remove-orphans
```

## Check logs
```
docker logs -f zavmo-api-app-1
```
## Delete all volumes
```
docker system prune -a --volumes
```