@echo off
REM Redis Docker Management Script for Windows

SET COMPOSE_FILE=docker-compose.redis.yml

IF "%1"=="" (
    echo Usage: redis-docker.bat [start^|stop^|restart^|status^|logs^|gui^|clean]
    exit /b 1
)

IF "%1"=="start" (
    echo Starting Redis in Docker...
    docker-compose -f %COMPOSE_FILE% up -d
    echo.
    echo ✅ Redis is now running on localhost:6379
    echo.
    echo Test connection with: docker exec -it parseqri_redis_cache redis-cli ping
    goto :end
)

IF "%1"=="gui" (
    echo Starting Redis with GUI management tool...
    docker-compose -f %COMPOSE_FILE% --profile tools up -d
    echo.
    echo ✅ Redis is running on localhost:6379
    echo ✅ Redis Commander GUI is running on http://localhost:8081
    goto :end
)

IF "%1"=="stop" (
    echo Stopping Redis...
    docker-compose -f %COMPOSE_FILE% down
    echo ✅ Redis stopped
    goto :end
)

IF "%1"=="restart" (
    echo Restarting Redis...
    docker-compose -f %COMPOSE_FILE% restart
    echo ✅ Redis restarted
    goto :end
)

IF "%1"=="status" (
    echo Redis Container Status:
    docker-compose -f %COMPOSE_FILE% ps
    goto :end
)

IF "%1"=="logs" (
    echo Redis Logs (press Ctrl+C to exit):
    docker-compose -f %COMPOSE_FILE% logs -f redis
    goto :end
)

IF "%1"=="clean" (
    echo WARNING: This will remove Redis data permanently!
    set /p confirm="Are you sure? (yes/no): "
    if /i "%confirm%"=="yes" (
        docker-compose -f %COMPOSE_FILE% down -v
        echo ✅ Redis stopped and data cleaned
    ) else (
        echo ❌ Cancelled
    )
    goto :end
)

echo Unknown command: %1
echo Usage: redis-docker.bat [start^|stop^|restart^|status^|logs^|gui^|clean]

:end
