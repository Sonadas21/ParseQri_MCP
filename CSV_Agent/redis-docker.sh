#!/bin/bash
# Redis Docker Management Script for Linux/Mac

COMPOSE_FILE="docker-compose.redis.yml"

case "$1" in
    start)
        echo "Starting Redis in Docker..."
        docker-compose -f $COMPOSE_FILE up -d
        echo ""
        echo "✅ Redis is now running on localhost:6379"
        echo ""
        echo "Test connection with: docker exec -it parseqri_redis_cache redis-cli ping"
        ;;
    
    gui)
        echo "Starting Redis with GUI management tool..."
        docker-compose -f $COMPOSE_FILE --profile tools up -d
        echo ""
        echo "✅ Redis is running on localhost:6379"
        echo "✅ Redis Commander GUI is running on http://localhost:8081"
        ;;
    
    stop)
        echo "Stopping Redis..."
        docker-compose -f $COMPOSE_FILE down
        echo "✅ Redis stopped"
        ;;
    
    restart)
        echo "Restarting Redis..."
        docker-compose -f $COMPOSE_FILE restart
        echo "✅ Redis restarted"
        ;;
    
    status)
        echo "Redis Container Status:"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    
    logs)
        echo "Redis Logs (press Ctrl+C to exit):"
        docker-compose -f $COMPOSE_FILE logs -f redis
        ;;
    
    clean)
        echo "WARNING: This will remove Redis data permanently!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            docker-compose -f $COMPOSE_FILE down -v
            echo "✅ Redis stopped and data cleaned"
        else
            echo "❌ Cancelled"
        fi
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|gui|clean}"
        exit 1
        ;;
esac

exit 0
