# Neomarket

### B2B Docs http://localhost:8000/docs  
### B2C Docs http://localhost:8001/docs  

## Build and run 
``` 
docker compose up -d --build
```  

## Stop  
```  
docker compose down -v
```  
  
## Logs 
```
docker compose logs b2b
```  
  
## Tests

### Build
``` 
docker compose -f docker-compose.test.yml build
```

### B2B
```
docker compose -f docker-compose.test.yml run --rm tests_b2b pytest --asyncio-mode=auto tests -v
```

### B2C
```
docker compose -f docker-compose.test.yml run --rm tests_b2c pytest --asyncio-mode=auto tests -v
```

### Stop
```
docker compose -f docker-compose.test.yml down
```