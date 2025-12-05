#!/bin/bash
set -e

# Wait for database
echo "Waiting for database..."
while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
    sleep 1
done
echo "Database is ready!"

{%- if cookiecutter.use_redis == "yes" %}
# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST $REDIS_PORT; do
    sleep 1
done
echo "Redis is ready!"
{%- endif %}

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Create initial superuser if needed
echo "Checking for initial superuser..."
python -c "
import asyncio
from app.db.session import async_session_maker
from app.models.user import User
from app.core.config import settings
from app.core.security import security_manager
from sqlalchemy import select

async def create_superuser():
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=security_manager.hash_password(settings.FIRST_SUPERUSER_PASSWORD),
                full_name='Admin',
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            print(f'Superuser created: {settings.FIRST_SUPERUSER_EMAIL}')
        else:
            print('Superuser already exists')

asyncio.run(create_superuser())
"

# Start application
echo "Starting application..."
exec "$@"
