# TG Tools Backend

This is the backend for the TG Tools application. It is a FastAPI application that provides a REST API for managing Telegram accounts, jobs, and other resources.

## Prerequisites

To run this application, you need to have the following installed on your machine:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Environment Variables

The application uses a `.env` file to manage environment variables. Before running the application, you need to create a `.env` file in the `backend` directory.

```
# backend/.env
DATABASE_URL=postgresql://user:password@db:5432/tg_tools
OPENAI_API_KEY=your_openai_api_key_here
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-super-secret-key-here
```

## Building and Running the Application

To build and run the application, you can use Docker Compose. From the root of the repository, run the following command:

```bash
docker-compose up --build -d
```

This will build the Docker images for the backend, database, and Redis services, and run them in detached mode.

The backend service will be available at `http://localhost:8000`.

## Running the Worker

The application uses a background worker to process long-running jobs like group monitoring and auto-promo campaigns. The worker needs to be run as a separate process.

To run the worker, you can execute the following command inside the running backend container:

```bash
docker-compose exec backend python worker.py
```

Alternatively, you can add a new service to the `docker-compose.yml` file to run the worker automatically.

### Example `docker-compose.yml` with a worker service:

```yaml
services:
  # ... other services (backend, db, redis)

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python worker.py
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./backend:/app
      - ./job_results:/app/job_results
```

**Note on Permissions:** The worker process needs to write to the `/app/job_results` directory. If you are using a bind mount to map a local directory to `/app/job_results` (as shown in the example above), you need to ensure that the directory on your host machine has the correct permissions for the user running inside the Docker container.

## Running Tests

To run the test suite, you can use `pytest`. The tests are configured to run against the running services in the Docker environment.

Make sure you have installed the dependencies from `backend/requirements.txt` in your local python environment.

From the root of the repository, run the following command:

```bash
pytest backend/tests
```

## Database Migrations

Database migrations are managed by [Alembic](https://alembic.sqlalchemy.org/). The migrations are located in the `backend/alembic/versions` directory.

When the backend container starts, it automatically applies any pending migrations to the database.

To create a new migration, you can run the following command inside the backend container:

```bash
docker-compose exec backend alembic revision --autogenerate -m "Your migration message"
```

## Troubleshooting

### `permission denied while trying to connect to the Docker daemon socket`

This error means that your user does not have permission to access the Docker daemon. You can either run the `docker` and `docker-compose` commands with `sudo`, or you can [add your user to the `docker` group](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user).

### `toomanyrequests: You have reached your unauthenticated pull rate limit`

This error means that you have made too many anonymous requests to Docker Hub to pull images. To solve this, you need to authenticate with a Docker Hub account.

You can log in to Docker Hub by running the following command:

```bash
docker login
```
