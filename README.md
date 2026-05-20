# Neomarket  
## Дока на http://localhost:8000/docs  
  
## Запуск  
``` 
docker compose up -d
```  

## Остановка  
```  
docker compose down -v
```  
  
## Логи  
```
docker compose logs b2b
```  
  
## Запуск тестов  
``` 
docker compose -f docker-compose.test.yml run --rm tests pytest --asyncio-mode=auto tests -v
```
```
docker compose -f docker-compose.test.yml down
```
